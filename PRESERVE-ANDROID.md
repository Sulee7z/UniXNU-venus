# Mi 11: retaining Android and its data

## Latest official dual-system evaluation

The user supplied the official F2FS/GPT split guide again. Its prerequisites
were evaluated with bounded read-only Android queries: the base GPT/F2FS
layout matches, while recovery decryption/resize support still needs checking.
The deployment partition and capacity remain undecided. See
`DUAL-SYSTEM-SHENG.md`; the old pinned-file proposal below stays deferred.

## Scope update, 2026-10-25

The user asked to follow the complete official porting guide and temporarily
deprioritized retaining Android. The current storage development target is
the guide's userdata OS/SystemOS layout. The pinned-file proposal below is
historical and deferred. See `GUIDE-REVIEW.md` and `porting.toml` for the active
plan. No storage write or partition change was performed by this scope update.

## Current design

Firmware and first-console XNU are loaded with `fastboot boot`. No Android
boot slot, vbmeta, vendor_boot, dtbo or partition table change is required.
The first native-XNU test has no physical-storage driver enabled and no iOS
root filesystem installed. Its FAT payload is read-only and memory-backed.

For persistent iOS storage, investigate a pinned, preallocated file inside
the existing Android F2FS /data. Use its validated physical extents as the
only allowed block ranges for an iOS root image and separate iOS Data/log
files. This is not ordinary opening of an Android encrypted file from iOS.
The plaintext iOS image would have to be placed below Android's encryption
layer, exclusively in blocks already owned and held by those files.

## Verified read-only facts

Evidence: `evidence/venus/data-readonly/20261025T043712Z` and
`20261025T045014Z`.

- /data uses F2FS, 4096-byte blocks, `inlinecrypt`.
- Android reports file encryption and metadata encryption.
- Runtime F2FS features include `pin_file`.
- /data is dm-42, name userdata, backed only by sda34 (259:18).
- dmctl: `0-470990808: default-key, aes-xts-plain64`, offset 0.
- dm-42 and sda34 both contain 470990808 512-byte sectors.
- sda34 starts at 22282240 512-byte sectors on its disk.
- Available space at acquisition: 106880676 KiB (about 101.9 GiB).
- No f2fs_io/filefrag command was found in the phone's PATH.
- No test file, pin ioctl, physical write or filesystem change was performed.

These establish candidate compatibility, not a working storage solution.

## Remaining storage experiments

1. Compile an AArch64 pin/extent inspection tool locally. Before uploading
   or creating anything on the phone, describe it and obtain popup approval.
2. Use a new small file to test preallocation, pin state and FIEMAP on this
   actual kernel/filesystem. The pin state is FS_NOCOW_FL; GET_PIN_FILE counts
   failed GC moves rather than returning a Boolean pin state.
3. Confirm full extents, alignment, no unsupported FIEMAP flags, one-to-one
   device mapping and no overlap with any other device-mapper holder.
4. Check extent stability across reboot before considering raw writes.
5. A first-block test, complete write/readback hash test, and persistent-root
   installation are separate phone-write approvals, not covered by a RAM-boot
   approval. The iOS block backend must reject every write outside the pinned
   extents and recheck extents before every boot.

References read: `ShueiTsuki/data-a-live` commit
050b07cc254cfa328d86e2b1938ab8d04aa2a064, especially FUXI_NOTES.md and
tools/pinfile/pinfile.c. Its pandora runtime result does not qualify Venus.

## Current kernel stage

Source XNU is xnu-10063.141.1 with the pinned UniXNU 4K patches and source
crypto/pthread/ArmDTPlatform/ArmCpu components. No iOS userspace image has
been selected or installed. The matching iOS 17/iPadOS target and original
APFS/prelink components remain a subsequent phase after native entry.
