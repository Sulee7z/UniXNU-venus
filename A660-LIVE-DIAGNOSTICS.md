# A660 live diagnostics and reference comparison — 2026-10-28

## Result

The A660 backend and its 24 dependency units compile and link against the
Venus iOS17 kernel. The new candidate fixes the stale diagnostic row and
removes a retained Duo 2 physical trace address. Host framebuffer regression,
package identity checks and the QEMU owner-root/display control pass. One
authorized phone RAM boot then completed the whole kernel GPU bring-up on the
A660: power/clocks, GMU context, command DB/votes, firmware cold start with HFI,
GX power-on, GPU context/SQE/ring/CP init, the ZAP shader, a CP write through
the GPU context, service publication and two user-client submission rounds.
Metal (user space), display scanout and a desktop are still pending.

Candidate: `G:/UniXNU-Port/artifacts/venus-a660-live-phone/phone/boot-venus-unixnu.img`

- Boot SHA-256: `9b1be886d5a934499f4f4659830f51146685c69f60412e1d46e520feaa6d1f32`
- Kernel SHA-256: `e9481d2ac32006d1e074651162a695202705f2ea6dd8eb8a14c73366f3179a47`
- Boot size: 168960000 bytes; owned memory: 1073741824 bytes (1 GiB).
- Build label: `a660-live`; GPU mode: 9. GPU scanout handoff remains mode 0.
- ADT SHA-256: `2efc31683ac0f63582b26b55fbf634a5ef0ab8c2552178a589a824bf606cacd7`.
- Candidate, source snapshots and archive receipts: `artifacts/venus-a660-live-phone/`.
- Host evidence: `evidence/a660-live-candidate.json`. Phone evidence:
  `evidence/a660-live-phone.json`, photograph `G:/20261028_074705.JPG`
  (SHA-256 `331d80f5ad8478471a52d9c178d453777f7ab4ee54c37e7688b26b8bde573d3e`).
- The candidate was RAM booted once after the user confirmed Android recovery
  and authorized this exact image: Sending 3.692 s, Booting 0.194 s, one
  attempt, no retry, no partition write. Each later phone reboot/RAM boot again
  needs its own exact-operation authorization under `AGENTS.md`.

### Phone reading at t≈99 s

| Row | Result |
| --- | --- |
| power | `mode=9 map=1f gcc/cc/smmu/gpu=1/1/1/2 io=0 CX=f8228800>f8228800 GX=00222001` |
| GMU context / clocks | `step=7 st=0 kit=0/0 id1=30000007`, `CLK read=1 step=6 fail=0 cfg=3` |
| command DB / pre-cold GMU | `ver=1 parse=0 bin=0 build=0`, `reset/gen7/busy/hfi=1/0/0/0` |
| cold start | `st=0 at=6.1 hash=1 blocks=15 init=00000100 ready=1/1 fault=00000000/00000001` |
| HFI / GX | `step=8 ack=c6 err=0`, `vote=0/0 polls=2 state=000000c0>00000000 rbbm=00000001` |
| GPU / CP / ZAP / publish | `step=10 sqe=0 init=0/0 wr=0/0 word=5e9a660 ZAP=9/0/0/0/0 pub=0 rounds=4/4` |
| summary row | `GPU A660 t=99s stage=a4 calls=1 requested-mode=9` |

`rounds=4/4` means both independent connections allocated BOs, mapped them,
took CPU views through `clientMemoryForType`, submitted three CP_MEM_WRITEs and
their fence, and found all three written dwords plus the untouched guard dword
in the client mapping. The userspace still showed `DISPLAY stage=10`, `SWAP
calls=0`, `CLIENT calls=2` (`IOMobileFramebufferUserClient`) and the retained
SpringBoard/watchdogd SIGTRAP exits, so publication did not by itself create a
frame, a desktop or a working render server.

## Correction to the old photographs

