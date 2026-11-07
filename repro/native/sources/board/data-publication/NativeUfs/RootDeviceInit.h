// SPDX-License-Identifier: BSD-2-Clause-Patent
// Device initialization after exclusive queue/SMMU takeover. Uses the same
// production UPIU validation and quarantine rules as ordinary block requests.
static bool hostDeviceFailure (const char **why, const char *reason)
{
  gHost.ready = false;
  *why = reason;
  return false;
}

static bool hostRetryableDeviceStatus (uint32_t scsi)
{
  if (gHost.poisoned) return false;
  if (scsi == 0x08 || scsi == 0x28) return true; // BUSY / TASK SET FULL, response=0.
  if (scsi != 0x02) return false;
  unsigned key = (gRootDiagnostic.sense >> 16) & 15;
  // UNIT ATTENTION is consumed by the completed command's autosense. Only
  // NOT READY / becoming ready is transient here; illegal commands and media
  // errors must not be hidden behind a generic timeout.
  return key == 6 || (key == 2 && (gRootDiagnostic.sense & 0xffff) == 0x0401);
}

static bool hostDeviceScsi (uint8_t lun, const uint8_t *cdb, unsigned length,
                           uint32_t dataBytes, const char **why, const char *reason)
{
  uint64_t deadline;
  clock_interval_to_deadline (2000, kMillisecondScale, &deadline);
  for (unsigned attempt = 0; attempt < 20; ++attempt) {
    uint32_t scsi = 0xffff;
    IOReturn status = hostScsi (lun, cdb, length, dataBytes != 0, dataBytes, 500000, &scsi);
    if (status == kIOReturnSuccess) return true;
    if (!hostRetryableDeviceStatus (scsi) || attempt == 19 || mach_absolute_time () >= deadline)
      break;
    IOSleep (10);
    if (mach_absolute_time () >= deadline) break;
  }
  return hostDeviceFailure (why, reason);
}

static bool hostInitializeDevice (const char **why)
{
  gHost.ready = false;
  gRootDiagnostic.stage = "NOP OUT";
  if (hostNop () != kIOReturnSuccess) return hostDeviceFailure (why, "NOP OUT");

  // Firmware owns cold initialization. Wait for its existing fDeviceInit to
  // clear; do not issue SET FLAG or reset/reinitialize an already live device.
  gRootDiagnostic.stage = "firmware device initialization";
  uint64_t deadline;
  clock_interval_to_deadline (1000, kMillisecondScale, &deadline);
  for (;;) {
    uint32_t pending = 0;
    if (hostQueryRead (0x05, 0x01, &pending) != kIOReturnSuccess)
      return hostDeviceFailure (why, "fDeviceInit query");
    if (!pending) break;
    if (pending != 1) return hostDeviceFailure (why, "invalid fDeviceInit value");
    if (mach_absolute_time () >= deadline)
      return hostDeviceFailure (why, "firmware device initialization timeout");
    IOSleep (10);
  }

  gRootDiagnostic.stage = "power mode query";
  uint32_t power = 0;
  if (hostQueryRead (0x03, 0x02, &power) != kIOReturnSuccess)
    return hostDeviceFailure (why, "power mode query");
  gRootDiagnostic.power = power;
  // Preserve the existing bCurrentPowerMode encoding (0x11 Active, 0x33
  // PowerDown). These attribute values are not the SSU power-condition nibble.
  if ((power & 0xff) != 0x11) {
    gRootDiagnostic.stage = "device wake";
    const uint8_t ssu[6] = { 0x1b, 0, 0, 0, 0x10, 0 };
    if (!hostDeviceScsi (0xd0, ssu, sizeof (ssu), 0, why, "wake (START STOP UNIT)")) return false;

    gRootDiagnostic.stage = "device active confirmation";
    clock_interval_to_deadline (1000, kMillisecondScale, &deadline);
    for (;;) {
      if (hostQueryRead (0x03, 0x02, &power) != kIOReturnSuccess)
        return hostDeviceFailure (why, "power mode query after wake");
      gRootDiagnostic.power = power;
      if ((power & 0xff) == 0x11) break;
      if (mach_absolute_time () >= deadline)
        return hostDeviceFailure (why, "device did not become active");
      IOSleep (10);
    }
  }

  gRootDiagnostic.stage = "LUN ready";
  const uint8_t tur[6] = {};
  if (!hostDeviceScsi (0, tur, sizeof (tur), 0, why, "LUN 0 not ready")) return false;

  // RootLayout and the data/log windows use 4096-byte LBAs and READ(10).
  // Prove that geometry before the first GPT read or setting ready=true.
  gRootDiagnostic.stage = "LUN capacity";
  const uint8_t capacity[10] = { 0x25 };
  if (!hostDeviceScsi (0, capacity, sizeof (capacity), 8, why, "LUN 0 capacity")) return false;
  uint32_t last = loadBe32 (gHost.virt + kDataOffset);
  uint32_t blockBytes = loadBe32 (gHost.virt + kDataOffset + 4);
  if (blockBytes != 4096) return hostDeviceFailure (why, "LUN block size is not 4096");
  if (last < 2 || last == 0xffffffffU)
    return hostDeviceFailure (why, "LUN capacity outside READ(10) root geometry");
  gUfsLastLba = last;
  gHost.ready = true;
  return true;
}
