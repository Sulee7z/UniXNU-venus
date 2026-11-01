# Zeta reference and reuse decisions

User reference: https://unixnu.com/zh/devices/zeta.
The page pins `none24smu/UniXNU-zeta` at
`825d75028a3aefc2035164591ba9074837e39979`; that exact revision is checked out
in `sources/UniXNU-zeta-reference`. The SM8350 storage implementation was
read at `none24smu/UniXNU` revision
`68c513467bb6c44106c053c410582c1d14f96dd7` in `sources/UniXNU-zeta-core`.

## What its record establishes

The maintainer reports Surface Duo 2 native USB logging, native UFS reads,
APFS root mounting and PID 1 executing rewritten arm64 launchd/dyld and
shared-cache code. It still documents pager work and no completed GUI. Its
earlier interpretation of a masked terminal wait as a running launchd was
explicitly corrected. These are zeta's reported results, not Venus tests.

Zeta uses XNU 12377/iOS 26.5.2 and offline arm64e lowering. Venus currently
uses XNU 10063/iPadOS 17.7.11 and ordinary arm64 Apple components. The same
SoC makes its hardware path useful, but its OS ABI and image rewriting are
not direct replacements for the current selected profile.

## Hardware comparison performed

`scripts/audit-zeta-ufs-reuse.py` compared the retained Venus live FDT and
hash-verified vendor archive against the zeta SM8350 transport definitions.
The following match:

| Input | Value |
| --- | --- |
| Primary UFSHCI registers | 0x01d84000 + 0x3000 |
| Lahaina QMP v4 PHY | 0x01d87000 + 0xe10 |
| Interrupt | GIC SPI 265, INTID 297 |
| UFS SMMU stream | 0xe0, mask zero |
| GCC AXI / AHB | 0x77010 / 0x77018 offsets |
| GCC UniPro / aggregate | 0x7705c / 0x770cc offsets |

The clock values were extracted from the exact Venus vendor `gcc-lahaina.c`,
not inferred from zeta. The record is `evidence/zeta-ufs-reuse.json`.
It does not establish live clock state, firmware queue ownership or DMA.

The reusable patch is `patches/drivers/NativeUfs-sm8350.patch` in the pinned
zeta core. It selects Lahaina offsets, stops both UFS queues, and retargets
only an exact unique stream to an unused context bank without changing a
possibly shared old bank. Its root-policy extension stores policy offset
and size in SHNGROOT entry bytes 88..103. The matching layout/reader/signature
logic must be used together. Zeta's LUN/GPT values and volume UUIDs are not
Venus inputs.

## PMGR implementation completed for the current ABI

Zeta's newer AMFI/KDK path is different. For the immediate `AMFI: No PMGR?`
dependency, Venus now reuses the already audited 21H461 original-PMGR
implementation from UniXNU-sheng
`0e1f6e52638137db15905db8d775ad73757f39fa`.

- `package/ShengPlatformPower.cpp` retains the original runtime identifiers,
  original ApplePMGRNub and original read/write methods. The local resource
  description is named `venus-platform-power` and advertises no hardware map.
- `scripts/build-venus-platform-power.py` adapts paths to `kits/venus` and
  explicit bootstrap/kernelcache inputs while retaining all original ABI gates.
- LLVM 18 cannot globalize Mach-O symbols with llvm-objcopy. The small
  `macho-late-init.py` helper removes the initializer section with LLVM, marks
  the uniquely identified defined initializer external, and proves the text
  unchanged. The original 340-slot vtable checks and final link still run.
- The archive is selected in the complete build list, XNU_SHENG_PMGR is
  enabled and `sheng-pmgr=2` selects real nub publication.

Four real QEMU cases passed: unpublished allocation/release, publication and
service lookup, an unsupported power-operation panic, and the original AMFI
read/OR/write call after lookup. The provider and nub have the measured ABI
sizes and correct retained/released instance counts. Both the prelinked
kernel and the final payload copy subsequently reached `IOFindBSDRoot`.
No root disk was attached and no root mount is claimed.

Evidence: `evidence/pmgr-integration.json` and
`artifacts/venus-guide-pmgr/qemu-*` under the workspace root.

## Candidate

`G:\UniXNU-Port\artifacts\venus-guide-pmgr\phone\boot-venus-unixnu.img`

SHA256 `418b74a6696b5b817838abc79dc904d65ce51b9a816aaa0cb3aecf689e12434b`.
Size 168960000 bytes. Preserves the timer and ADT fixes, panic renderer and
logger menu. It has no root/Data filesystem and no timed reset. Phone testing
was explicitly approved. Fastboot returned Sending OKAY (3.612 s) and
Booting OKAY (0.193 s), total 3.845 s. Transcript:
`logs/venus-guide-pmgr-phone.txt` under the workspace. The actual phone
kernel result remains pending the user's screen observation.

