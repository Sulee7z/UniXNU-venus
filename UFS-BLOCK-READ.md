# First bounded UFS capacity/GPT read

## Current initialization-order correction

The successful zeta path was rechecked at the user's request; see the comparison
in `ZETA-REUSE.md`. The extra Venus **pre-initialization full-SCTLR-zero** check
was wrong for the observed unused banks. Photo `G:\20261026_025852.JPG` shows
CBAR=CBA2R=0 and SCTLR.M=0 for all eight candidates, with nonzero other SCTLR
bits. The reference initializes such an unreferenced, disabled bank first,
then requires SCTLR to read back as zero before exposing the stream.

The correction permits those observed unused reset states, preserves the M-bit
and complete stream-ownership checks, and retains strict zero/format/route
readback after writes. Non-M reset bits are not used as an ownership token.
Tests replay all eight photographed values and also verify ignored disable
writes stop before CBA2R/stream programming. General failure reports now include
the planned bank, alongside DMA address, commands, protocol and SMMU faults.

Current candidate, separately approved and RAM booted:

- `G:\UniXNU-Port\artifacts\venus-ufs-read-init\phone\boot-venus-unixnu.img`
- SHA256: `20537e4e62e0d0acbbd24fc2ab1b57be7e576def7db06cfa9785ff97ecbec56c`
- Size: 168960000 bytes; arguments remain probe=3/root=0.
- Base kernel: `54cd573e064b70e5848f283b7bc91666be31bad22e3581f786f070f553246562`.
- Payload: `71a4d71472d29a7a52c386c6300b941368562d60fa850b338f3e2d5c8c5dd348`.

The user approved the exact image and controlled initialization/read operations.
ADB5037 verified the device and entered fastboot. Sending OKAY 3.597 s, Booting
OKAY 0.194 s, total 3.832 s. Transcript:
`G:\UniXNU-Port\logs\venus-ufs-read-init-phone.txt`. The successful result is
recorded below.

ABI/import/sanitizer tests, exact real-GPT fixture, linked non-WZR store audit,
base/payload QEMU and container/reservation validation all passed. Evidence:
`evidence/ufs-read-init-{candidate,controls,reference}.json`. The previous two
tested images and their complete linked inputs remain in their own directories.
Use report/candidate directory `venus-ufs-read-init` and checker `--suffix=-init`
for the current source revision.

## Phone outcome: native DMA and known-block reads verified

`G:\20261026_153025.JPG` shows `VENUS UFS BLOCK READ OK`. A cropped, reduced
copy is in `diagnostics/ufs-init-153025-report.jpg`; the original is retained.
`scripts/check-ufs-read-phone.py` compared the transcription with the preexisting
Android raw-GPT evidence and passed.

| Observation | Result |
| --- | --- |
| LUN / logical block | 0 / 4096 bytes |
| Last LBA / capacity | 0x3acd7ff / 252555821056 bytes |
| Commands / GPT reads | 9 / 5 |
| GPT entries / used | 64 / 34 |
| UFS route | SID e0, slot 2, S2CR=4a (bank 74), CBAR=10000, CBA2R=1 |
| Private DMA / new UTRL | f0ec4000 / f0ec4000, extent 22000 |
| Primary / backup header CRC | 6df6048e / 27013bb1, both match retained Android GPT |
| Entry-array CRC | 6ef292f4, matches retained Android GPT |
| Final run/stop / doorbells / global fault | 0/0 / 0/0 / 0 |

Primary-header SHA256, matching the independently retained Android sector:
`6ee87636b38cac3d5f6ad22a36d078f19f3e4c8b173f8d7d0470160d5d8cd3d3`.

Evidence: `evidence/ufs-read-init-phone.json` and
`evidence/ufs-read-device-verified.json`. The latter binds the source photo hash,
exact tested image, transcription and reference values. This establishes the
bounded native UFS read path; root media publication, APFS root mounting and
Data persistence are the following milestones. No storage-media write was made
by this probe.

## First tested candidate

`G:\UniXNU-Port\artifacts\venus-ufs-read\phone\boot-venus-unixnu.img`

