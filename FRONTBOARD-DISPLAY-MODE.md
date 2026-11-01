# FrontBoardServices rejects a display mode — 2026-10-28

## Latest: zero scale captured (2026-10-29)

The later `G:/20261028_234010.JPG` already exposes MODE fields; the earlier
handoff missed them. It reads width1440/height3200/preferredScale0/override0,
120Hz/gamut1/HDR0/rotation0/virtual0. PC minus slide again equals0x19f3d0744.
The original initializer rejects the simultaneous zero preferred/override scale.
See `LOCKSCREEN-SCALE.md` for the exact QuartzCore/MobileGestalt/DT reading path,
the prepared scale-and-cache candidate, and the remaining runtime uncertainty.
The older candidate and its initially pending observations below are historical.

## Confirmed from the deployed 21H461 SystemOS

The photographed PC/slide maps to FrontBoardServices at unslid `0x19f3d0744`,
where the original bytes are `00 00 20 d4` (`BRK #0`). The surrounding failure
branch references:

```text
FBSDisplayMode cannot be configured as requested : %@
```

The same message also appears on the adjacent assertion path with source name
`FBSDisplayMode.m` and line 112. The actual photographed path is the mode
initializer's fatal-validation branch. Its caller invokes:

```text
_initWithWidth:height:preferredScale:scaleOverride:refreshRate:gamut:hdr:rotation:virtual:validityCheck:
```

The caller at `0x19f3e1f88` passes validity-check policy 1. The initializer at
`0x19f3d0500` validates the arguments and the branch for policy 1 leads to the
message and photographed BRK. This is stronger evidence than a generic missing
service hypothesis. It does not yet identify which supplied field is invalid.

Source is the read-only SystemOS image with SHA-256
`b4908cde41d23e6bc05e6af51a2c9eeb00cf0f863a6a18b1600c96a3fd70414f`.
Analysis: `artifacts/venus-frontboard-failure/frontboard-inspection.json` and
the address-annotated instruction/caller windows alongside it. Data pointers
are decoded using the cache's recorded slide information. Optimized relative
method-list names are left unresolved; the selector above comes from the
caller's actual Objective-C stub/selector reference.

## Targeted observation

Original Objective-C ivar metadata and initializer stores agree on this layout:

| Field | Offset | Bytes |
| --- | ---: | ---: |
| width / height / preferredScale | 8 / 16 / 24 | 8 each |
| scaleOverride / refreshRate | 32 / 40 | 8 each (double bits) |
| gamut / HDR / rotation | 48 / 56 / 64 | 8 each |
| virtual | 72 | 1 |

The initializer keeps the object in callee-saved `x19`, including through this
error path. The new diagnostic reads its first 80 bytes at ordinary process
exit, using the previously retained exception registers. It is gated to
SpringBoard, SIGTRAP, ESR `f2000000` and the exact unslid PC. No user-memory read
is added to the exception handler. A failed copy reports its error and leaves
the original crash/backtrace available.

The ordinary CRASH rows will include:

```text
MODE w=... h=... p=... so=... hz=... g=... hdr=... r=... v=...
```

`so` and `hz` are hexadecimal IEEE-754 double bits, not literal Hertz or scale
values. This avoids floating-point operations in kernel code. These are the
stored object fields; the initializer may normalize scaleOverride, so an
inconclusive snapshot still requires further argument/log tracing.

## Candidate and checks

- Image: `artifacts/venus-frontboard-mode-phone/phone/boot-venus-unixnu.img`
- SHA-256: `b31baa584619f9b9909103b1c691b2723a6a99be83f60360abeedcc4dd78ed7c`
- Kernel SHA-256: `9334d42b3775d7e75e89d3d338d8429c64422b32a1f18a9c9eb659ba04c30a6f`
- Tag `fbs-mode-001`; 1 GiB owned; 168960000-byte boot image.
- Functional arguments, ADT, Data seed, trustcache and firmware match the HID
  control. This change collects data; it does not change mode values or bypass
  their validation.
- ASan/UBSan checks the actual recorder, matching/mismatched exception gates,
  saved-register retention, bounded object read, copy failure, output bounds,
  and the actual four-row crash layout.
- Kernel build passes; QEMU reaches owner-root acceptance and AKS/HID initialize
  successfully. QEMU does not exercise the SpringBoard failure.
- Evidence: `evidence/frontboard-mode-candidate.json`.

The user confirmed Android recovery and authorized one RAM boot of this exact
image. Sending 3.696 s and Booting 0.704 s returned OKAY, total 4.441 s.
Runtime photograph is pending in `evidence/frontboard-mode-phone.json`; the
one-shot authorization has been consumed.

Next: read the rejected mode values from this boot, then
trace the failing field back through the OS display interface. A specific bad
refresh rate, scale, color enum or dimension must be measured before selecting
a fix. Persistent logging remains useful for full surrounding context.
