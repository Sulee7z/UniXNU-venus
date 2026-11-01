# Prelinked runtime and logger candidate

The 21H461 prelinked kernel was tested through newly built UniXNU and
DarwinBoot EFI binaries using the current upstream observer. Host adaptations
only select local AAVMF and preserve QEMU 8's actual SCTLR register alias.
The kernel was not modified during the base observations.

## QEMU observations

- With the OS-required `crypto-hash-method=sha2-384` and
  `amfi-only-platform-code=1` properties, XNU reached `bsd_init`.
- ArmDTPlatform configured, published its NVRAM proxy and registered one CPU.
- Original Apple corecrypto initialized its real function table and PRNG.
- GIC readiness, one running CPU and the first timer IRQ were observed at
  the actual return from `rtclock_intr`, with the return stack matched.
- The original APFS kmod start ran and its load call returned zero. The
  observer still reported no APFS VFS registration. This is a component-load
  result, not a root-mount or userspace result.
- The extracted panic-screen/entry-probe kernel from the final FAT payload
  also reached the actual timer-interrupt return in QEMU.

Initial QEMU fixture runs omitted OS properties: first crypto-hash-method,
then the platform-code property. Each produced the corresponding original
Apple panic before BSD init. Adding the profile's required inputs fixed the
fixture. The actual generated Venus ADT contains both properties and `main`.

Evidence is consolidated in `evidence/prelinked-runtime.json`. Full reports
are in `artifacts/venus-guide-linux/qemu-bsd-amfi`, `qemu-timer`, `qemu-apfs`,
and `artifacts/venus-guide-prelinked/qemu-timer` under the workspace root.
All successful runs stopped at real checkpoints without a deadline interrupt.
QEMU uses QEMU MMIO/CPU resources and does not validate physical Venus UFS.

## Firmware and RAM input

The new `VENUS_GUIDE_LOGGING` build option wires the real Mu Advanced Logger
into DxeCore and DXE/application debug libraries. DxeCore allocates 128 pages
(512 KiB) and publishes the logging protocol. Its hardware port forwards to
the existing framebuffer serial library. SEC retains its early screen path;
the memory log begins in DXE. AdvancedLogDxe and QrEncoderLib are compiled into
the firmware. The locator-variable feature is disabled, and no file logger
is included by this change.

The shared UniXNURamDiskDxe assumes the entire ABL initrd is sector-sized and
is the FAT block device. On this Android-v3 Venus boot chain, vendor ramdisks
precede the FAT and do not guarantee sector alignment. The known-working
bounded VenusPayloadDxe adapter is retained for that input contract. Merely
replacing it with the shared driver would lose the payload.

Payload construction uses the official format-2 command. Firmware uses the
existing external Mu build wrapper, now accepting `VENUS_UNIXNU_SOURCE` so it
builds the current package and DarwinBoot. This wrapper retains the required
Mu patch whitespace handling and produces the full compiled-library report.

## Candidate

`G:\UniXNU-Port\artifacts\venus-guide-prelinked\boot-venus-unixnu.img`

SHA256: `5d52b2967a1e35a7f392511be6b574a1ab578b84901aa00596e00c91659d3d51`

Size: 168960000 bytes; RAM FAT: 160 MiB. It fits the 192 MiB boot partition,
but the proposed test is RAM boot. Boot header v3 metadata and matching
vendor_boot/dtbo dependencies were verified. All 21 live reservations remain
covered and the 16 allocation ranges have no conflict.

The payload enables a five-second menu, Tools, entry bands and a panic screen.
It contains no timed-reset probe, root filesystem, Data seed or userland.
The user approved this candidate's RAM boot. Fastboot returned Sending OKAY
(3.618 s) and Booting OKAY (0.193 s), total 3.855 s. The transcript is
`logs/venus-guide-prelinked-phone.txt` under the workspace. Screen/kernel
and QR-export results are pending the user's observation.

The user subsequently supplied a real kernel panic at CNTP_CTL_EL0 in
fiq_context_init. Its source-level correction and successor candidate are
recorded in `VIRTUAL-TIMER-FIX.md`. QR export itself is still unobserved.

Build/check commands:

```
bash /mnt/g/UniXNU-Port/tools/build-venus-guide-efi.sh
bash /mnt/g/UniXNU-Port/tools/make-venus-guide-candidate.sh
python3 /mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/check-prelinked-evidence.py
```

The payload's freestanding ELF probes use `/usr/bin/clang`, avoiding the
Darwin-only flags of the XNU compiler wrapper. Actual kernel compilation
continues to use the dedicated XNU toolchain.