- SHA256: `5f2a8d477c5b6b93d895f8bbead828276d5fde4864214fe77a0d806ad496a448`
- Size: 168960000 bytes.
- Base kernel: `8db12375ce633c6beaf219d066293784df7dd7d618e5adba636b0deff09221c4`.
- Payload kernel: `724c710760b6b25f71e2fd972a6d4b998ba5d0f5e49528cb5ccdde7cf91ec782`.
- Arguments: `native-ufs-probe=3 native-ufs-root=0`, with the working PMGR arguments.
- Current configuration: `venus_ufs_read_defconfig`; work tree
  `/root/unixnu-build/venus-guide-out/venus/ipados-17.7.11-21H461/venus_ufs_read`.

The completed register survey is recorded in `UFS-SURVEY.md`. The user separately
approved this exact block-read image, reboot/RAM boot, temporary queue/SMMU/DMA
configuration and optional ACTIVE wake. ADB5037 verified the device and entered
fastboot; Sending OKAY 3.599 s, Booting OKAY 0.192 s, total 3.830 s. Transcript:
`G:\UniXNU-Port\logs\venus-ufs-read-phone.txt`.

The photo `G:\20261026_023753.JPG` shows `selected bank has unqualified context
state`, after private DMA allocation but before queue stop/configuration.
Command count is zero. IDR2=5111 supplies the previously missing 36-bit width
information. The old formatter did not populate candidate bank/context fields;
their zero values are not hardware measurements. Transcription:
`evidence/ufs-read-phone.json`. Exact first-attempt archive and source are retained
under `artifacts/venus-ufs-read/linked-inputs`.

## Bounded bank-selection revision

The first strict checker stopped when the original planner's first M-clear
candidate had an unqualified CBAR/CBA2R/SCTLR state. The revised checker applies
the same strict conditions to each of at most eight top banks. It skips an
unqualified candidate, never clears its state to make it pass, and still rescans
ownership before configuration. If none qualify, `VENUS UFS BANK PREFLIGHT`
prints candidate indices, read-valid flags and raw context values with zero
commands, then stops before queue/SMMU writes.

New candidate, separately approved and RAM booted:

- `G:\UniXNU-Port\artifacts\venus-ufs-read-banks\phone\boot-venus-unixnu.img`
- SHA256: `9ed1aee87839acf2b8d6f09abd53d4ab222ef32ee1159b67e06d403a51b373ad`
- Size: 168960000 bytes.
- Base kernel: `139c6271e432a77cc2807fb3cee874cf05d79ca55bfb04213d6cfd4e64835b95`.
- Payload kernel: `a22afcd8ec5d549495473835680e8147b475a1a7cf0d55b13a0cb349a2215d4e`.

The user approved this exact revision and the stated controlled operations.
ADB5037 identity check and reboot completed; Sending OKAY 3.580 s, Booting OKAY
0.193 s, total 3.814 s. Log: `G:\UniXNU-Port\logs\venus-ufs-read-banks-phone.txt`.
The new photo showed all eight candidates rejected before configuration with
zero commands. Their raw states are recorded in `evidence/ufs-read-banks-phone.json`;
this led to the initialization-order correction described above.

Sanitizer tests now cover each disqualified register state falling back without
modifying the skipped bank, exhaustion of all eight candidates, and selection
changes after planning. Archive/ABI, base/payload QEMU, exact-container checks,
retained real GPT and the linked non-WZR store audit passed again. Evidence:
`evidence/ufs-read-banks-candidate.json`, `ufs-read-banks-controls.json` and
`ufs-read-banks-reference.json`.

For this revision use the `venus-ufs-read-banks` report/candidate directories
with the same configuration and boot arguments. The check scripts accept
`--suffix=-banks` to retain separate observations.

Expected retained GPT: last LBA 61659135, 4096-byte blocks, 252555821056 bytes,
64 entries/34 used, primary header CRC 6df6048e, backup CRC 27013bb1, array CRC
6ef292f4, primary-header SHA256
`6ee87636b38cac3d5f6ad22a36d078f19f3e4c8b173f8d7d0470160d5d8cd3d3`.

## Operations and bounds

1. Read current power/clock/HCI/SMMU state. Reject failed geometry, inactive
   clocks, outstanding queues, controller errors or a missing exact UFS route.
2. Allocate a private physically contiguous 0x22000-byte kernel DMA buffer.
   Check its full address extent against HCI and all IDR2 address widths before
   changing firmware queues. No firmware buffer is borrowed or overwritten.
