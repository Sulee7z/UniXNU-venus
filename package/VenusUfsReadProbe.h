// SPDX-License-Identifier: BSD-2-Clause-Patent
// Included after the production host, command and parser definitions.
#include "VenusUfsGptRead.h"
static void venusBankRefusal(const VenusUfsReadPlan::Plan &plan)
{
  native_ufs_status = kIOReturnNotReady;
  static char report[2048];
  int used = snprintf(report, sizeof(report),
    "VENUS UFS BANK PREFLIGHT: %s\ndma=%llx bytes=%llx id0=%x id1=%x id2=%x\n"
    "commands=%u examined=%u (contextRead=0 means values not sampled)\n",
    plan.error, plan.dma, plan.bytes, plan.idr0, plan.idr1, plan.idr2, gRootDiagnostic.command, plan.examined);
  for (unsigned i = 0; i < plan.examined && used >= 0 && used < int(sizeof(report)); ++i) {
    const auto &c = plan.candidates[i];
    used += snprintf(report + used, sizeof(report) - used,
      "bank=%u read=%u cbar=%08x cba2r=%08x sctlr=%08x %s\n",
      c.bank, unsigned(c.contextRead), c.cbar, c.cba2r, c.sctlr, c.reason ? c.reason : "qualified");
  }
  panic("%s", report);
}
static void venusBlockReadProbe(void)
{
  gRootDiagnosticEnabled = true;
  OSSharedPtr<IOMemoryMap> gccMap, hcMap, smmuMap;
  uintptr_t gcc = mapPhys(GCC_BASE + 0x77000, 4096, gccMap), hc = 0, smmu = 0;
  auto before = VenusUfsSurvey::collect(
    [&](unsigned o, uint32_t &v) { if (!gcc || o > 0xffc || (o & 3)) return false; v = read32(gcc, o); return true; },
    [&](unsigned o, uint32_t &v) {
      if (o > UFS_HC_SIZE - 4 || (o & 3)) return false;
      if (!hc) hc = mapPhys(UFS_HC_BASE, UFS_HC_SIZE, hcMap);
      if (!hc) return false;
      v = read32(hc, o); return true;
    },
    [&](unsigned o, uint32_t &v) {
      if (o > 0xcfffc || (o & 3)) return false;
      if (!smmu) smmu = mapPhys(0x15000000, 0xd0000, smmuMap);
      if (!smmu) return false;
      v = read32(smmu, o); return true;
    });
  native_ufs_mapped = before.hcRead;
  if (before.errors || !before.hcRead || !before.cbRead || before.matches != 1 ||
      before.transferDoorbell || before.taskDoorbell || before.gfsr ||
      !(before.hce & 1) || (before.hcs & 15) != 15 || (before.is & kUfsFatalStatus))
    panic("VENUS UFS BLOCK READ preflight refused\nerr=%x hc=%u cb=%u hcs=%x hce=%x is=%x\n"
          "db=%x/%x id0=%x id1=%x id2=%x gfsr=%x\nsmr=%x s2cr=%x users=%u",
          before.errors, before.hcRead, before.cbRead, before.hcs, before.hce, before.is,
          before.transferDoorbell, before.taskDoorbell, before.idr0, before.idr1, before.idr2, before.gfsr,
          before.smr, before.s2cr, before.users);
  const char *why = "";
  auto fail = [&](const char *reason) {
    native_ufs_status = kIOReturnError;
    rootDiagnosticFailure(reason);
    panic("VENUS UFS BLOCK READ: %s", reason);
  };
  // Production path: private contiguous allocation, bounded stop/readback,
  // checked SMMU plan, NOP, power query/optional ACTIVE wake, bounded TUR.
  if (!hostBringUp(&why)) fail(why);
  gRootDiagnostic.stage = "READ CAPACITY(10)";
  uint8_t cdb[10] = {0x25};
  uint32_t scsi = 0;
  if (hostScsi(0, cdb, 10, true, 8, 1000000, &scsi) != kIOReturnSuccess) fail("capacity command");
  uint64_t last = loadBe32(gHost.virt + kDataOffset);
  uint32_t blockBytes = loadBe32(gHost.virt + kDataOffset + 4);
  gRootDiagnostic.stage = "bounded GPT mirror read";
  auto gpt = VenusUfsGptRead::collect(blockBytes, last, gScratch, sizeof(gScratch),
    [&](uint64_t lba, unsigned blocks, uint8_t *dst) {
      gVenusReadScope = {lba, blocks};
      IOReturn result = hostRead4k(0, lba, blocks, dst);
      gVenusReadScope = {};
      return result == kIOReturnSuccess;
    });
  if (gpt.error) fail(gpt.error);
  // Keep all DMA storage and mappings alive at the diagnostic stop. On failed
  // commands the production path already quarantines them; never reuse/free.
  gRootDiagnostic.stage = "final queue stop";
  if (!hostStopQueue(&why)) fail(why);
  gHost.ready = false;
  SHA256_CTX sha;
  uint8_t digest[32]; char hash[65];
  SHA256_Init(&sha); SHA256_Update(&sha, gScratch, 4096); SHA256_Final(digest, &sha);
  static const char hex[] = "0123456789abcdef";
  for (unsigned i = 0; i < 32; ++i) { hash[i * 2] = hex[digest[i] >> 4]; hash[i * 2 + 1] = hex[digest[i] & 15]; }
  hash[64] = 0;
  native_ufs_status = kIOReturnSuccess;
  panic("VENUS UFS BLOCK READ OK\n"
        "lun=0 bs=%u last=%llx bytes=%llx\n"
        "dma=%llx extent=%llx id2=%x\n"
        "sid=e0 slot=%u s2cr=%x cbar=%x cba2r=%x\n"
        "old_utrl=%llx old_utmr=%llx old_cb=%x\n"
        "new_utrl=%llx commands=%u GPTreads=%u\n"
        "GPT entries=%u used=%u usable=%llx..%llx\n"
        "GPT arrays=%llx/%llx CRC=%08x\n"
        "GPT headerCRC=%08x backupCRC=%08x\n"
        "primarySHA256=%s\n"
        "stopped=%x/%x db=%x/%x gfsr=%x",
        blockBytes, last, (last + 1) * blockBytes, gHost.phys, gRootDiagnostic.contiguous, gRootDiagnostic.smmuId2,
        gRootDiagnostic.smmuSlot, gRootDiagnostic.s2cr, gRootDiagnostic.cbar, gRootDiagnostic.cba2r,
        before.transferBase, before.taskBase, before.cb, gHost.phys, gRootDiagnostic.command, gpt.reads,
        gpt.entries, gpt.used, gpt.firstUsable, gpt.lastUsable, gpt.entriesLba, gpt.backupEntriesLba,
        gpt.entriesCrc, gpt.primaryCrc, gpt.backupCrc, hash,
        read32(gHost.hc, 0x60), read32(gHost.hc, 0x80), read32(gHost.hc, 0x58), read32(gHost.hc, 0x78), read32(gHost.smmu, 0x48));
}
