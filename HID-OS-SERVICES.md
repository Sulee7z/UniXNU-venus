# HID/AKS initialization and log preparation — 2026-10-28

## Current result

The supplied phone photograph `G:/20261028_091241.JPG` now confirms at 132 s:
`AKS=3/0 opens=4 calls=110`, `HID=3/0/0 res=1 meta=0 start=1/0`, and GPU stage
`a4`. SpringBoard still exits with SIGTRAP and display swap/copy counts remain
zero. These results do not support continuing to attribute the missing UI to
uninitialized AKS/HID/GPU. Physical input and full service correctness remain
separate questions.

The transcribed PC `0x1bd350744` minus slide `0x1df80000` is `0x19f3d0744`.
The deployed 21H461 SystemOS cache maps it into FrontBoardServices, subcache
`.09`, with bytes `00 00 20 d4` (`BRK #0`). The earlier A660 photo's
`0x1b5378744 - 0x15fa8000` gives the same address. This identifies a repeatable
failure site, not its triggering condition or a named local function. See
`evidence/hid-phone.json` and `artifacts/venus-hid-fault-symbolication/`.
Next investigation is the failure path/termination reason and persistent logs,
instead of another speculative component addition.

The HID-enabled kernel builds and passes the 207-slot original IOHIDDevice ABI
audit. QEMU now reads the actual AKS/HID state at owner-root acceptance:

| Observation | Enabled run | Gates absent control |
| --- | --- | --- |
| AKS stage/status | 3 / 0, service non-null | 0 / -1, service null |
| HID stage/load/matching-load | 3 / 0 / 0 | 0 / -1 / -1 |
| IOHIDResource found | 1 | 0 |
| HID metaclass registration | 0 (success) | -1 (not attempted) |
| Device init / attach / start | each observed once, each status 0 | never attempted |

This verifies IOKit initialization, not physical input or a lock screen. The
HID device exposes the offline keyboard/consumer (Home) descriptor. No Venus
touch or physical-button producer, scripted Home press, or digitizer path is
enabled. The resolved ShengNovatekTouch/QcomGeniSpi dependencies are source
dependencies; their board-specific hardware paths are not started here.

The prior assertion that QEMU stops before late-probe initialization was
incorrect. In the current XNU source, `bsd_init.c` calls `bsd_autoconf()` before
`vfs_mountroot()` and the owner-root checkpoint. The new retained-state reads
verify this sequence at runtime as well.

## Candidate

- Image: `G:/UniXNU-Port/artifacts/venus-hid-phone/phone/boot-venus-unixnu.img`
- Boot SHA-256: `96a2c7476da6946261e08993014d96ab866e7e602644a76ad76049afaef5c456`
- Kernel SHA-256: `7a3f0b0952b04d68481af31a2c6821826c1cf9cc4b9f189ea44435a7fa640f79`
- Size: 168960000 bytes; 1 GiB owned; label `hid-001`.
- Enables `offline-hid-input=1 offline-hid-home=1` with the AKS gates.
- Actual ADT, Data seed, trustcache and firmware identities are recorded in
  `artifacts/venus-hid-phone/candidate.json`.
- Host evidence: `evidence/hid-candidate.json`; source/archive snapshots in
  the candidate's `linked-inputs/`.
- The user confirmed Android recovery and authorized one boot of this exact
  image. Fastboot returned Sending 3.696 s / Booting 0.193 s OKAY, total 3.931 s.
  The photograph and runtime observations are in `evidence/hid-phone.json`. The authorization
  has been consumed and the image must not be retried automatically.

## Link fix and visible diagnostics

The failed kernel tried to branch from `NativeHidInput::stop()` to an
absolute-zero `_native_buttons_set_sink`. Weak-address checks do not make an
out-of-range ARM64 branch relocation valid. `DisplayProbeStubs.c` now supplies
callable no-op producer-registration hooks and actual zero-initialized storage
for all `native_touch_*` fields the HID consumer can read. These hooks do not
retain or invoke callbacks. The real HID event/result globals replace their
old absent-symbol definitions.

Row 39 of BootProgress now shows a timestamp and software-only observations:

```text
OS t=... AKS=stage/status opens=... calls=... HID=stage/load/match res=... meta=... start=count/result
```

For successful initialization, expect `AKS=3/0` and
`HID=3/0/0 res=1 meta=0 start=1/0`. Those values alone do not establish
user-space service health or input delivery. On a phone the AKS open/call
counters can show whether clients actually used it. The row respects future
process/cpufreq ownership and the independent pulse; host pixel tests cover
refresh, stride bounds and display yield.

The 150-second photograph of the previous AKS image
`G:/20261028_082939.JPG` still shows SpringBoard SIGTRAP for p152–154 and
`SWAP=0`, with three framebuffer-client opens. Absence of liveactivitiesd or
watchdogd from the last few failure rows cannot prove either recovered.
`evidence/aks-phone.json` records this limitation. AKS/HID as the cause of the
remaining SpringBoard failure is still an unconfirmed hypothesis. CPU-rendered
UI without Metal is supported by the same-OS QEMU reference; Metal is not the
prerequisite being tested here.

## Persistent-log groundwork

Following the [log-capture guide](https://unixnu.com/zh/porting/log-capture),
the exact compiled UFS source and deployed layout were checked, rather than
treating space after the composite root image as automatically free.

- Target is the existing **unixnu** partition, never Android userdata.
- The compiled transport already keeps a **1 GiB tail reservation** independently
  of whether logging is enabled. The persistent Data store ends below it.
- Its existing 32 MiB log window is absolute 4 KiB LBAs
  **[61650688, 61658880)**. Relative to unixnu: skip **16769024**, count **8192**.
- The 256 MiB export region lies directly below it; this is distinct from Data.
- The kernel already exports bounded `native_ufs_log_open/write/sync` and the
  GPT recheck API. The writer is not enabled in the HID candidate.
- Evidence: `evidence/log-layout-host.json`.

Remaining work is the writer's boot-ID/completion-header/sync protocol and an
exact-range reader/decoder, followed by one authorized manual capture cycle.
Neither a new GPT layout nor a change to `sheng-log-reserve` is needed for this
existing reservation. The source audit is not a claim that logs have already
been written or read from the phone.

## Verification commands

From the G-backed WSL workspace:

```sh
python3 ports/UniXNU-venus/scripts/check-a660-live-screen.py
python3 ports/UniXNU-venus/scripts/prepare-venus-a660-phone.py \
  --out-name venus-hid-phone \
  --kernel-sha256 7a3f0b0952b04d68481af31a2c6821826c1cf9cc4b9f189ea44435a7fa640f79 \
  --build-tag hid-001 --aks --hid
python3 ports/UniXNU-venus/scripts/check-venus-hid-candidate.py
python3 ports/UniXNU-venus/scripts/inspect-venus-log-layout.py
python3 sources/UniXNU-guide/scripts/porting-record.py check --device ports/UniXNU-venus
```

Packaging refuses to overwrite an existing candidate. The enabled and disabled
QEMU controls are retained under `artifacts/venus-ufs-root/qemu-hid-phone/`
and `qemu-hid-disabled/`; both use read-only host root disks and GPU mode 0.