The diagnostic added to the `diag`, `delay`, `strong` and `calls` images used
row 47. `BootProgress.c:line()` captures that row's text but skips its pixel
stores after `pulse.ready` becomes 1. The early `stage=0 calls=0` pixels can
therefore remain after the probe advances. The first A660 image had no GPU row.

The old photographs do **not** prove that the GPU probe was uncalled, that
boot arguments were cached too early, or that weak imports resolved to zero.
Nor do they demonstrate successful GPU execution. The late-probe call chain
and shared stage address were verified in the final kernel, which establishes
linkage rather than a phone execution trace. The interpretation in
`G:/UniXNU-Port/evidence/a660-phone-diagnostic.json` has been corrected while
retaining the original photograph transcription and image identity.

## Implementation

`BootProgress.c:draw_gpu()` uses rows 24–29 for power, GMU context/clocks,
command DB/GMU state, cold start, HFI/GX, and CP/ZAP/publication. Row 41 gives
the paint time, stage, display-to-GPU call count and requested mode. The
independent pulse keeps its reserved row 47. When `BootProcessProbe` is linked,
the GPU layout yields these rows instead of overwriting the process display.

`GpuPowerProbe.cpp:native_gpu_diagnostic_row()` formats retained software
fields. It performs no MMIO, allocation, service calls or locks. These are
individual samples during progress, not an atomic multi-field snapshot. A zero
field alone is not completion; `ffffffff` in DB/cold/publication status means
not attempted. The `t=` field distinguishes a new paint from an old image.

The reference cold-start trace still mapped `0x8b51a000`, a Duo 2 reserved
address. Venus now uses an 8192-byte CPU-only kernel BSS buffer, verified in
the final image. It no longer tries to read a previous boot's trace. The
buffer is separate from the Mi 11 ZAP region at `0x8e71a000`; this change makes
no cross-boot persistence claim. There is no evidence showing whether the
old phone runs reached the foreign trace address or whether it caused a fault.

The previous delayed mode-reading behavior remains in this candidate to keep
that variable stable. It is not a confirmed fix for the old zero text.

## Verification

From the G-backed WSL environment:

```sh
python3 /mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/check-a660-live-screen.py
python3 /mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/prepare-venus-a660-phone.py \
  --out-name venus-a660-live-phone \
  --kernel-sha256 e9481d2ac32006d1e074651162a695202705f2ea6dd8eb8a14c73366f3179a47 \
  --build-tag a660-live
python3 /mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/check-a660-live-candidate.py
```

The packaging command refuses an existing candidate; these are provenance
commands, not instructions to overwrite the saved artifacts.

- ASan/UBSan executes the actual row gate, GPU layout and pixel painter. It
  reproduces the old capture/pixel discrepancy, verifies repaint after pulse
  anchoring, process-row ownership, stride padding and scanout yield. The GPU
  state provider is substituted in this host test; no hardware is simulated.
- Actual iOS17 archive/kernel build and prelink pass. Required diagnostic,
  late-probe, GPU and publication symbols resolve; current source hashes match
  compiled receipts. The non-selected `NativeAdrenoKernelTime.cpp` still lacks
  `ShengGmu.h`; it is outside the required A660 closure.
- QEMU reaches `_native_owner_root_accepted_checkpoint`, without a bounded
  timeout, using read-only OS/SystemOS images and `sheng-gpu-power=0`.
  `NativeLegacyDisplay` init/start/probe_match are 1, GOP is 800×600; there is
  no rendered frame or desktop result.
- Firmware/EFI, Data seed and trustcache match the existing control. All
  original ADT nodes/properties are compared after removing the three added
  firmware properties. The injection JSON is now actually saved. Payload
  arguments are read back and compared; the final boot container round-trips.

Logs: `logs/venus-a660-live-kernel.log`,
`logs/venus-a660-live-phone-prepare.log`. Screen report:
`artifacts/venus-a660-live-checks/screen-report.json`.

## What sheng/zeta do differently

