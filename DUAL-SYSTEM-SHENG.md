# Official dual-system and sheng storage reference

Reviewed user references:

- https://unixnu.com/zh/porting/dual-system-partition
- https://unixnu.com/zh/devices/sheng, with record
  `516a780473a2ac59c8b438e132bb60204dda9e22`.

Sheng provides the same iPadOS 17.7.11/21H461 OS ABI used by Venus, including
original storage classes, prelink, PMGR, root/Data layout and presentation
integration. Its SM8550 registers and board policy remain different from
SM8350. The selected transport reference is still zeta's reviewed SM8350
patch. This combines checked interfaces with the target's measured hardware.

## Read-only partition findings

Snapshot: `G:\UniXNU-Port\evidence\venus\dual-readonly-20261025T161421Z`.
The phone was running Android. Bounded binary reads used ADB exec-out through
root, without transferring a helper or writing any device file.

- Logical disk sector: 4096 bytes.
- `userdata`: GPT index 34, LBA 2785280 through 61659130.
- Primary/backup GPT headers and entry tables agree and pass their CRCs.
- userdata is the last occupied partition, a free GPT entry exists and no
  `unixnu` partition is present.
- Both decrypted F2FS superblocks agree: 4 KiB blocks, 512 blocks per segment,
  one segment per section, no multi-device/zoned layout, checkpoints enabled.
- The single dm backing device and raw-device holder match, and mapped/raw
  byte sizes agree. The mapping offset must still be rechecked in recovery.
- Compatible TWRP was not active. Its decryption support and actual
  F2FS_IOC_RESIZE_FS implementation remain unverified.

These are Android-side prerequisites. A formal plan requires rechecking in
the compatible recovery session, choosing capacity and measuring available
space. No GPT plan/apply, resize, partition creation or formatting was run.
The official twelve host tests, F2FS section-rounding self-test and shell
syntax check passed (`logs/venus-official-dual-tests.log`).

The official splitter creates a partition; it does not install iOS. Before
using a new `unixnu` partition, the image builder and UFS parser must select
that same partition and actual geometry. The final deployment target has not
been selected. The old pinned-F2FS-file proposal stays deferred.

## Storage ABI and transport preparation completed

1. The shared storage audit now accepts an explicit candidate and snapshot,
   and can emit a plan of the actual metadata addresses to read in QEMU.
2. Class member offsets come from the current OSMetaClass compiled DWARF.
   The real prelinked IOBlockStorageDevice metadata was observed after APFS
   component loading, with the same kernel hash and a reached checkpoint.
3. All 190 public iOS dispatch slots were qualified, including 176 native
   bindings and actual class sizes 0x90/0x88. The annotation object was never
   linked or executed.
4. Zeta's exact NativeUfs base and complete SM8350 patch compile against this
   iOS17 build's real headers/recipe. The newer vm_kern_xnu.h include is removed
   only when this XNU version supplies its existing API in vm_kern.h.
5. The concrete NativeUfsBlock is bound through the shared storage binder:
   190 slots, 23 overrides and 11 original imports checked. The full import
   check also reads native link-object definitions: nprocs and the real UBSan
   runtime are private in the final image but present in the native link.
6. `NATIVE_UFS_ROOT_PARTITION` provides explicit `unixnu`/`userdata` selection.
   Both build variants passed sanitized GPT tests for exact matching,
   rejecting the other target and prefix matches without fallback.

Archives:

- `G:\UniXNU-Port\artifacts\venus-ufs-probe-unixnu\libShengUfs.a`
- `G:\UniXNU-Port\artifacts\venus-ufs-probe-userdata\libShengUfs.a`

These are unlinked diagnostic archives compiled without the root-verification
layer. They are not normal root-boot artifacts and have not performed physical
UFS I/O. Current deployed kernel configuration still has native UFS disabled.
Before normal root use, integrate the storage policy, select the exact target
partition and validate real read/DMA behavior.

Commands from the existing WSL environment:

```
python3 /mnt/g/UniXNU-Port/tools/audit-venus-storage.py --prepare-observation
# Capture the resulting metadata plan at its actual QEMU checkpoint.
python3 /mnt/g/UniXNU-Port/tools/audit-venus-storage.py --snapshot /mnt/g/UniXNU-Port/artifacts/venus-storage-abi/qemu/gdb-stop.json
python3 /mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/build-venus-ufs-probe.py --partition unixnu
python3 /mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/build-venus-ufs-probe.py --partition userdata
python3 /mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/check-storage-preparation.py
```

Evidence: `evidence/dual-readonly.json`, `evidence/storage-preparation.json`,
`artifacts/venus-storage-abi`, and `logs/venus-ufs-probe-partitions-final.log`.

## Next step

Integrate a bounded SM8350 UFS probe into a separate kernel configuration,
verify live clock/link/queue/SMMU ownership and known-block reads, then connect
the selected root policy and OS/SystemOS/Data images. Formal dual-system
partitioning proceeds only once recovery conditions and the user's target
capacity are decided.
