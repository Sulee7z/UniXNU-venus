# Venus iOS 26.5.2 native candidate

2026-10-31. Source: iPhone18,2 iOS 26.5.2 (23F84). Everything below was built
and verified on the host; nothing ran on the phone.

## 1. Restore inputs

The pinned IPSW was read with HTTP range requests; every component passed its
ZIP CRC and SHA-256. `ipsw` 3.1.739 (release asset digest pinned) decrypted the
AEA images with its pure-Go implementation; no key material is stored.

| Component | Bytes | Volume UUID |
| --- | ---: | --- |
| OS | 9,565,110,272 | `B6C635B2-67F6-4034-B5D5-539E4D03D1EC` |
| SystemOS | 5,247,074,304 | `B792C617-C87F-4706-9CD3-4C3A034C27CB` |

## 2. Kernel and prelink

`xnu-12377.121.6` at `ac9718fb` was built with the Venus storage profile:
UFS, verified/owner root, KDK IOKit ABI, APFS crypto KPIs, CSR, ML-DSA, trust
cache runtime, dyld flags, iOS class aliases, EDT fstab, NativeRamBlock and the
owner Data mount. The Data UUID is `716C953C-0A69-4049-B75D-88A3C7A6ECE8`.

- kernel `f01f8bed…`, 18,109,376 bytes; unstripped `1a417fad…`, 23,015,184 bytes
- prelink `eb63ab6c…`, 28,098,560 bytes, 17 kext metadata entries
- APFS/AMFI/zlib closure: 8 KDK executables, 0 missing or ambiguous names
- primary vtable gate: identical observed slots
- extra vtable gate: 23 paired tables identical; `AppleEffaceableStorage` and
  `CoreAnalyticsHub` have no native provider and are reported, not passed

QEMU, real UEFI + DarwinBoot: both the storage kernel and the prelinked kernel
reach `bsd_init` at EL1 with the MMU on and 4 KiB TG0/TG1.

Two fixture faults were identified and fixed on the host only: the upstream test
DT needed `--nvram-proxy` (ArmDTPlatform refuses a `/chosen` without the CHRP
bank), and the ADT needed `crypto-hash-method=sha2-384`, without which the
kernel panics with `non-sensical crypto hash method`.

## 3. Userland

- 3,383 images rewritten to ordinary arm64 (9,859,356 instruction edits)
- 2 OTE factory test apps refused: their original cdhash is in neither Apple
  trust cache, so they stay arm64e and cannot be graded
- shared cache: 84 files, 29,577,370 edits, 4 KiB CodeDirectories rebuilt;
  one PAC-shaped word (a float constant in `libsystem_m`) is left untouched
- trust bundle: 7,155 entries, all original Apple entries preserved

## 4. Root and Data

The OS container was grown from 2,335,232 to 4,129,280 blocks, 3,471 rewritten
files (7.08 GB) were written through a Linux APFS guest, and every file was
re-hashed on read-back. `apfsck` passes.

The SHNGROOT image wraps the modified OS and the unmodified SystemOS behind
minimal protective GPTs, signs both with the Venus owner key, and links the
policy envelopes outside the disk windows. A C implementation of the verifier
replayed all 5,410,816 blocks.

- root image `b0c3dd3f…`, 22,338,863,104 bytes (kept on C: — G: is nearly full)
- Data seed `b42ce865…`, 1,130,624 bytes packed

## 5. Boot image

`artifacts/venus-ios26/boot-venus-ios26.img`, 168,960,000 bytes,
SHA-256 `150d35f2…`. It carries the prelinked kernel, the ADT with 8 CPUs and
the Venus chip identity, the trust bundle, the Data seed and the previously
RAM-booted firmware volume; the container roundtrip and stock header metadata
checks pass.

## 6. What is still required

1. Approval to flash the 22.3 GB root image to `unixnu` (slot 35). It is larger
   than the currently flashed 9.46 GB image, so most of the partition is
   rewritten; Android partitions are not touched.
2. Approval for one RAM boot of the 169 MB image with USB console capture.
3. Runtime confirmation that APFS/AMFI start without `AppleEffaceableStorage`
   on this kernel, that launchd execs, and that the cache maps. None of this is
   demonstrated yet, and no UI or Metal claim is made.
