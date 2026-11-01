# Sheng success-record comparison (2026-10-27)

Latest2026-10-29 requested-repo review: HEAD08cde20e is freshly confirmed,
19 startup files verified by Git blob/length/SHA256. Shared init order and the
original watchdog policy are already reused; two supported generic policies
are now packaged in the qualified4b1 chain010 control. See `SHENG-STARTUP-CHAIN.md`.
Historical observations below retain their original dates.

User-supplied record: https://unixnu.com/zh/devices/sheng

Published device revision: `08cde20edc3254ed6f7df8d0f5384fb887786e8f`.
Read the page, its pinned `configs/sheng_defconfig`,
`scripts/build-boot-progress.py`, `package/BootProgress.c`, and
https://unixnu.com/zh/devices/sheng-unattended-test .

## Applicable findings

- Sheng targets the same iPadOS 17.7.11 / 21H461 profile as Venus. Prefer this
  same-ABI diagnostic source over the previously inspected XNU12377 zeta version.
- The root configuration agrees on native UFS, Virtio/RamBlock support,
  VerifiedRoot, owner root/cache/Data enforcement, union SystemOS and PMGR.
- Sheng also enables `CONFIG_XNU_DT_PANIC_REGION`,
  `CONFIG_XNU_ZONE_PGZ_ALIGNMENT_PROBE`, `CONFIG_XNU_BOOT_PROGRESS`, and its own
  native legacy display. Venus currently lacks that complete observation/display
  chain. `boot-progress=2` needs the compiled implementation and hooks; adding
  only the argument cannot make the current kernel report later stages.
- Its BootProgress source records actual stages, IRQ/monitor activity, UFS reads,
  integrity results, root acceptance, memory and process events. Framebuffer
  binding accepts the mapping only after XNU provides a valid kernel virtual
  address. The current three bars alone do not supply those observations.

## Memory and board differences

- The published sheng payload requests `0x130000000` (4.75 GiB). Its firmware has
  board-owned memory expansion. Venus's measured 310 MiB conventional run and
  qualified 288 MiB candidate are an early bring-up constraint, not proof of
  sufficient resources for the full OS and graphics workload.
- Local `sources/uefi-sheng/.../ShengBootMemoryDxe.c` is an older implementation
  with ADD_LIMIT=1 GiB and ADD_BELOW=4 GiB. Do not treat it as the firmware behind
  the current published 4.75 GiB request. It does show the intended method:
  derive RAM from the handed-off FDT and exclude firmware/reserved regions.
- Reconcile Venus's actual FDT RAM banks, reserved-memory, GCD map, initrd,
  framebuffer and address-width limits before changing its UEFI memory policy.
- Sheng is SM8550 and uses UFS SID 0x60. Venus is SM8350; its already measured
  SID 0xe0/bank74 and existing storage geometry remain the board-specific inputs.

## Diagnostic storage scope

Sheng BootLog uses its userdata tail's reserved 32 MiB, and its read-only Linux
reader is built for sheng's kernel/DT. A Venus logger must instead bind to the
verified unixnu layout and its reserved region. Neither the sheng reader image
nor its userdata write offsets are appropriate device operations on Venus.

## Memory finding and high-memory candidate

- The live Venus DT has two DRAM banks: `0x80000000` + 0x39700000 and
  `0xC0000000` + 0x1C0000000 (8 GiB total). Its `/reserved-memory` nodes all
  lie below 4 GiB; the high bank past 4 GiB has no reserved-memory entries.
- `venusPkg/Library/MemoryMapLib/MemoryMapLib.c` published only the low run up
  to `0x100000000`, so DarwinBoot saw a 310 MiB largest run and iOS ran with a
  288 MiB owned window (free pages near exhaustion after launchd started).
- Add `Kernel RAM G` at `0x100000000` for 4 GiB, guarded by
  `UNIXNU_VENUS_HIGH_MEMORY` in `venus.dsc`. Static DT checks show no overlap
  with memory or reserved-memory. `ArmConfigureMmu` supports the resulting
  40-bit physical range.
- Candidate: UEFI FD `ee2e60af...`, ADT window 1 GiB, boot image
  `d7dcd9309de5092f706cf99df5888c5b908a718535d10236e79da77f73403570`.
  A QEMU 1 GiB run reached the real owner-root checkpoint with 830226432 free
  bytes. Phone execution is not yet performed; high physical memory and the
  modified UEFI still need device qualification.

## Current Venus facts and follow-up

- GPT, Android reinitialization, post-reset geometry and 67-fragment unixnu root
  flashing completed. Root mounting and launchd are not yet observed on phone.
- The b017a79e 288 MiB RAM boot shows green/blue/magenta bars for over two minutes.
  Magenta precedes MSR SCTLR_EL1, so it does not prove the MMU transition passed.
- First obtain a qualified early-C checkpoint and/or same-ABI passive stage
  observation. Then distinguish translation, driver/root publication, mount and
  process startup failures from the actual result.
- The early-C checkpoint image was completed and independently verified. It
  reset the phone shortly after `fastboot boot`, consistent with reaching the
  first `PE_init_platform` call in `arm_init`; the reset timing alone does not
  exclude a watchdog path. Android booted normally afterwards.
- The sheng BootProgress implementation was then ported from the same pinned
  `package/` revision. `BootProgressAbsent.S` supplies only the optional driver
  symbols Venus does not build. The new kernel and full sparse-root QEMU test
  reached `_native_owner_root_accepted_checkpoint` with `boot-progress=2`,
  288 MiB owned memory and two authenticated policy copies.
- `artifacts/venus-ufs-root/phone-bootprog/boot-venus-unixnu.img` SHA256
  `44d6c7ce1d3be22a2a919778d4b3b2af4a43d7ae506efc6e84836aec0dcae6eb` is the next
  candidate. It has no entry-probe/panic-screen patch; BootProgress owns the
  diagnostic page. It still requires explicit authorization for a phone RAM boot.
- The QEMU wrapper now filters absolute-zero stub symbols before inspection so
  the host observer does not mistake absent Venus display/touch drivers for
  present legacy hardware. This changes host evidence only, not guest code.
- Existing phone authorizations have been consumed by their recorded attempts.
  New diagnostic kernels and any log-region writes need their own exact
  operation authorization.
