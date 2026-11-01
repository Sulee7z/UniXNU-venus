# Venus legacy-build migration plan
Started 2026-10-27 after the format-2 iOS 17 port reached root and userspace but
SpringBoard still exited with SIGTRAP. Its cause has not been established.

## Crash-page result and display ABI audit
`SPRINGBOARD-FAULT-DIAGNOSTICS.md` records the `32e385b5...` 1 GiB candidate.
Its authorized phone run displayed `CRASH 1/4 p149 SpringBoard sig5 src=EL0`
with `root=1`, 118 processes and zero UFS failures/integrity failures. The
photographed PC (`0x1a11a43ec`) does not land on a BRK instruction in the
matching 21H461 SystemOS cache, and the 100-character row split a backtrace
word, so the provisional MediaToolbox/FrontBoard mapping is not a root-cause
claim. The user subsequently reported Android/black-screen; no retry occurred.

`scripts/audit-venus-mobile-graphics.py` then passed a static audit of the
current full Venus kernel: the original `IOMobileGraphicsFamily` text hash
matches sheng (`2e044ee6...`), and its 358-slot Legacy dispatch, constructor
chain, pure slots, generic overrides and `newUserClient` ABI match. This makes
the original display ABI usable for host work, but does not create a display
instance or scanout. Report: `evidence/display-abi-audit.json` and
`artifacts/venus-exit-fault/display-analysis/`.

## Display instance in QEMU

`build-gop-legacy-display.py` now builds the actual display archive and
`EXTRA_LD_ARCHIVES` links it into kernel `394b4dce...`. QEMU with 1 GiB owned
memory still reaches `_native_owner_root_accepted_checkpoint`; the original
`NativeLegacyDisplay` reports stage 10, init/start success, probe/parent match,
surface found, registration and device-tree attachment, and an 800x600 GOP.
`NativeGOPPresenter.ready` remains zero, with no client, transfer, swap or
frame. The probe's display data-field reads report `E22` and are recorded as
unavailable. This is display-instance evidence, not a Venus panel, compositor
or desktop result. Evidence: `evidence/display-qemu-instance.json`.

## Display candidate phone result

The exact `279526f1...` display image was RAM booted once on the phone. It
stopped on a BootProgress page with only top/bottom content and `NativeGOPFramebuffer`
text; there was no SpringBoard, desktop or presented frame. The image was not
retried and no partition was written. The phone needs a manual force reboot to
Android. Photos: `G:\20261027_192718.JPG`, `G:\20261027_192706.JPG`; record:
`evidence/display-phone-result.json`. Display integration did not fix the
SpringBoard signal-5 path.

## Next candidate: visible fault context
The candidate added crash-row observability only. A closer CRASH 1/4-2/4
photograph or a space-aware formatter is needed before trusting the captured
image path. No display/GPU driver is added in this step.

## Latest result: complete baseline reaches phone userspace
- The complete build uses `/root/unixnu-build/UniXNU-sheng-base` at
  `8d157ee18ae9c4d518aba28cb3040a84e860dcd1` with local changes, the original
  `ports/UniXNU-venus` device and `venus_ufs_root_defconfig`. It is a schema-2
  build despite the legacy-full experiment name; the minimal legacy device
  below is a separate configuration.
- Kernel `dfa93ce0af513817929e1d939b296745b00dd078f7ed92634f8cb8cc7fba81f8`
  built successfully after a clean XNU bootstrap. The incremental missing-object
  detection defect has not thereby been repaired.
- Boot image `28051b5a09fc7ff875d11202cd179173a0b30f40272a765937e92d0eb0d037f0`
  was RAM booted once under the exact-image authorization. The user photograph
  shows BootProgress, root acceptance, 112 processes and zero reported UFS
  failures/integrity failures. SpringBoard still has three retained signal-5
  exit rows; a usable desktop is not demonstrated.
- Correction: the image reused `phone-highmem-1g/payload.img` with only its
  kernel replaced. The pre-boot description said 3 GiB incorrectly; the phone
  shows 1024 MiB and 1932 free 4K pages (about 7.55 MiB).