3. Stop both request queues with bounded polling. Select a context using the
   pinned SM8350 planner, requiring M clear, no other stream users and qualified
   CBAR/CBA2R. Initialize unused reset-state banks and verify zero SCTLR afterward.
   Rescan ownership/context immediately before writes.
   Retarget only the existing exact SID e0; preserve its old context bank.
4. Program temporary SMMU/queue registers and submit NOP, a read power query,
   optional START STOP UNIT with ACTIVE power condition, and bounded TUR.
5. Read LUN 0 capacity. Require the measured 4096-byte block size and a capacity
   representable by this READ(10) probe; reject the READ CAPACITY(16) sentinel.
6. Read and validate primary/backup GPT headers and arrays. The parser bounds
   every read by capacity, limits arrays to 128 entries, verifies header/array
   CRCs, partition bounds/overlap, disk GUID and matching primary/backup arrays.
   Each READ(10) is separately scoped to the exact validated LBA/count; at most
   four blocks per command and seven GPT read commands.
7. Stop queues after success, retain all DMA memory/maps, and intentionally
   panic with `VENUS UFS BLOCK READ OK`, capacity, CRCs and primary-header SHA256.

The compiled command gate permits only exact TUR, capacity, ACTIVE wake and
scoped READ(10) forms. Data-out, WRITE, FORMAT, UNMAP and SYNCHRONIZE CACHE are
refused. It publishes no root or data window. Protocol, fatal or timeout
failures quarantine the DMA allocation without cancellation, retry or reuse.

MMIO configuration and device wake are real state changes and require a new
phone authorization; the previous register-only authorization does not cover
this candidate. No storage-media write is performed by this probe.

## Verification

- Original 190-slot iOS17 ABI and kernel import checks passed.
- Five sanitizer suites cover the reference SMMU/command paths, stricter
  ownership/width checks, actual gated commands/quarantine, and bounded GPT
  parsing. The register-survey and explicit-partition tests also passed.
- A separate ASan/UBSan runner passed the actual retained phone GPT snapshot,
  with 34 used partitions. Expected CRCs/header SHA are in
  `evidence/ufs-read-reference.json` for the subsequent hardware comparison.
- Real QEMU default-off execution reaches IOFindBSDRoot. Root/legacy-transfer
  modes reject before HCI mapping. The accepted probe=3 entry rejects QEMU's
  unimplemented MMIO at preflight before DMA/queue configuration.
  QEMU can return all ones for absent registers; it is not a physical UFS model.
- The refusal checker decodes Darwin ARM64 variadic arguments from the captured
  stack, not AAPCS64 argument registers. Retained observations remain bound to
  the exact kernel hash.
- The final payload also passes default-off QEMU. Container roundtrip and all
  21 live reservations pass. Evidence is `evidence/ufs-read-candidate.json` and
  `evidence/ufs-read-controls.json`.
- The linked `venusSmmuWrite` disassembles to `dsb sy; str w1,[x0]; dsb sy; ret`.
  It deliberately avoids STR WZR, as documented for Qualcomm SMMU traps in
  [Linux v5.4 arm-smmu.c](https://github.com/torvalds/linux/blob/v5.4/drivers/iommu/arm-smmu.c).

## Rebuild

Use the existing baseline ABI audit to build the archive, then the independent
block-read configuration. The copy recipe checks its mode, tests and input hashes.

```
python3 /mnt/g/UniXNU-Port/sources/UniXNU-guide/unixnu defconfig venus_defconfig
python3 /mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/build-venus-ufs-probe.py --partition unixnu --block-read-probe
VENUS_DEFCONFIG=venus_ufs_read_defconfig VENUS_GUIDE_REPORT=/mnt/g/UniXNU-Port/artifacts/venus-ufs-read bash /mnt/g/UniXNU-Port/tools/build-venus-guide.sh
VENUS_DEFCONFIG=venus_ufs_read_defconfig VENUS_GUIDE_CANDIDATE=/mnt/g/UniXNU-Port/artifacts/venus-ufs-read/phone bash /mnt/g/UniXNU-Port/tools/make-venus-guide-candidate.sh --kernel-arg native-ufs-probe=3 --kernel-arg native-ufs-root=0
```

The `unixnu` partition compile definition remains explicit for unused root
code; this probe selects no deployment partition and reads no partition body.