The user subsequently provided `G:\96a296c654debdabf614c1b9ac1d923e.jpg`:
after about one minute it shows `Failed to mount root device` at
`IOKitBSDInit.cpp:984`. The exact source panics there when the IOMedia
matching wait has no result. The previous AMFI No PMGR failure is passed on
the phone; root-device discovery has run. This is not APFS mount completion.

## Transport-source preparation

The exact UFS base used by the zeta patch is `UniXNU/NativeUfs`
`af785c1777161a62931425c2faaa536ce0bebd5b`. It was checked out at that pin,
exported through git archive into an isolated Linux directory and patched
with the complete SM8350 changes. Forward and reverse patch checks passed.
The patched SmmuTakeover and RootLayout tests passed with GCC ASan/UBSan,
including shared-bank stream retargeting, failed-write handling, GPT/manifest
bounds and policy-envelope placement. No MMIO or device operation occurs in
these tests. Evidence: `evidence/zeta-ufs-primitives.json`.

The next storage task is to adapt the reviewed SM8350 transport to the
current IOStorage ABI and verify bounded known-block reads. Keep the original
Apple IOStorageFamily already selected by this profile, rather than importing
the zeta iOS26 native IOStorageFamily build wholesale. Then prepare matching
root/SystemOS/Data inputs and observe root mounting and launchd in order.

## Full UFS path comparison after Venus bank reports (2026-10-26)

The user requested revisiting the successful cases and consolidating fixes.
The zeta README lines 445-497 report the same GCC/HCI/SID geometry and actual
native reads at core `68c513467bb6c44106c053c410582c1d14f96dd7`. That exact core
and its NativeUfs `af785c1777161a62931425c2faaa536ce0bebd5b` remain our inputs.
Sheng supplies the matching iOS17 ABI integration; its SM8550 wiring is not
used as Venus hardware data.

| Part | Comparison and action |
| --- | --- |
| Resources | Measured Venus GCC offsets, HCI/PHY/SID agree with the SM8350 patch and zeta observations. |
| SMMU initialization | Reference `planUfsSmmuBank` requires M clear/no conflicting users; `configureUfsSmmu` then writes SCTLR=0 and verifies it. Venus's added pre-zero requirement incorrectly rejected unused reset-state banks. Removed that precondition only for unreferenced CBAR=CBA2R=0 states; write-after-readback checks remain. |
| Ownership | Preserve old CB2; stop both UFS queues before changing only the exact SID e0. Recheck complete stream table and selected context before writes. |
| DMA | Same private contiguous allocation and complete HCI/IDR2 extent checks. Actual Venus allocation and IDR2=5111 are now observed. |
| Queue and commands | Same production stop/start, descriptor layout, DC/DSB, NOP, query, ACTIVE wake, TUR and READ(10) code. Venus adds a probe-only exact-command/range gate and media-write rejection. |
| Completion | Same OCS/UPIU type/tag/LUN/residual/sense checks, bounded polling and quarantine. Local real-command fault fixtures pass. |
| Scheduling | Zeta's five-second settle was an observer fix: its terminal checkpoint disabled interrupts before an asynchronous driver finished. The Venus phone payload has no such root-finder terminal checkpoint; its probe runs synchronously and panics only after completion/refusal. No arbitrary five-second hardware delay is copied. |
| Measurement | Venus reads capacity first, bounds primary/backup GPT reads, verifies both CRCs/arrays and reports the header SHA for comparison with the retained Android blocks. |
| OS ABI | Keep the measured iOS17 190-slot binding instead of replacing it with zeta's iOS26 native IOStorage build. |

The reported zeta ARM64 UFS-model tests used a qualified QEMU10 model. Our
installed QEMU8.2 is used for kernel entry/default-off/refusal controls, not
claimed as a passing UFS hardware model. Local transport fault tests and actual
phone-GPT parser tests remain separately identified from device acceptance.

All eight photographed nonzero, M-clear SCTLR reset values are now regression
inputs. Ignored initialization writes, an enabled M bit, new stream users,
changed routes and bad widths still refuse. See `UFS-BLOCK-READ.md` for the
single current consolidated candidate and its exact evidence.

The consolidated `20537e4e...` image subsequently succeeded on Venus: the user
photo `G:\20261026_153025.JPG` reports nine commands and five GPT reads through
bank 74. Capacity, both header CRCs, the array CRC and primary-header SHA256
match the independently retained Android raw blocks. The earlier full-SCTLR-zero
precondition was the observed blocker; restoring the reference initialization
order passed. See `evidence/ufs-read-device-verified.json`. Root mounting and
userland are still subsequent stages.