- QEMU reached `_PE_init_printf` with page shift 12, but the probe exited 1
  because the original crypto provider had not initialized at that early stop.
  This is checkpoint evidence, not a full QEMU pass or an isolated diagnosis
  of the minimal candidate's early fault.
- See `evidence/legacy-full-phone.json` for image/photo hashes and transcript.
  Next: collect SpringBoard failure details and audit iOS17 display-service
  dependencies. GPU causation and Data persistence remain unverified.

## Original plan (historical; current build selection is above)
Keep the working format-2 deployment untouched. Build a separate legacy Venus
device repository against `G:\UniXNU-Port\sources\UniXNU` (iOS 17.7.11,
xnu-10063), because the graphics-capable iOS 17 components and the sheng success
record use that pipeline.

## References
- `G:\UniXNU-Port\sources\UniXNU-sheng-legacy`: complete legacy iOS 17.7.11
  device repository, commit `08cde20edc3254ed6f7df8d0f5384fb887786e8f`, with
  submodules, packages, kits, graphics build scripts and the published sheng
  success record. Same OS profile as Venus.
- `G:\UniXNU-Port\sources\UniXNU-zeta-none24smu`: mature SM8350/Adreno 660
  graphics code (ZetaA660HwInit, ZetaGmu, GpuPowerProbe, NativeAdreno patches),
  but iOS 26/XNU 12377. Use only the A660 hardware sequences and design facts.
- Current Venus format-2 artifacts remain the control: 3 GiB BootProgress image
  `867af31b...`, 1 GiB image `d7dcd930...`, signed root image/Data, owner key,
  UEFI GPT application and host evidence.

## Graphics integration issue under investigation
The format-2 prelink emits only the native kernel symtab; the original
IOMobileFramebufferLegacy/MobileGraphics symbols are absent. The sheng display
and GPU scripts bind exact original symbols/addresses from the legacy
`build/xnu-prelink/native-owner-mobile-graphics-candidate.macho`. That audited
candidate still needs to be produced for Venus. Missing exported names do not
prove the original component code is absent or that schema-2 cannot support
graphics; the prelink reports include IOMobileGraphicsFamily and IOGPUFamily.

## Phases
0. Control and recovery
   - Preserve the format-2 repo/artifacts; do not overwrite them.
   - Recover the phone to Android or keep it in a known bootloader state.

1. Legacy Venus repository and baseline kernel
   - Create `ports/UniXNU-venus-legacy` with board.toml, configs, dts, patches,
     scripts and package files modeled on sheng's legacy repo.
   - Port Venus-specific UFS/root/PMGR/ADT/UEFI-inputs code from the format-2
     work; keep the same 64 GiB unixnu partition, signed root image, Data seed
     and owner public anchor.
   - Milestone: legacy Venus kernel reaches real unixnu root, owner-root
     acceptance and launchd, with the 3 GiB high-memory firmware.

2. Display
   - Adapt the iOS 17 GopFramebuffer/NativeMobileDisplay path to the Venus GOP
     framebuffer and single panel.
   - Milestone: IOMobileFramebuffer/display service published; observe whether
     SpringBoard/backboardd stop trapping and whether a UI frame appears.

3. Adreno 660 GPU
   - Extract and hash-pin the Mi 11 `a660_gmu.bin`, `a660_sqe.fw` and
     `a660_zap.elf` from the stock Android vendor firmware/stock package.
   - Port zeta's A660 GMU cold start, power-up register list, HFI votes and SMMU
     facts into the legacy NativeAdreno driver as Venus board code.
   - Milestone: bounded GPU open, allocation, submit and fence completion.

4. Metal / UI
   - Adapt the iOS 17 NativeMetal/AdrenoMetal plugin to A660 device facts and
     Turnip; validate Metal device creation, IOSurface import and a known
     rendered frame.
   - Milestone: SpringBoard/compositor presents a stable frame.

5. Input
   - Port Venus touch/buttons after the renderer works.

## Required inputs
- Mi 11 stock GPU firmware and vendor files (extract from Android vendor
  partition or a matching stock firmware package; hash and provenance recorded).
