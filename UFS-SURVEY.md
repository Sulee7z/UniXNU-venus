# Linked read-only UFS survey

The next hardware step is a register-state survey before controller ownership
or DMA changes. The user authorizes ordinary file work across G: and its WSL
workspace; individual phone operations still require their own approval.

## Scope

`venus_ufs_defconfig` is isolated from the working `venus_defconfig`. It links
the checked iOS17 UFS archive with `NATIVE_UFS_READONLY_SURVEY=1`. The start
path permits only `native-ufs-probe=2` and rejects root mode or other probe
modes before mapping the controller. With no probe requested, it remains idle.

The survey reads:

- GDSC, AXI/AHB/UniPro/aggregate clock state from the measured Lahaina GCC page.
- UFSHCI capabilities/version/status and both request-list bases, doorbells
  and run state, only when power and all required clock conditions are met.
- SMMUv2 global status and stream table; a matching context is read only for
  an exact unique SID 0xe0 with valid bounded geometry. Other users of that
  context are counted before any later ownership decision.

Callbacks expose reads only. This survey performs no device-register writes,
DMA allocation, SCSI command submission or root publication. It intentionally
panics with a `VENUS UFS READ-ONLY` report so the existing renderer preserves
the results for a photograph.

## Verification completed

- The actual survey helper passed GCC ASan/UBSan tests for clock gating,
  64-bit queue addresses, shared and ambiguous streams, invalid geometry and
  mapping failure.
- The UFS object passed the original 190-slot iOS17 ABI checks and link-input
  symbol checks. The archive was copied by a hash-checking board recipe into
  the isolated kernel build; normal baseline builds skip that recipe.
- Kernel compilation and Apple prelink passed.
- Real QEMU default-off execution matched the UFS driver but did not map the
  controller, and reached IOFindBSDRoot.
- Separate QEMU requests for transfer mode and root mode reached the explicit
  unsupported-operation panic with `mapped=0` and status 0xe00002c7.
- The final payload kernel also passed the default-off root-finder regression.
  QEMU tests do not claim the physical SM8350 register values are known.
- Boot-image roundtrip and all 21 live memory reservations passed validation.

## Candidate and approved phone attempt

`G:\UniXNU-Port\artifacts\venus-ufs-survey\phone\boot-venus-unixnu.img`

SHA256: `a308047374e3faaead73333638667737c0607161ef05b8eff08e6939465ac62a`

Size: 168960000 bytes. Kernel arguments include `native-ufs-probe=2` and
`native-ufs-root=0`. No timed reset is enabled.

The user approved this exact image's RAM boot and read-only register survey.
The verified ADB5037 connection entered fastboot; Sending returned OKAY
(3.596 s), Booting OKAY (0.193 s), total 3.831 s. Transcript:
`G:\UniXNU-Port\logs\venus-ufs-survey-phone.txt`. The result is recorded below.

## Phone result

`G:\20261026_015422.JPG` shows the expected diagnostic report with `err=0`.
The transcription is `evidence/ufs-survey-phone.json`.

- Power/clock conditions passed: GDSC=f822f000, AXI/UniPro=221,
  AHB/aggregate=1.
- Controller read succeeded: CAP=1587031f, UFSHCI version=300, HCS=10f,
  HCE=1. It reports 32 transfer slots and an enabled, ready controller.
- Transfer list=d4993000, run=1, doorbell=0. Task list=d4994000, run=0,
  doorbell=0. Both queues had no outstanding request at this instant.
- SMMU IDR0=4c017e59, IDR1=6000004b, global fault status=0. SID e0
  matches slot 2 exactly once, S2CR=2, context bank 2 has one observed user.
- CBAR=1f000, CBA2R=1, SCTLR=a9f00e0, TTBR0=0. Retain these raw values;
  do not infer a free/reprogrammable context from SCTLR.M being clear.

This is successful physical register access, not a completed SCSI/DMA read.
Next: reread queue/stream ownership, validate DMA address limits and an
available context, then authorize the controlled queue/DMA configuration and
bounded capacity/GPT reads. Existing firmware queue addresses are observations,
not constants to transplant into the next build.

Evidence: `evidence/ufs-survey-controls.json` and
`evidence/ufs-survey-candidate.json`.

## Rebuild

First select the baseline to compile the archive against its existing audited
storage ABI. Then select the isolated kernel configuration:

```
python3 /mnt/g/UniXNU-Port/sources/UniXNU-guide/unixnu defconfig venus_defconfig
python3 /mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/build-venus-ufs-probe.py --partition unixnu --readonly-survey
VENUS_DEFCONFIG=venus_ufs_defconfig VENUS_GUIDE_REPORT=/mnt/g/UniXNU-Port/artifacts/venus-ufs-survey bash /mnt/g/UniXNU-Port/tools/build-venus-guide.sh
VENUS_DEFCONFIG=venus_ufs_defconfig VENUS_GUIDE_CANDIDATE=/mnt/g/UniXNU-Port/artifacts/venus-ufs-survey/phone bash /mnt/g/UniXNU-Port/tools/make-venus-guide-candidate.sh --kernel-arg native-ufs-probe=2 --kernel-arg native-ufs-root=0
```

This survey's build tree is
`/root/unixnu-build/venus-guide-out/venus/ipados-17.7.11-21H461/venus_ufs`.
The subsequent block-read candidate is documented in `UFS-BLOCK-READ.md` and
uses the separate `venus_ufs_read_defconfig` selection.
The baseline tree and earlier phone images remain retained separately.

## Build interruption recovery

The final revision also rejects 64 KiB SMMU register geometry before reading
context-bank registers. Its base kernel SHA256 is
`643e9fa3613dd31c6bd831fb1f12ef68fb846194a645513599477803511e7f4e` and its
instrumented payload SHA256 is
`33722dd476b8d0d9c7093852c540de693a4e48b581261a107d47c638ef117b0b`.

An interrupted packaging run exposed mcopy's host-file overwrite prompt.
Extraction now uses binary mtype output, publishes completed temporary files
and checks kernel/ADT hashes against payload.json. It needs no interactive
file overwrite response.

Later checks found zero-filled config files in reference submodule metadata
and empty WSL kernel outputs. The cause has not been established. Original
submodule metadata/worktrees were retained under
`diagnostics/git-recovery-20261025T173705Z` and
`diagnostics/git-recovery-20261025T174032Z`. The affected checkouts were
recreated at the existing pinned commits; tracked file comparisons found no
content changes after CRLF normalization. Main-project local edits were kept.
The empty generated kernel and report were restored from the G: exports whose
SHA256 and prelink identity matched. Build/export scripts now sync before
successful completion. The final candidate and QEMU controls were revalidated.
