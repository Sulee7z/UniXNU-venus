# Venus 64 GiB deployment preparation

The user separately authorized and completed creation of the 64 GiB `unixnu`
partition and Android userdata/metadata reset. The EFI application reported
successful main/backup GPT readback; fastboot then reported userdata
`0x2825700000` and unixnu `0x1000000000`, matching the plan. Both erases and reboot
returned OKAY. Android now reports boot_completed=1, slot _a, Android 16, kernel
5.4.302-qgki-g7f2a2a060d1d and mounted F2FS /data. The user also confirmed normal
system entry. Root is no longer available to the ADB shell after reset; exact
partition sizes will be rechecked in fastboot immediately before root flashing.
The user then explicitly authorized the root flash and matching RAM boot.
Fastboot rechecked those exact post-reset sizes and flashed all 67 sparse
fragments successfully in 217.735 seconds. The matching b257518c RAM boot
transport succeeded, but DarwinBoot reported `NO WINDOW 20000000 BIG RUN
13600000 @ ECA00000`: the requested 512 MiB does not fit its observed 310 MiB
conventional-memory run. XNU did not start. Android was subsequently confirmed
booted again through ADB (Android 16, slot _a). The root partition stays flashed.

### Reduced-window RAM candidate

- `artifacts/venus-ufs-root/phone-288m/boot-venus-unixnu.img`, 168960000 bytes.
- SHA256 `b017a79e5f169b806bee8d653e6b4eb0aa1ca279c899c77c196b74a4832b2de6`.
- Requests 288 MiB (`0x12000000`). Kernel, root arguments, Data and trust hashes
  match the previous candidate; ADT differences are the explicit window and
  the newly generated random seed. The three core loader EFI hashes match.
- Real QEMU APFS root acceptance passed with max_mem=301989888 and 18364 free
  4 KiB pages (75218944 bytes). Both authenticated Virtio policy copies are
  already resident; SystemOS/Data mounting and userspace are later stages.
- This new RAM boot requires its own exact-image approval. No root reflash is
  needed for this memory-only candidate. See `evidence/root-memory-candidate.json`.

## Current root transfer file

- `artifacts/venus-deployment/unixnu-root.sparse.img`: 8885303488 bytes.
- SHA256: `0508c98268aa6b89efd63d3ecd7aa058da11693263a97ae1e6465df7e169261d`.
- Expands to all 9457106944 bytes of the already signed root image, SHA256
  `08bd7c4cdbe9519f75025fad65deb683d7dc2891339cd1e3e6dfb26852227bdc`.
- 6737 bounded RAW/FILL chunks cover the complete image. There are no
  DONT_CARE blocks; explicit zero fills do not rely on erased device contents.
- Independent decoding with an empty base reconstructed the exact raw hash.
- The proposed command uses `fastboot -s 55870427 -S 128M flash unixnu ...`,
  followed by RAM boot of the matching b257518c image after successful flashing.
  This exact root flash and b257518c RAM boot completed under separate approval;
  see `evidence/root-flash-execution.json` for the actual device transcript.

`scripts/flash-venus-root.py` checks exact input hashes, device/boot identity,
active slot and post-reset partition sizes. It journals the operation before
flashing and refuses automatic repetition of an existing execution. Its
default mode checks local inputs only; device operations need both the
execution flag and matching recorded authorization.

## Exact proposed disk layout

- Device: Venus/M2011K2C, serial 55870427, LUN0, 4096-byte logical blocks.
- Existing Android userdata: GPT slot 34, start 2785280.
- New Android userdata end: 44881663; capacity 172426788864 bytes.
- New unixnu: GPT slot 35, 44881664..61658879 (`0x2acd700..0x3acd6ff`).
- unixnu capacity: 68719476736 bytes (64 GiB); tail gap 1028096 bytes.
- Existing userdata identity/start and all other occupied GPT entries are
  preserved. Both GPT copies/CRCs are regenerated and independently parsed.

`artifacts/venus-deployment/partition-preview.json` and the before/preview
regions hold the exact proposal. The reference supplied in `参考.md` describes
another geometry and a destructive userdata reset, not an in-place F2FS shrink.
It cannot supply this phone's LBAs or slot number.

## Root image and Data seed

- `artifacts/venus-deployment/unixnu-root.img`: 9457106944 bytes, SHA256
  `08bd7c4cdbe9519f75025fad65deb683d7dc2891339cd1e3e6dfb26852227bdc`.
- The complete unchanged iPadOS 17.7.11/21H461 OS and SystemOS disks are wrapped
  by the SHNGROOT manifest and independent owner policies. The actual C verifier
  authenticated all 1483785 OS and 806400 SystemOS blocks after assembly.
- OS volume UUID: `04769D26-2CA0-4825-B443-E2E5F88300F2`.
- SystemOS UUID: `8846FE78-2910-4297-AF97-D59BB6F8FC16`.
- `Data.dbr`: 1015936 encoded bytes representing an 8 GiB APFS volume, SHA256
  `ca732abdafa194ceb1d1ede1b20f930374180d238da6f74ebb00a2caa4c6fb33`.
