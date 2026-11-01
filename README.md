# Xiaomi Mi 11 (venus)

Format-2 migration following the [UniXNU porting guide](https://unixnu.com/zh/porting/).
Target hardware: M2011K2C, SM8350/Lahaina, 8 GB, 1440x3200.

The user prioritizes iOS bring-up and supplied the official dual-system guide
for evaluation. OS/SystemOS layout and the explicit physical target partition
must agree. The selected plan creates a separate 64 GiB unixnu partition and
reinitializes Android userdata/metadata; concrete device operations still need
their own approval. See `DEPLOYMENT-64G.md` for the built images and checks.
Device writes and partition changes require approval for the specific operation.

## Interrupted iOS26 root flash (2026-10-31)

The root-flash attempt was interrupted. A mistaken64MiB zero-file diagnostic
had already overwritten the old root's start; its old manifest cannot be
treated as intact. The first successful historical recipe used complete
RAW/FILL coverage and `-S 128M`, with67acknowledged transfers. The newer skipped
zero-block transfer was unsuitable and has been superseded by a fully verified
RAW/FILL image and a152fragment bounded recovery plan. No recovery write has
executed. See [IOS26-FLASH-REVIEW.md](IOS26-FLASH-REVIEW.md).

## iOS 26.5.2 native candidate built (2026-10-31)

The iPhone18,2 / iOS 26.5.2 (23F84) inputs were downloaded with ZIP CRC checks,
decrypted, and built into a native XNU 12377.121.6 kernel with the APFS/AMFI/zlib
KDK prelink, a 3,383-image arm64 userland rewrite, a re-signed 84-file shared
cache, a 7,155-entry trust bundle, a Data seed, and a 22.3 GB owner-signed
SHNGROOT image. A 169 MB RAM-boot image is assembled and its container
roundtrip verifies.

The prelinked kernel reaches `bsd_init` through real UEFI/DarwinBoot in QEMU;
the non-prelinked storage kernel does too. No launchd/dyld/SpringBoard execution
has been observed, and nothing was flashed or booted on the phone this round.
See [`evidence/ios26-candidate-host.json`](evidence/ios26-candidate-host.json)
and [IOS26-CANDIDATE.md](IOS26-CANDIDATE.md).

## WSL zeta XNU12377 entry (2026-10-30)

The native XNU12377.121.6 kernel is built (17,097,288 bytes;
21,818,392 unstripped). Newly built UniXNU/DarwinBoot EFI loaders, a QEMU ESP
and a 256-byte random-seed ADT now pass real UEFI handoff and
`arm_vm_init()` return: EL1, MMU enabled, native4KiB pages, no timeout.
See [ZETA-WSL-ENTRY.md](ZETA-WSL-ENTRY.md) and
[`evidence/zeta-wsl-entry.json`](evidence/zeta-wsl-entry.json).
This is an early kernel/VM checkpoint; matching root/Data and userspace remain
to be qualified for this kernel.

## Earlier phone baseline and iPhone work

The user now retains XNU10063 and selects the full UniXNU-zeta reference,
including its ordinary-pointer ARM64e approach; the iOS16/HackiOS route is deferred.
039 corrects plugin cache/format/error handling and packages all original trust
entries plus the two owner binaries in one static module.039 was RAM booted once:
touch is fully normal, with no performance change and Metal apparently inactive.
040 added a bounded post-launch diagnostic written by the plugin itself. It was
booted once; the read-only Data capture found no diagnostic file at any checked
path. That is consistent with the plugin never being reached, but filesystem
denial is not excluded. 041 adds a prelaunch GPU/Metal status file so the next
boot can distinguish accelerator publication failure from post-launch plugin
reach; it is host-verified and not booted.
For the iPhone target, the complete iPhone11,8 iOS17.7/21H16 OS/SystemOS,
DeviceTree, kernelcache and trust inputs are checked, and a 9.59 GiB SHNGROOT
image was built with volume UUID1104DA02-BEB4-484A-80C1-584C109E73F1. The target
kernelcache is MH_FILESET arm64e and has no classic
`_PrelinkLinkKASLROffsets`; XnuPrelink's classic pointer-table model cannot emit
a loadable image from it. A fileset unprelink/relink converter is required before
a matching Data seed and QEMU candidate. See
`evidence/iphone17-fileset-prelink-audit.json`.

038 prepares four-core startup (boot affinity0 plus0x400/0x500/0x700), correcting
the reset vector's lost Affinity1. QEMU observes four available CPUs and timer
dispatch return; per-core timer/IPI and device performance are not fully qualified.
The user also selected a full iPhone target. iPhone X iOS16.7.16 inputs/profile
and the7.80GiB root image are prepared and hash-checked; the matching native16
kernel, driver ABI and Data seed remain to be migrated. See
[CPU-038-AND-IPHONE.md](CPU-038-AND-IPHONE.md).

035 source audit corrects the mistaken FocalTech identification: the vendor
fts_spi driver is STMicroelectronics. The old codec reversed motion (0x23) and
lift (0x33), and the GPIO helper failed to clear the reset output latch. These
bugs now have raw-frame/GPIO regressions, with an old-source failing control.
The STM transport, reset-ready/scan-echo checks and mainline HID bridge are
rebuilt. The user confirms physical touch works after the exact035 boot
(`db727796...`); see `evidence/touch035-phone.json`. Individual multitouch cases
are not separately qualified. GPU work now uses035 as the touch baseline.
See [TOUCH-035-AUDIT.md](TOUCH-035-AUDIT.md).
Earlier prelaunchd snapshots cannot establish what happened to user input after launchd.

036 fixes the missing original `IOAcceleratorES` Metal discovery adapter, using
the matching iOS17 ABI and deferred registration. GPU startup is ordered before
launchd; exact035 touch code is retained. ABI/publication failure tests, native
build, prelink and signed-addon/image checks pass.036 was RAM booted once;
the user reports severe lag. GPU/Metal enable arguments are present, but actual
UI GPU rendering remains unmeasured. See [METAL-036-DISCOVERY.md](METAL-036-DISCOVERY.md)
and `evidence/gpu036-render-path-review.json`.

Metal and own ST implementations now compile/link. Touch014 exposed a premature
`__mod_init_func` metaclass registration; it is fixed with the ShengHidInput
late-initializer pattern, and Touch015/Metal016 are rebuilt from kernel
`87145de7...`. QEMU default-off and mode1 pass. Exact phone validation is pending.
See [`TOUCH-015-FIX.md`](TOUCH-015-FIX.md) and
[`METAL-TOUCH-013-014.md`](METAL-TOUCH-013-014.md).

The user now confirms the exact012 run reached the system welcome page. The
012 image/kernel and cache repair are retained as the UI baseline. New work is
the requested none24smu/zeta-derived A660 Metal path and a self-written Venus
ST touch driver; hardware rendering/touch and cache-detail readback remain
separate gates. See `evidence/welcome-baseline-012.json`.

The011 readback left the original cache unchanged. Actual APFS reproduction now
identifies the old cache's unowned UID(-2)/mode0 being rejected by our guard.
The012 repair recognizes only that exact shared-cache case and keeps journal/
backups under protected Data db storage, away from early /tmp cleaning.
Real QEMU APFS rename (moved1/missing6), C failure tests and image checks pass;
The exact012 image was then authorized and RAM booted once; protected status,
backup and fresh hardware MG/UI results await readonly retrieval.
See [`SCALE-REFRESH-012.md`](SCALE-REFRESH-012.md).

The011 targeted scale repair now applies the documented MG cache invalidation
after original startup policy, saving exclusive backups and durable begin/end
status before normal launchd. Actual C failure models, SystemOS checks and a real
QEMU Data/sync-refusal checkpoint pass. Its exact image was authorized and RAM
booted once; journal/backup/fresh-cache/UI results await readonly retrieval.
See [`SCALE-REFRESH-011.md`](SCALE-REFRESH-011.md).

The010 original-chain phone readback now verifies matching launchd boot args,
early boot/bootstrap and disabled watchdogd while the user reports continued
counters. It records19 SpringBoard SIGTRAP exits and5 real PID-matched IPS
reports at the same FBS display-mode initialization BRK. Display scale remains
the current blocker; UI/MG API success is unmeasured.
See [`SHENG-CHAIN-010-RESULT.md`](SHENG-CHAIN-010-RESULT.md).

The official sheng startup-chain review now confirms the shared init order and
original watchdog policy are already reused. A010 control preserves the proven
4b1 kernel/normal launchd chain and adds two supported original policies:
kt_fixed_zones120 and disabled watchdogd. New QEMU/input/container checks pass;
One exact010 RAM boot has now been authorized and executed; device UI/policy/log
result is pending. See [`SHENG-STARTUP-CHAIN.md`](SHENG-STARTUP-CHAIN.md).
009's readonly capture verifies installation and a subsequent kernel policy
write, but has no journal/API output or new launchd logs; its later stage is unknown.

The latest evidence-first recheck found a real forensic-reader EOF bug: the
MobileGestalt plist is7477 logical bytes, with8192 bytes allocated; it is valid.
All three retained captures contain the same cached MainScreenStaticInfo with
scale0. An actual MG API helper is now built/signed/page-hash verified and packed
as the008 single-query candidate. After its one authorized boot, a stable readonly
Data capture verifies both installed files against payload hashes, but neither
JSON nor stderr exists. The matching008 boot-args log reaches normal launchd
bootstrap; the deployed signed launch cache contains561 full service definitions
and excludes the new job. Directory-only job activation is unqualified, so the
next step is an explicit execution path. Actual MG API values remain unmeasured.
The009-r2 activation repair now uses an opt-in readonly union for the existing
prng_seedctl early task. Its wrapper immediately executes the exact original,
while one bounded mobile query saves a separate launch journal and report.
Host process/mount tests and rebuilt-kernel SystemOS/AKS/HID checks pass;
One exact009-r2 RAM boot has now been authorized/executed; device task/API
results await readonly retrieval. See [`MG-TASK-ACTIVATION.md`](MG-TASK-ACTIVATION.md).
See [`MG-QUERY-OBSERVATION.md`](MG-QUERY-OBSERVATION.md). The user-supplied
iamOJZ/haydn reference is pinned and reviewed in [`HAYDN-IAMOJZ-REFERENCE.md`](HAYDN-IAMOJZ-REFERENCE.md).

The current lock-screen candidate addresses the photographed zero-scale mode:
the boot ADT now provides display-scale2/rotation0, and an opt-in pre-launchd
helper preserves the three documented MobileGestalt cache files under exclusive
backup names so the OS can query fresh values. Actual build, cache/pixel host
tests, 6GiB QEMU SystemOS/AKS/HID and payload checks pass. Its one authorized
phone run is now confirmed stalled at2s/SystemOS entry, before any observed
cache operation. The storage object and bindings still match the qualified
Data002 inputs. A narrower002 control keeps the earlier phone-tested kernel
with the early-scale ADT; it is prepared but not phone-tested. See
[`LOCKSCREEN-SCALE.md`](LOCKSCREEN-SCALE.md).

The active work now follows the official prerequisite order. The first pass
aligned the board's full-root/1 GiB defaults, moved sRGB into the consumed ADT
table, and repaired the active base converter's missing phandle/arm-io fixes.
Real Android-side reads also verified the existing Data store header/bitmap.
Controlled Data002 write/reboot/readback has now passed on the phone. CPU
frame/swap and physical input are the next stage gates. See [`ORDERED-BRINGUP.md`](ORDERED-BRINGUP.md).

The normal userspace candidate now removes the Data-test pause and uses the
same phone-qualified kernel/ADT/seed/trust/firmware. Its payload and boot checks
pass. Its exact image was authorized and RAM booted once; photographs show
launchd signature acceptance and process growth from1 at34s to86 at about87s.
The latest page still has zero swaps/copies, watchdogd SIGTRAP and FDR-loader
exit1; a lock screen or desktop has not been observed.
See [`USERSPACE-BOOT.md`](USERSPACE-BOOT.md).

The user confirmed that the87s page remained frozen. The configured continuous
recorder does not intentionally stop there. The6GiB normal-boot candidate and
matching expanded-memory firmware passed host/QEMU checks. A later phone photo
reports6144MiB, root acceptance and124 processes at172s, but still shows
SpringBoard SIGTRAP, zero swaps/copies and no UI. The photo does not independently
identify the full boot-image SHA or show progress after capture. See
[`MEMORY-6G.md`](MEMORY-6G.md).

The paired Data test passed same-boot write/reopen but failed after restart:
the read image returned ENOENT for the marker. The disk previously published
its seed before attaching the persistent overlay. A restored-before-publication
fix now passes host regression, storage ABI, full-kernel build and QEMU root
controls; its initial phone attempts are described below. See
[`DATA-QUALIFICATION.md`](DATA-QUALIFICATION.md) and [`DATA-PUBLICATION.md`](DATA-PUBLICATION.md).
The user has now returned and authorized the exact recovery image once.
The recovery001 photo and user confirmation show a stall at SystemOS mount
entry at2s, before the Data test. A second correction now defers persistent
Data publication until the original post-SystemOS selection path. Its model,
190-slot ABI, full build, actual QEMU SystemOS mount and image checks pass;
recovery002 then passed SystemOS/Data mount progression on the phone but still
returned ENOENT for the old marker. The new controlled test below now passes.
See `DATA-PUBLICATION.md` and `UFS-GUIDE-RECHECK.md` for the official UFS stage
review and the missing physical-write/recovery evidence.

The next paired test adds verified Data/parent/file identity, parent-directory
and full filesystem sync, a real UFS cache-sync command and persistent-write
counters. It uses a new exclusive53-byte file. The full build, core/pixel tests,
QEMU SystemOS control and paired-image checks pass. Its exact write image was
authorized and RAM booted once. The four diagnostic rows confirm matching
Data/parent/file identities, all sync results0, persistent writes0→32 and
successful53-byte reopen comparison. The confirmed-restart read round also
passed at63s: the same53 bytes match, store is resumed and read-interval write
counters stay unchanged. This completes the bounded file-persistence gate.
See `DATA-SYNC-QUALIFICATION.md`.

CPU copy checks now also cover the real 1440x3200 geometry, and target DSI
brightness, ST SPI firmware names and PMIC button connections are recorded in
[`DISPLAY-INPUT-FOUNDATION.md`](DISPLAY-INPUT-FOUNDATION.md). Actual frames,
swaps, brightness and physical input remain unverified.

**This is a partial device port.** UFS/root and bounded A660 bring-up have
phone evidence; physical touch/buttons, motion/light/proximity sensors,
battery telemetry and several peripheral backends remain unimplemented.
See [`DRIVER-COVERAGE.md`](DRIVER-COVERAGE.md) for the exact tested-image audit.

The SpringBoard trap has now been traced to the original FrontBoardServices
error **"FBSDisplayMode cannot be configured as requested"**. A targeted
diagnostic candidate records the rejected mode object's source-verified fields;
the particular invalid field is still unknown. See
[`FRONTBOARD-DISPLAY-MODE.md`](FRONTBOARD-DISPLAY-MODE.md).

The latest HID/AKS candidate passes real QEMU service-initialization and
default-off controls. Its live diagnostic row exposes both service states.
The preceding AKS-only phone run still showed SpringBoard SIGTRAP and zero
swaps; it did not establish that other daemons recovered. See
[`HID-OS-SERVICES.md`](HID-OS-SERVICES.md) for the new candidate and the
source-verified, already reserved unixnu log window.

The A660 backend/firmware dependency closure builds against iOS17. The
2026-10-28 `a660-live` candidate fixes the old frozen GPU diagnostic row and
uses kernel-owned trace memory instead of a retained Duo 2 physical address.
Host pixel regression and QEMU owner-root/display control pass. One authorized
phone RAM boot completed the kernel GPU bring-up through GMU cold start, GX
power-on, ZAP, a CP write, service publication and two user-client submission
rounds; the old `stage=0/calls=0` photographs were stale pixels. Metal, display
scanout and a desktop remain unverified, and SpringBoard still exits with
SIGTRAP. See [`A660-LIVE-DIAGNOSTICS.md`](A660-LIVE-DIAGNOSTICS.md) and
`evidence/a660-live-phone.json`.

The complete `venus_ufs_root_defconfig` build against the locally adapted
sheng-base `8d157ee18ae9c4d518aba28cb3040a84e860dcd1` has now reached owner-root
acceptance and iPadOS userspace on the phone. The `legacy-full` experiment name
does not change its schema-2 device configuration. Image `28051b5a...` reports
1024 MiB, 112 processes and zero UFS failures/integrity failures; SpringBoard
still exits with SIGTRAP. A usable desktop and Data persistence across reboot
remain unverified. See `evidence/legacy-full-phone.json` and
`LEGACY-MIGRATION.md` for the exact image and photograph.

The host-verified candidate (`32e385b5...`, 1 GiB) exposes the retained crash
registers/backtrace on the ordinary diagnostic page. Its authorized phone run
did show a SpringBoard EL0 BRK, but the transcribed PC does not land on a BRK
instruction in the matching cache; MediaToolbox/FrontBoard is provisional, not
a root-cause conclusion. See `SPRINGBOARD-FAULT-DIAGNOSTICS.md`.

A static audit of the current full Venus kernel now confirms the original
`IOMobileGraphicsFamily` text and 358-slot `IOMobileFramebufferLegacy` ABI match
the sheng reference (`2e044ee6...`). The real display archive is now linked into
kernel `394b4dce...`; QEMU still reaches the owner-root checkpoint and reports a
started `NativeLegacyDisplay` with an 800x600 GOP. The presenter is not ready and
no client or frame is observed; this is not a panel/compositor/desktop result.
See `evidence/display-abi-audit.json` and `evidence/display-qemu-instance.json`.

The exact display-enabled image `279526f1...` was also RAM booted once. It
stopped on a BootProgress page with only top/bottom content; no SpringBoard,
desktop or presented frame appeared. No partition was written and the image was
not retried. See `evidence/display-phone-result.json`; the phone needs a manual
return to Android.

### Earlier checkpoints (historical)

The legacy native-XNU pipeline reached actual kernel entry, MMU enable and
`arm_vm_init` return on the phone. These observations are retained in
`VM-INIT-PROBE.md`. This format-2 configuration has a different profile and
hardware description and must be validated independently.

The initial OS/ABI target is the guide's `ipados-17.7.11-21H461` profile,
which matches XNU 10063.141.1. It selects iPad7,1/J120 Apple components as
ABI inputs. It does not establish an iPhone UI identity or a booted userland.
Generic platform/CPU, SoftwareAES, XnuPrelink and DarwinBoot are selected.
SM8350 UFS now has a device-verified bounded DMA/read path. Root-media
integration, Adreno 660, touch and other board services remain pending.

The official native-kernel build and Apple-component prelink have now passed.
The 51011584-byte candidate is exported to
`G:\UniXNU-Port\artifacts\venus-guide-linux\kernel\kernel.macho`, SHA256
`8d7a798ed7971fae50e7ec938859d8d34414e37a801aaabab525a5884f6526c6`.
It includes the profile's APFS/storage/display/HID service components. QEMU
has now verified platform/BSD entry, original crypto/PRNG initialization and
timer-interrupt return. APFS component loading returned success; root mount
remains unverified. See `PRELINKED-RUNTIME.md` for the new logger-enabled phone
candidate and its pending hardware test.

The current PMGR candidate is documented in `ZETA-REUSE.md`. Its original
ApplePMGRNub lifecycle/publication and AMFI call path passed QEMU, and both
the kernel and final payload reached IOFindBSDRoot. The zeta SM8350 UFS
implementation has been pinned and compared with Venus's own hardware inputs.

The PMGR candidate was also RAM booted on Mi 11. Its screen reached
`Failed to mount root device` at IOKitBSDInit.cpp:984 after the matching wait,
passing the former AMFI PMGR stop. The immediate next milestone is publishing
a real UFS root device and supplying the matching volume, not more entry probes.

`DUAL-SYSTEM-SHENG.md` records the read-only GPT/F2FS findings and the current
storage ABI work. Both explicit `unixnu` and `userdata` UFS diagnostic archives
compile and bind to the measured iOS17 ABI. They are not yet linked into a
phone kernel or qualified for root I/O.

The next isolated kernel, `venus_ufs_defconfig`, now links a read-only register
survey. Its compiled start path rejects root and transfer modes and reports
clock, queue and SMMU state through the panic screen. See `UFS-SURVEY.md` for
the current candidate and tests. The phone survey returned err=0 with a ready
UFSHCI3.0 controller, idle queues and a unique SID e0/context2 mapping. Actual
DMA/storage-command and block-read qualification is the next step.

`venus_ufs_read_defconfig` builds the isolated capacity/GPT candidate in
`UFS-BLOCK-READ.md`. Its phone run completed 9 commands and 5 GPT reads; capacity,
primary/backup CRCs and the primary-header SHA256 match retained Android blocks.
The next milestone is integrating the selected OS/SystemOS/Data layout and
actual root-media publication and mounting.

## Local prerequisites and commands

The active WSL build uses `/root/unixnu-build/UniXNU-sheng-base` at
`8d157ee18ae9c4d518aba28cb3040a84e860dcd1` plus recorded local adaptations,
including `patches/tools/adt-handoff.patch`. Use Python 3.11+, dtc, mtools and
the existing Linux XNU toolchain. The local SM8350 source remains selected by
`local.toml`. See `ORDERED-BRINGUP.md` before preparing a fresh base checkout.

Current full-root configuration commands:

```sh
python3 /root/unixnu-build/UniXNU-sheng-base/unixnu defconfig venus_ufs_root_defconfig -D /mnt/g/UniXNU-Port/ports/UniXNU-venus --out /root/unixnu-build/venus-legacy-full
python3 /root/unixnu-build/UniXNU-sheng-base/unixnu status --json -D /mnt/g/UniXNU-Port/ports/UniXNU-venus --out /root/unixnu-build/venus-legacy-full
python3 /mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/check-stage-foundation.py
python3 /mnt/g/UniXNU-Port/sources/UniXNU-guide/scripts/porting-record.py check --device /mnt/g/UniXNU-Port/ports/UniXNU-venus
```

Use `scripts/check-venus-hardware.py` to compile and compare hardware against
the retained live FDT before generating ADT with the shared `scripts/make-adt.py`.
`porting.toml` records the current work and remaining inputs. `GUIDE-REVIEW.md`
records the guide review and migration decisions.

Before a complete build, resolve source pins, audit the updated firmware
RAM-disk/Advanced Logger integration, supply kernelcache/ABI/trust-cache and
Data inputs, and verify userdata geometry. The local SoC has no published
revision. A successful configuration check is not a complete OS build.

`sources/UniXNU-guide/unixnu.local.toml` now saves the device, fast WSL output,
UEFI and kernelcache paths. From that checkout, subsequent official commands
can use those saved inputs. Set `UNIXNU_TOOLCHAIN=/root/unixnu-toolchain` for
Linux kernel builds. `tools/build-venus-guide.sh` also exports kernel/logs to G:.
