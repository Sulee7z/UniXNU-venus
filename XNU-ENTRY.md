# Venus first-console XNU

## PrePi FDT allocation correction

Photo 20261025_135758.JPG stopped before MMU enable/DXE. The earlier
AllocateCopyPool(FdtSize) was invalid for the roughly 758 KiB real FDT:
Mu's PrePi AllocatePool rejects requests over 64 KiB. This is corrected to
AllocatePages plus CopyMem, with visible checkpoints and failure statuses.

Latest candidate: `artifacts/venus-xnu-fdt-pages/boot-venus-unixnu.img`.
SHA256 `dccf09b0ad468d487f20d69f84b0c8f27756b14d4ad3208df614fec64dbc17e0`.
The kernel and RAM payload did not change. This corrects a source-proven bug;
phone execution of this correction is not yet observed.

## initrd overlap fix

The first phone test did not reach DXE/XNU. Photo `20261025_133152.JPG`
showed ABL's initrd at [0xACCD6000, 0xAFFFEB97), inside the original DXE
heap. The SEC overlap check correctly stopped before overwriting this input.

DXE heap is now [0xC6200000, 0xD6200000), a verified clean 256 MiB DRAM
range; the old heap is ordinary RAM with the exact ABL input reserved at
runtime. The overlap check now uses the actual descriptor rather than an
old hardcoded heap address. FAT headers can occur at byte-aligned offsets
within ABL's concatenated ramdisks. A bounded BPB parser identifies our label;
its tests passed 512 alignment offsets plus truncation/malformed-header
controls under ASan/UBSan.

New candidate: `artifacts/venus-xnu-initrd-fix/boot-venus-unixnu.img`.
SHA256: `755393d7bb5ecee165eca59edaa44e1c79d381270265f835933e471dfbe41c54`.
Size: 34734080. Native kernel and FAT payload remain unchanged.
Build/container/compiled-heap checks passed; all 21 reservations remain
covered. The user approved a corrected-image RAM boot; fastboot returned
Sending/Booting OKAY (0.955 s). Screen/entry result is pending a new photo.

## Build

- XNU source: xnu-10063.141.1 / d8b80295118ef25ac3a784134bcf95cd8e88109f.
- Plain ARM64, iOS 17 deployment, 4K BCM2837 layout with UniXNU patches.
- Actual corecrypto source, matching source libpthread, ArmDTPlatform and
  ArmCpu compiled/linked; source crypto HMAC field sealed normally.
- Linux host compiler LLVM 23; cross compiler retains the pinned LLVM source
  58c46bae21181fb4240cf964461bea738d96d50e plus XNU type-builtins patch.
- Kernel SHA256: b8ac3c1df330d9c20295a47e96d3908b47063cbcc4cd7ed34c6fe0c2f9d292f2.

## Offline execution

QEMU booted the same native kernel through standalone (non-Venus-MMIO) EFI
builds of UniXNU and DarwinBoot. The upstream observer's host artifact paths
and QEMU 8 register alias `SCTLR` were adapted; no guest kernel code or
register values were invented/changed.

Observed at bsd_init:

- Native 4K active translation, nonzero TTBR0/TTBR1.
- source corecrypto status 0, PRNG ready 1.
- Matching pthread registration status 0.
- ArmDTPlatform configured 1.
- CPU registration 1; GIC readiness and timer delivery are not yet completed
  at this early boundary.
- No bounded timeout interruption.

Report: `artifacts/venus-xnu-entry/qemu/gdb-stop.json`.
An additional run observed the real rtclock_intr return at its caller:
CPU registration 1, GIC ready 1, running CPUs 1, timer interrupt count 1,
with no timeout interruption. This qualifies the native CPU/timer path in
QEMU, not on Mi 11. Report: `qemu-timer/gdb-stop.json`.
The first emulator attempt accidentally used Venus-specific EFI debug-library
links, which faulted on the physical framebuffer. A standalone EFI DSC was
then built for QEMU; the phone build retains its required Venus libraries.

## Phone payload

Image: `artifacts/venus-xnu-entry/boot-venus-unixnu.img`.
SHA256: 22be06dbe2b3a6c0f3c2c4d528581517aed5b4df730e2e041a551c8296684db7.
Size: 34734080 bytes. Android boot v3 + 32 MiB FAT RAM payload.

FAT volume contains the native kernel, generated Mi 11 ADT and unixnu.toml.
Only CPU0 is described; PSCI SMC, GICv3 and 19.2 MHz are taken from live FDT.
DarwinBoot requests a 256 MiB contiguous owned kernel window.

Firmware adds measured low-4GiB RAM ranges outside all reservations. SEC
reserves ABL's initrd and keeps a low-memory FDT copy before DXE allocation.
VenusPayloadDxe finds the labelled FAT inside ABL's combined initrd and
publishes it as a read-only block device, allowing normal FAT parsing.

No physical UFS XNU driver or iOS root filesystem is included. Root-device
wait/failure after successful platform bring-up is expected at this stage.
The user approved this image's RAM boot and menu selection. Fastboot returned
Sending/Booting OKAY (0.960 s total), without partition flashing or phone file
creation. The screen/native-entry result remains pending the user's photo.
