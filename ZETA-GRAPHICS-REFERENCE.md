# none24smu/UniXNU-zeta graphics reference
Read 2026-10-27 from https://github.com/none24smu/UniXNU-zeta, commit
`eb489285a1d9153872f00c93ebb519a269b249b5`, cloned to
`/root/unixnu-build/UniXNU-zeta-none24smu` and mirrored to
`G:\UniXNU-Port\sources\UniXNU-zeta-none24smu`.

## What it targets
- Microsoft Surface Duo 2 (`zeta`), SM8350, Adreno 660, iOS 26.5.2 / XNU 12377.
- Its graphics stack is mature: NativeAdreno with A660 GMU cold start and
  votes, NativeMetal (metal2vulkan), GopFramebuffer/NativeLegacyDisplay,
  AIR/Gallium evaluation, GPU probes, and extensive hardware evidence.
- The README reports a working iOS Home screen with a black wallpaper and
  SpringBoard alive; this is far ahead of Venus's current SpringBoard SIGTRAP.
- The repository is a device repository, not a standalone driver: the base
  NativeAdreno/NativeMetal sources live in UniXNU, and its patches/package files
  adapt them for zeta.

## Why it is not a drop-in for Venus
- Venus uses the same SoC and GPU family, but its current OS is iPadOS 17.7.11
  (XNU 10063, plain arm64). Zeta is iOS 26 (XNU 12377) and the graphics
  userland patches are named `NativeMetal-ios26.patch`.
- Our guide already has iOS 17 Adreno740/AdrenoMetal/GopFramebuffer components,
  verified on sheng (SM8550, Adreno 740). Zeta instead adapts the iOS 26 base
  driver to A660/SM8350.
- Zeta's display code is for the Duo 2's dual panel; Venus needs a single-panel
  GOP path or its own DSI/DPU integration.
- A660 GPU firmware (`a660_gmu.bin`, `a660_sqe.fw`, `a660_zap.elf`) is not in
  the zeta repository. Zeta obtains hash-pinned copies from its stock firmware;
  Venus needs the Mi 11 equivalents before a real GPU probe can run.

## Reusable pieces
- A660 hardware sequences: `package/ZetaA660HwInit.h`, `ZetaGmu.c/.h`,
  `ZetaGmuVotes.c`, `GpuPowerBoard.h`, `GpuPowerProbe.cpp`.
- NativeAdreno A660 patches for VM/address-space/fence/import/display-drain
  behaviour, subject to porting onto the iOS 17 Adreno740 base.
- Graphics diagnostics and acceptance ideas from GRAPHICS-*.md.
- The method of keeping the current renderer as a control and validating one
  boundary at a time.

## Current Venus facts
- GPT/root/Data and UFS are working; BootProgress reaches 121 processes with a
  3 GiB window and about 1.1 GiB free.
- SpringBoard and liveactivitiesd still exit with signal 5 (SIGTRAP); memory
  pressure is excluded.
- No Adreno/display component is selected in the Venus kernel yet. GOP
  framebuffer drawing works (BootProgress), but no IOMobileFramebuffer or GPU
  service is published to iOS.

## Proposed sequence
1. Recover Android and keep the 3 GiB RAM-boot candidate as the control.
2. Display-only candidate: select/port the iOS 17 GopFramebuffer/legacy display
   path for the Venus GOP framebuffer, without GPU; observe whether
   SpringBoard/backboardd stop trapping and whether an IOMobileFramebuffer is
   published. This is the lowest-risk graphics step.
3. A660 GPU bring-up: extract and hash-pin the Mi 11 GPU firmware, adapt the
   zeta A660 GMU/power sequences to the iOS 17 Adreno driver, and validate a
   bounded GPU open/submit before enabling the compositor.
4. AdrenoMetal A660: adapt the iOS 17 AdrenoMetal plugin to the A660 device
   info and Turnip path; validate Metal device creation, IOSurface import and a
   known rendered frame.
5. Touch/input and UI stabilization after the renderer works.

Each stage needs its own exact RAM-boot image and authorization; no partition
write is implied.

## Build-pipeline blocker (2026-10-27)
- Venus uses the format-2 guide pipeline. Its prelink emits only the native kernel symtab; the original kext symbols (e.g. IOMobileFramebufferLegacy) are not exported. llvm-nm on the Venus prelinked kernel shows only IOService and no IOMobileFramebufferLegacy/IOMobileGraphics symbols.
- The sheng display/GPU scripts bind exact original symbols/addresses from uild/xnu-prelink/native-owner-mobile-graphics-candidate.macho, a legacy-pipeline candidate. Zeta likewise uses the legacy UniXNU build/pipeline.
- Therefore enabling GopFramebuffer/AdrenoMetal is not a config toggle: it needs either a Venus migration to the legacy graphics-capable build or a new format-2 binding/export implementation plus A660 hardware and firmware work.