| Item | Confirmed Venus difference / next check |
| --- | --- |
| Diagnostic transport | sheng uses extension rows; zeta A660 logs through its USB/log infrastructure. Venus needs ordinary-page rows because its banner is disabled and XNU USB logging is unavailable. |
| BootProgress build | Although it is absent from Venus's explicit archive list, `build-xnu-4k-baseline.sh` invokes the boot-progress builder. The compiled receipt matches the new Venus source; this is not a missing archive. |
| AppleKeyStoreState | sheng links `KeyStoreProbe.cpp` and the deferred `NativeKeyStoreEvents` initializer, with `offline-key-events=1 sheng-aks=1`. Venus still has an empty probe. This is a state/notification-only compatibility service, not keys, keybags or data protection. Its causal relation to Venus SIGTRAP is unproven. |
| HID | sheng links the HID component and probe. Venus has an empty probe and the assembled component is absent. The current original IOHIDFamily text matches `7e4c5104…`; the 207-slot dispatch, constructors, report path and board input source still need qualification before use. Matching text alone is insufficient. |
| ADT product/buttons | The saved Venus ADT has P3, no `thin-bezel`, and no `/buttons`. `artwork-display-gamut` is misplaced at `[adt]`; the converter consumes `[adt.product.string]`. sheng uses sRGB and an explicit hold/volume button description. The diagnostic candidate preserves the control ADT so these remain a separate platform change. |
| DRAM attributes | Venus advertises the real upper bank `0xc0000000 + 0x1c0000000`; zeta describes a wider DRAM envelope. This is distinct from the 1 GiB owned window. Current XNU `wimg_to_pte()` consults `is_dram_addr()` for IO/posted mappings, but its WCOMB branch does not. The command DB is intentionally copied with aligned 32-bit Device reads and ZAP uses write-combined mapping; a lower address alone does not establish the failure cause. Check actual attributes before changing the bank description. |
| Text fixups | All four entries in the saved ADT exactly match the selected 21H461 OS profile. Their presence is verified; runtime application and any relation to SIGTRAP are not. |
| Watchdog policy | The implementation is compiled, but sheng's `sheng-disable-watchdogd=1` gate is absent. `sheng-lite=1` does not replace it. Enabling the policy would write the existing Data launchd policy and needs a separately described experiment. |
| Metal and scanout | Kernel service publication is only one step. Venus still needs the matching user-space plugin/Turnip/compiler path, successful commands/fences/known pixels, and validated display handoff. |

References: `sources/UniXNU-sheng-legacy` (same iOS17 profile),
`sources/UniXNU-zeta-none24smu` (same SM8350/A660, different iOS/XNU ABI),
`sources/UniXNU-zeta-base` commit `35c384e84266343991fd14706e8c651f7d2e09ed`,
the local resolved XNU10063 source, and
[the official GPU guide](https://unixnu.com/zh/porting/gpu).

The phone's qfprom fuse at `0x784000+0x17b` read 0 on this unit, and the live DT
contains a bin-0 power-level table; the DB parse and vote build succeeded with
bin 0. The earlier "speed-bin 4" expectation was not confirmed by this unit's
fuse and must not be used for calibration. The Mi 11 bin-4 table remains in the
board source for units whose fuse reports 4.

The same-OS QEMU reference explicitly documents CPU rendering with no Metal
device. This supports continuing CPU-display diagnosis before Metal. The
QEMU/tb128fu board notes describe a missing-AppleKeyStore wait chain through
liveactivitiesd/chronod/SpringBoard. That motivated the AKS experiment; similar
photo symptoms did not establish that this was Venus's actual cause.

The AKS-only phone result is now available: at 150 s, SpringBoard p152–154 still
exit with SIGTRAP and swaps remain zero (`evidence/aks-phone.json`). The bounded
recent-exit tail does not establish that other daemons recovered. The next
HID candidate adds the offline keyboard/Home device and explicit live service
state. Its QEMU enabled/disabled controls verify real AKS/HID initialization,
not a phone lock screen or physical input. See `HID-OS-SERVICES.md` for exact
identities, evidence and the verified existing log reservation. Metal and GPU
handoff remain later work; HID as the remaining crash cause is unconfirmed.