- Legacy base UniXNU feeds/submodules compatible with sheng's `unixnu.lock`.
- Venus DTS/ADT facts (already partly in the format-2 work) and the existing
  signed root/Data/owner key.
- No partition write or Android erase is implied by this plan.

## Risks
- Legacy and format-2 code have diverged; ports must be explicit, not assumed.
- Venus's panel/backlight/GOP handoff differs from sheng; display may need its
  own board integration.
- A660 firmware is version- and device-specific; a wrong blob must fail closed.
- The A660 GPU/Metal adaptation is a large stage; the sheng record is A740 and
  zeta is iOS 26.
- Many build/boot iterations and exact-image RAM-boot authorizations will be
  required.

## Original next actions (historical)
1. Create the `ports/UniXNU-venus-legacy` repository skeleton from sheng's
   legacy structure, keeping Venus identity and the existing unixnu layout.
2. Port the format-2 Venus UFS/root/PMGR/ADT code into the legacy kernel build;
   first goal is a baseline legacy kernel that reaches the same root/userspace
   checkpoint without graphics.
3. Only then add GopFramebuffer/display, followed by A660 GPU/Metal.

## Milestone 2026-10-27: first legacy Venus kernel built
- Base: /root/unixnu-build/UniXNU-sheng-base at 8d157ee, submodules initialized.
- Device: ports/UniXNU-venus-legacy with SoC ports/UniXNU-sm8350-common.
- Config: minimal venus_legacy_defconfig (platform/crypto/pthread only).
- Kernel: artifacts/venus-legacy/kernel/kernel.macho, 51023872 bytes, SHA256 0ee15ada2ce2b7fc27f0e2385c8e1521bec5713cca540b38c6c7b800f32a7651.
- The base boot-progress patch required the sheng PMGR hook; sheng-platform-power.patch was inserted before it in the OS series.
- The kernel prelink includes the MobileGraphics roots but does not export IOMobileFramebufferLegacy/MobileGraphics symbols. The sheng display scripts still need the separate native-owner-mobile-graphics prelink candidate.
- Next: add BootProgress/UFS/root/display to the legacy device and resolve that graphics prelink candidate. No device write was performed.


## Milestone 2026-10-27: legacy BootProgress image
- Kernel 2d15e32a... now includes BootProgress after adding the legacy UFS/Virtio/Data/RamBlock/owner-root stubs.
- Payload 4a0525... uses the hardware DTS, 3 GiB ADT, BootProgress args and the high-memory UEFI FD ee2e60af.
- Boot image 21c10a37..., 168960000 bytes, no UFS/root/PMGR/display/GPU; it is a diagnostic image only.
- Next: RAM-boot it to confirm the legacy platform and diagnostic page, then port UFS/root/PMGR and the graphics services.


## Legacy BootProgress phone result (2026-10-27)
- The phone image (21c10a37...) stopped on the DarwinBoot handoff text; no BootProgress page and no return to Android.
- QEMU with the probe synthetic ADT reached _PE_init_platform (pc matched 0x...79a60ec), then faulted in the panic path before _PE_init_printf: ESR 0x96000005, FAR 0x1c8, ELR _current_percpu_base+0xc. The 4K probe check failure is a format-2 assumption, not the boot verdict.
- Fixture-ADT runs using the legacy and format-2 payload ADTs timed out in the loader/entry path; that fixture path is not yet a valid comparison.
- Next: port the working format-2 Venus ArmCpu/ArmDTPlatform/ADT integration into the legacy base, then retest the diagnostic page before UFS/root/display. The phone needs a manual reboot to Android.


## Early-panic follow-up (2026-10-27)
- QEMU at _panic: debug_buf_base=0, debug_buf_size=0, so the panic text was never buffered; the stop is the early exception itself (ESR 0x96000005, FAR 0x1c8, ELR _current_percpu_base+0xc).
- diff of the guide and legacy ArmCpu.cpp showed only line-ending changes; ArmDTPlatform is identical. The component source is not the difference.
- The remaining difference is the legacy base's config/patch/ADT baseline versus the working format-2 Venus kernel. Next: port the complete format-2 Venus UFS/owner/Virtio/PMGR/ADT baseline (and then graphics) into the legacy device before another phone test.