- Data UUID: `FCC1EC83-9500-4D4D-AEED-6004A520B3C0`. It was generated in a
  separate Linux guest from original `/private/var`, preserving file contents,
  owners/modes and symlinks. APFS checking and full packed reconstruction passed.
- The original two-module trust bundle hashes to
  `7416ca4f8377146626bb284e2133c76bee6cb4e3ee0af5d648b186235a7323a7`.

Private owner keys remain under `/root/unixnu-build/venus-owner-root` in the
G-backed WSL filesystem. Only the public anchor is in the device package.
Use the prepared signed image; the generic userdata builder alone does not
append these disk-policy envelopes. `[userdata] partition="unixnu"` and
`geometry_verified=true` reflect the applied GPT and successful post-reset
fastboot geometry check; the prepared signed image targets only unixnu.

## Root kernel and runtime checks

Configuration: `venus_ufs_root_defconfig`. Kernel SHA256:
`f1f657e69fcbf7bcc8da2022a697bed965c000e132703024444df8ded417cac9`.

`artifacts/venus-ufs-root/phone/boot-venus-unixnu.img`: 168960000 bytes, SHA256
`b257518c19506982a7e48563683b3cf2b50fd563e63371173e0d6bb45c7d5ea5`.
It includes the root kernel, original trust bundle, Data seed, root=1,
`sheng-data-persist=2`, and a 512 MiB owned-memory request. The normal mode
   rejects legacy raw probes and uses the verified unixnu root policy.

Host verification completed:

- Root support archives, exact original 190-slot binding aliases and input
  hashes checked. Runtime object names are used by the linker audit.
- Interrupted final-pass recovery checks the actual link inputs as well as
  retained JSON recipes. Seven regression tests cover the missing-object loop.
- The complete kernel and Apple prelink passed. Default-off QEMU and the final
  payload kernel reached IOFindBSDRoot.
- Genuine XNU RSA/SHA policy checks and refusal controls passed, status=1.
- The original APFS OS root mounted on read-only QEMU Virtio disks and reached
  the actual owner-root acceptance checkpoint: readonly=1, UUID match=1,
  wrong UUID refused=1, owner accepted=1, zero Virtio read failures.
- This checkpoint precedes SystemOS/Data mounting and userspace execution.
  It is not phone root-mount or graphical iOS qualification.

## Plan-bound EFI partition tool

### Corrected payload identity (current)

The first phone attempt returned `Not Found` after the menu
(`G:\20261027_102733.JPG`). Its FAT label was `VENUSGPT`; the board's actual
`VenusFatView` accepts only `VENUSXNU`. The corrected payload is:

- `artifacts/venus-deployment/gpt-apply-label/boot-venus-unixnu.img`
- 68296704 bytes, SHA256
  `40c84a3e056067e7f894187dae3589e1781dfaf13e8fa631412c73f035687c43`.

The actual board recognizer now accepts this volume and rejects the old image;
all 512 alignment offsets and truncation checks pass under sanitizers. The
packager also rejects incorrectly labelled payloads before writing a boot image.
A full QEMU test boots UniXNU from a separate ESP, discovers this exact payload,
loads its configuration, selects the EFI entry and observes
`VENUS_GPT_COMMITTED_AND_READBACK_OK`, with both synthetic GPT regions verified.
See `evidence/gpt-efi-menu-host-test.json`.

No erase was executed after the failed phone launch. The corrected image was
subsequently authorized, ran successfully on the phone, and was followed by the
authorized size verification and Android reset described above.

### Original attempt (retained; incorrect FAT label)

`artifacts/venus-deployment/gpt-apply/boot-venus-unixnu.img`: 68296704 bytes,
SHA256 `bc0c3b4b4aaca27f5a364ca070f9f2a26d1fd26389b86a28f86838f664117552`.

The application requires one writable whole-disk BlockIO device with the exact
LUN0 capacity and both retained GPT byte regions. It rechecks before writing,
writes/flushes/reads back the backup first, then the primary, and displays the
result without rebooting. A changed/mixed layout or ambiguous disk refuses.
An exact already-applied layout reports no writes. No automatic retry/rollback
is attempted after failure.

The compiled EFI application ran against a sparse synthetic disk in QEMU.
Both resulting GPT regions exactly matched the preview; allocated bytes outside
GPT stayed zero. Sanitizer tests also cover preview, mismatch, idempotence and
all eight read/write/flush failure boundaries. Physical GPT execution subsequently
completed successfully under the separately recorded authorization.

## Device sequence to authorize separately

1. Verify phone identity and the exact GPT tool image; RAM boot the application.
2. Read its result. Only a complete successful writeback permits the next step.
3. Return to fastboot and verify the new userdata/unixnu sizes.
4. Erase Android userdata and metadata, then reboot Android for initialization.
   This destroys the previous Android apps/files. Confirm Android boot and the
   retained 64 GiB unixnu layout before installing the iOS root image.
5. In a subsequent explicitly authorized sequence, flash only `unixnu` with the
   signed image, boot its matching kernel/Data bundle, and observe root mounting
   and process startup. Display/touch support remains separate porting work.

Evidence: `evidence/deployment-host-ready.json`, `evidence/gpt-efi-host-test.json`,
`evidence/root-payload-inputs.json`, and the files named by those records.
