# Root flash: historical recipe and current correction

The first successful flash is recorded in `evidence/root-flash-execution.json`
and `G:/UniXNU-Port/logs/venus-ios-root-device-commands.log`.

1. `prepare-venus-root-flash.py` used `venus_sparse.py` to encode **RAW/FILL
   only**, including explicit zero fills. RAW payloads were bounded to8MiB.
2. An independent decoder reconstructed the whole image from an empty base
   and matched SHA-256. No existing device bytes were required.
3. `flash-venus-root.py` verified exact files/device/slot/partition sizes,
   wrote the journal, then executed:

   ```text
   fastboot -s 55870427 -S 128M flash unixnu <complete sparse image>
   ```

4. Fastboot internally split that one8.885GB transfer file into67 downloads.
   Every Sending/Writing completed OKAY; flash exited0 in217.735seconds.
   These were not67 separately prepared input files.
5. Only then did the approved matching RAM boot execute.

## What went wrong in the iOS26 attempt

- A22.339GB raw image was sent through two host attempts, both displaying
  `std::bad_alloc`. The768MiB max-download-size alone does **not** prove the
  allocator failure's cause.
- A64MiB zero-file diagnostic was actually flashed to `unixnu`. Its
  Sending/Writing completed OKAY. It overwrote the old manifest and start of
  the OS window. That diagnostic write was an error and was not the
  confirmed root image.
- The replacement sparse encoder skipped538,571zero blocks using DONT_CARE,
  leaving2,205,986,816bytes dependent on existing storage contents. This is
  unsuitable for installing the signed root on a previously used partition.
- The user interrupted that transfer. Its output was buffered through
  `Select-Object -Last`, so there is no full progress transcript. The extent
  actually written is unknown. No iOS26 RAM boot has executed.

## Local correction completed

`pack-venus-ios26-sparse.py` now reuses the first successful `venus_sparse.py`
encoder. It preserves the old attempted image and publishes a new file only
after complete coverage and independent expanded-hash checks pass.

```text
C:\unixnu-ios26-root\userdata-root.complete.sparse.img
20,133,460,076bytes
SHA256 c21357134f9e2e22b69dd49e6bb16c166e48a9e63530b23039eb858f8dace6a1
```

The complete transfer has4,915,253RAW blocks,538,571FILL blocks and **zero
DONT_CARE blocks**. Expansion from an empty base matches the original
22,338,863,104byte image:
`b0c3dd3ff44f3bb7bf639e281b05da948d7ad85da060f113051d4d03e928049c`.

Reports: `evidence/ios26-complete-sparse-preparation.json` and
`evidence/ios26-flash-history-review.json`. The three historical sparse
boundary/coverage/refusal tests pass.

## Bounded recovery transfer prepared

`prepare-ios26-flash-fragments.py` planned152separate transfers, each at most
134,215,816bytes (<128MiB). Assigned ranges have no gaps or overlaps and cover
all22,338,863,104bytes. Zero source blocks remain FILL records. Each fragment
skips only the ranges assigned to the other fragments.

The first, middle and last fragments were staged locally, independently
decoded, and compared with the corresponding ranges of the pinned raw image.
The full input SHA and every planned extent were rechecked by the recovery
executor in its default local-only mode.

Plan: `evidence/ios26-bounded-fragment-plan.json`, SHA256
`73ae452e0720b86e52bcc0a8e3be99bf2e7de5995cdd4060d8845f90b83f93e1`.

`flash-venus-ios26-recovery.py` starts in fastboot and, only with matching
separate authorization, stages/verifies one fragment at a time and flashes
only `unixnu` using `-S 128M`. It writes an execution journal before each
command, streams stdout/stderr into a persistent log immediately, and requires
both exit0 and an explicit Writing OKAY acknowledgement. An interruption stops
the host process, leaves the current fragment for inspection, and refuses an
automatic restart. It executes no reboot, Android erase or RAM boot.

The20.133GB corrected transfer and its152fragment plan have been flashed once
under explicit approval. All152fragments returned exit0 and an explicit
Writing OKAY; the journal at `evidence/ios26-root-recovery-execution.json`
records every staged fragment SHA and its raw-range SHA. No reboot, RAM boot or
Android erase occurred. The first execution attempt aborted during its
`getvar serialno` precheck because the reader thread raised a bare
`queue.Empty`; that attempt wrote nothing, and its journal/log are retained as
`ios26-root-recovery-precheck-aborted.json` and
`venus-ios26-root-recovery-precheck.log`.

The old root cannot be treated as intact, and this review does not establish
Android damage or an on-device readback. What the transfer proves is that the
host sent and the bootloader acknowledged every fragment; it does not prove the
partition bytes read back correctly or that APFS/AMFI/launchd run.

Result record: `evidence/ios26-root-recovery-result.json`.
