# SpringBoard fault-screen candidate

## Latest: checked FrontBoardServices trap site (2026-10-28)

The HID candidate's photograph `G:/20261028_091241.JPG` shows initialized AKS
with actual client activity, initialized HID, GPU stage `a4`, and continued
SpringBoard SIGTRAP with no display swaps/copies. This supersedes the approach
of treating another absent service as the presumed crash cause.

Unlike the earlier ambiguous photo below, this transcription maps to a real
instruction in the exact deployed SystemOS:

```text
PC    0x1bd350744
slide 0x1df80000
      ------------
      0x19f3d0744  FrontBoardServices, dyld_shared_cache_arm64.09
                  bytes 00 00 20 d4 = BRK #0 (matches ESR f2000000)
```

The earlier A660 photograph's PC/slide pair also gives `0x19f3d0744`.
`artifacts/venus-hid-fault-symbolication/symbolication.json` records source
identity, APFS/cache validation, image mapping and instruction bytes. No local
function name or runtime error message is yet available; a framework trap site
does not establish its underlying cause. Next work is the preceding failure
path and machine-readable error/termination context, supported by persistent
logging. The observations below describe the older candidate.

The `28051b5a...` full-baseline phone run reached owner-root acceptance and
userspace with 1 GiB, but retained three SpringBoard SIGTRAP exit records.
The cause is still unknown.

## Diagnostic gap and implementation

`BootFaultProbe.c` already captures EL0 exception registers and correlates a
bounded frame-pointer backtrace at process exit. `BootProgress.c` retained the
result, but the ordinary page displayed only the short status/signal rows.
The detailed crash records were used by the UI-trace page, post-scanout banner
and BootLog; those paths are unavailable on this baseline.

The ordinary page now uses rows 12-15 for `CRASH 1/4` through `CRASH 4/4` after
a recorded crash. It wraps all 400 bytes without reading past short records,
clears unused continuation rows, and preserves crashes across normal helper
exits and SIGKILLs. Before a crash, the usual PC samples remain visible.

- `src=EL0`: a retained hardware-exception record for that PID. For SIGTRAP,
  the ESR must identify a lower-EL breakpoint, step, watchpoint or AArch64 BRK.
- `src=EXIT`: fallback saved registers of the exiting thread, which need not
  be the thread that originally faulted.
- `PC`, `LR`, `E`, `F`, `+`, `bt`: PC, link register, ESR, FAR, shared-cache
  slide, and bounded frame-pointer backtrace. The slide can help symbolicate
  addresses in the matching iPadOS17 shared cache.

Records can be overwritten, and a captured exception can have a handler.
These observations must be correlated with the process exit; they do not
identify a graphics fault by themselves.

## Candidate and checks

- Image: `G:\UniXNU-Port\artifacts\venus-exit-fault\phone\boot-venus-unixnu.img`
- Bytes: `168960000`
- SHA256: `32e385b546568b6a2b0b20fb2f8b76ac9a0d012a286dd41d446b6fbd0dd3cc65`
- Kernel: `f103ee3b85f4eaa482ca18102e7e65b069d183621a6ff91c73096fa8f10f4a83`
- Memory: **1 GiB**. ADT, Data seed, trust cache and boot arguments are
  byte-identical to the `28051b5a...` phone control; firmware/EFI hashes match.
- `scripts/check-boot-fault-screen.py`: actual C capture/format/layout bodies
  pass ASan/UBSan with explicit kernel-API and pixel-store stand-ins. Includes
  class/PID matching, saved-state mutation, copy failure, contention, record
  wrap, complete backtrace display and retention across 2000 normal/kill exits.
- The compiled source receipt matches the tested files. The new formatter
  strings and file-backed executable diagnostic symbols are in the final kernel.
- QEMU with this kernel, 1 GiB owned memory and read-only OS/SystemOS disks
  reaches `_native_owner_root_accepted_checkpoint`, without timeout. Root is
  read-only, wrong UUID is refused, and two authenticated policy copies exist.
  This is synthetic-hardware root verification, not a desktop or phone test.

Build/export recipe: `scripts/prepare-venus-exit-fault.py`. It preserves the
phone control and refuses to overwrite an already completed candidate record.
Full receipts are in `artifacts/venus-exit-fault/`; the port record is
`evidence/exit-fault-candidate.json`.

## Phone result and static mapping

One authorized Android-to-bootloader transition and RAM boot completed. Sending
(3.757s) and Booting (0.193s) returned OKAY. The user supplied
`G:\43ae1a26-abd0-4064-90a3-ccc6d3726c72~1.jpg`; the page then retained:

- `CRASH 1/4 p149 SpringBoard sig5 src=EL0 PC1a11a43ec LR1a11a42bc EF2000000 F0 +8de4000 bt ...`
- `CRASH 2/4 ...` (the 100-character formatter split the third backtrace word
  `198346b04` across the two rows).
- `root=1`, 118 processes, 1024 MiB, `failures=0`, `integrity=0`.

The photo confirms the new page exposed a real SpringBoard EL0 BRK record. It
does **not** confirm a MediaToolbox fault: the photographed PC maps to
`0x8fd6edf2`, not a BRK instruction, in the matching 21H461 SystemOS cache.
The image names (`MediaToolbox`, `FrontBoard`) are therefore provisional; the
PC, LR or cache slide transcription is not exact enough for a symbol claim.
`dyld_shared_cache_arm64.symbols` is decmpfs type 14 (LZFSE), and local-symbol
decoding failed in this host run, so no local symbol name is claimed.

The user then reported the phone back on Android/black screen. No retry, write
or further phone operation was performed. That authorization is consumed.

## Display ABI audit

`scripts/audit-venus-mobile-graphics.py` audited the current full Venus kernel.
The original `IOMobileGraphicsFamily` executable text matches the sheng
reference (`2e044ee68c1650397e1435234ca6459206262e4c7ed709cb7131c6f664f9bd9b`);
the 358-slot `IOMobileFramebufferLegacy` dispatch, constructor chain, nine pure
slots, generic override set and `newUserClient` ABI all match. Report:
`artifacts/venus-exit-fault/display-analysis/mobile-graphics-legacy-abi.json`.

This establishes a usable original class ABI, not a runtime display instance,
display publication, scanout or desktop. The next host phase is to adapt the
sheng GopFramebuffer/NativeLegacyDisplay recipe to the Venus tree, add its
config/archive and verify it in QEMU before any new exact-image phone request.

## Next

A closer CRASH 1/4 and 2/4 photograph (space-aware wrapping in a future
candidate would also avoid splitting addresses) is needed before the
MediaToolbox/FrontBoard path can be trusted. The display ABI work can proceed
on the host independently. The candidate adds observability; it does not
implement display/GPU support or claim to fix SpringBoard.
