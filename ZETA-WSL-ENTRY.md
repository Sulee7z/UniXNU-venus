# zeta XNU12377: WSL build and QEMU entry

2026-10-30: the WSL-built kernel passed real UEFI / UniXNU / DarwinBoot
handoff and returned from `arm_vm_init()`. Evidence:
[`evidence/zeta-wsl-entry.json`](evidence/zeta-wsl-entry.json).

## Exact inputs

WSL distro: `UniXNU-Build`. Tree:
`/root/unixnu-build/zeta-venus-wsl/zeta/tree`.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `mach.development.bcm2837` | 17,097,288 | `db145017aba2d7843a24a3fe0777824be85e6b9c282e9c869cc807509a6a58a2` |
| `mach.development.bcm2837.unstripped` | 21,818,392 | `f51ca7b60940f46672c631ab56f88fa8f476e74a0ffd0f08647dcc10fbd4470a` |
| `UniXNU.efi` | 95,232 | `7efb53869101f2231a4ad8d287d7fc3d4a2c0acffb7b9741998ccc4080301e09` |
| `DarwinBoot.efi` | 25,088 | `6b76a0ce411390c4970e6332e7c72dc16837b14d8e2809217ce86ca5bb1ac54b` |

Kernel files are in `build/xnu-12377.121.6/ios-obj/DEVELOPMENT_ARM64_BCM2837/`.
The source revision is `ac9718fb1af618d5ce8678d0dc6e8a58f252216f` plus
the local patches. The kernel is ARM64, subtype0, MH_EXECUTE, deployment
iOS26.0; stripped and unstripped executable-section addresses and hashes match.

The EFI pair was built with Clang/LLD18.1.3, DEBUG/CLANGPDB, from zeta base
`35c384e84266343991fd14706e8c651f7d2e09ed`, DarwinBoot
`85332b317ee80898fc78939ea64e6ca52d3837a3`, and Mu
`cfb93724a06ff86ff5ba971413368a7809ee42a5`.
Build logs, commands and source inventory are in
`/root/unixnu-build/zeta-qemu-loaders/`.

## ESP and ADT

Output: `/root/unixnu-build/zeta-qemu-entry-002/`.
Windows access: `\\wsl.localhost\UniXNU-Build\root\unixnu-build\zeta-qemu-entry-002`.

```text
esp/EFI/BOOT/BOOTAA64.EFI
esp/EFI/UniXNU/unixnu.toml
esp/EFI/UniXNU/Payloads/DarwinBoot.efi
esp/EFI/UniXNU/Payloads/kernel.macho
esp/EFI/UniXNU/Payloads/kernel.macho.adt
```

The ADT contains a fresh 256-byte `os.urandom` seed in `/chosen/random-seed`,
round-trip verified after encoding. It describes QEMU virt/A710/GICv3,
2GiB actual VM memory and a 512MiB contiguous DarwinBoot allocation.
Unused Qualcomm UFS placeholders from the upstream fixture were removed.
QEMU presents the directory as a read-only FAT boot disk.

## Observed checkpoint

- QEMU8.2.2/TCG, Cortex-A710, GICv3, one CPU.
- UART confirms UniXNU configuration, DarwinBoot driver start, validated
  handoff and exit from boot services.
- `_arm_init` observed at `0xfffffff007b07758`.
- `_arm_vm_init` entered at `0xfffffff0074ff12c` and returned to
  `0xfffffff007b07f9c`, with the same stack `0xfffffff007d27f30`.
- No timeout. PSTATE `0x600003c4` gives EL1.
- SCTLR_EL1 `0x3454593d`: MMU enabled.
- TCR_EL1 `0x22a51a251a`: TG0 and TG1 both4KiB.
- TTBR0_EL1 `0x49158000`; TTBR1_EL1 `0x49159000`.
- ESR_EL1 and FAR_EL1 are zero at this stop.

`gdb-stop.json` contains the raw observation and stack-match result;
`gdb-uart.log` contains firmware/loader output. `entry-report.json` records
input hashes, commands, host observer changes and the seven successful checks.

The old XNU10063 audit assumes iOS17 and `_sysreg_restore`. XNU12377 constructs
TCR_EL1_BOOT inline; the new probe validates its real runtime register instead.
The only GDB observer adaptation normalizes QEMU8's `SCTLR` name to
`SCTLR_EL1`. The probe performs no guest code or register writes.

Run001 failed in that old-symbol host audit before starting QEMU; run002
is the successful entry test. Both outputs are retained.

## Reproduce

The loader builder preserves existing output; its completed receipt is already
available. The entry runner also requires a new output directory for every run.

```powershell
wsl.exe -d UniXNU-Build -- python3 -B /mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/probe-zeta-wsl-entry.py --output /root/unixnu-build/zeta-qemu-entry-003 --checkpoint arm_vm_init_return --timeout 90
```

Each run gets fresh entropy, so its ADT hash changes.

This checkpoint proves early native kernel entry and VM initialization.
Root/Data and userspace were not attached. Next is platform/CPU initialization,
then matching prelink, root volume, Data seed and userspace qualification.
This run supplies no new phone observation.
