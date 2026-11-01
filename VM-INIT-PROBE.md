# arm_vm_init return probe

The preceding six-second reset test was observed on Mi 11 without any button
press. It confirms execution after initial MMU enable. The next boundary is
the return from `arm_vm_init` in `arm_init`, before serial and video-console
initialization (`osfmk/arm/arm_init.c`:535,549,591 in the staged source).

Candidate: `artifacts/venus-xnu-vm-init/boot-venus-unixnu.img`.
SHA256: `37cd8c7394713d4dd8658b38250726c670a5f24a9c6f75fe0de35d015192759a`.
Size: 34734080 bytes.

Build: `tools/make-venus-vm-init-probe.sh` uses the original native kernel
copy with `--reset-delay 6 --reset-after _arm_vm_init --in _arm_init`, then
reseals the source-crypto integrity field and builds the RAM payload/firmware.
This candidate waits six seconds after that function returns and requests
PSCI SMC SYSTEM_RESET. The earlier stage-3 reset site is not patched here.

Disassembly confirms:

- Original call site: `0xfffffff007a0f5d8`, now branches to stage 4.
- Cave: `0xfffffff007420620`, first instruction calls real `_arm_vm_init`
  at `0xfffffff007418190` with the original argument registers.
- Counter reads start at `0xfffffff007420624`, after that call returns.
- SMC instruction: `0xfffffff007420660`, function ID `0x84000009`.

QEMU stopped at that actual high-VA SMC instruction with x0=0x84000009,
SCTLR_EL1=0x3454593d and TCR_EL1=0x22a51a251a, without timeout. Native 4K
translation is active. The measured kernel physical base is 0x48004000;
the observer also armed the corresponding physical alias. Unlike the
earlier common_start checkpoint, stage 4 executed through the high VA.

Verification command:

```
python3 /mnt/g/UniXNU-Port/tools/test-venus-mmu-reset.py --directory /mnt/g/UniXNU-Port/artifacts/venus-xnu-vm-init --stage 4
```

Evidence: `artifacts/venus-xnu-vm-init/qemu/reset-check.json`,
`qemu/gdb-stop.json`, and `logs/venus-xnu-vm-init-build.log`.
Container checks passed; all 21 reservations are covered, 16 allocation
ranges checked, and no memory conflicts found.

## Phone result

The user explicitly approved this candidate's RAM boot and automatic reset.
Fastboot returned Sending OKAY (0.755 s), Booting OKAY (0.193 s), total
0.957 s. Transcript: `logs/venus-xnu-vm-init-phone.txt`.

The user confirmed an automatic reboot about six seconds after the bands
appeared, in response to the question asking whether no button was pressed.
This matches the function-return reset probe: `arm_vm_init` returned on Mi 11.
Android subsequently reappeared on ADB5037 with sys.boot_completed=1,
kernel 5.4.302-qgki-g7f2a2a060d1d and slot _a. Its boot_a SHA256 remained
`f1adee89d918a25bc62a1a5c05de3d652af121a252588db21a7b2580d3d3dafb`, matching
the original backup.

Serial/video-console initialization and later kernel startup are not yet
observed on the phone. The next useful boundary is `PE_create_console`
after `serial_init`; readable kernel output remains the immediate goal.
This candidate's deliberate reset prevents it from reaching those stages.
