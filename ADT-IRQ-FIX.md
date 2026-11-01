# ADT interrupt-parent identity

Photo `G:\54aa65409b42226aadab1ec2adc131c1.jpg` shows the virtual-timer
candidate passed the prior CNTP fault and reached a later kernel data abort:
PC `0xfffffff0078e5bb4`, LR `0xfffffff0078e3e98`, FAR zero, ESR `0x96000005`.
These map to `IODTGetICellCounts` and `IODTMapInterruptsSharing`.

The exact XNU source uses `AAPL,phandle` in AddPHandle/FindPHandle. The shared
FDT converter emitted `phandle` and an `interrupt-parent` reference but no
Apple alias. Consequently the controller was not indexed and lookup returned
NULL. No null-dereference bypass was added to XNU: the hardware description
now supplies the missing provider identity.

Local shared-tool correction in `scripts/unixnu/devicetree.py`:

- Emit little-endian `AAPL,phandle` for exported nodes with either FDT alias.
- Preserve existing FDT spellings and numerical values.
- Reject conflicting/reserved aliases and references to interrupt parents
  that will not actually be exported to ADT.

Upstream base is `16e592abee8a550dec8154ed1f38b5ebc4f16213`; this is a local
change, not a published upstream revision. Converter SHA256:
`25eab74c1091a7d84322bfa0805a492d418138834920c982ac796025512e5645`.

## Runtime regression

The former minimal QEMU tree had no timer interrupt-parent reference, so it
did not cover this failure. `qemu/shared-generator.dts` now describes actual
QEMU CPU/RAM/GIC/timer resources and feeds the shared converter with the OS
profile. The existing observer accepts this explicit fixture ADT.

Using the same kernel for both runs:

1. Before correction, QEMU reproduced the photo's exact PC, LR, FAR and ESR.
2. After correction, platform configuration, original Apple crypto and the
   real timer-interrupt return succeeded, without timeout.
3. Six converter regression tests passed, including Linux-only/equal aliases,
   conflicting handles and missing/unexported interrupt providers.
4. Updated English and Chinese device-tree docs passed the full VitePress build.

Detailed evidence: `evidence/adt-irq-fix.json`. Full QEMU reports remain in
`artifacts/venus-guide-virtual-timer/qemu-shared-before` and
`qemu-shared-after` under the workspace root.

## Candidate and approved RAM-boot attempt

`G:\UniXNU-Port\artifacts\venus-guide-adt-fix\boot-venus-unixnu.img`

SHA256: `cedcfa3ac0e61cc6338ab7d31f55a1230a5d3bd4802b7ba140e314a6858549f3`.
Size: 168960000 bytes. Kernel bytes are identical to the virtual-timer
candidate's payload kernel. Its actual extracted phone ADT now has equal
intc `AAPL,phandle`, intc `phandle` and timer `interrupt-parent` values (1).
No timed reset or iOS root/Data volume is included.

The user approved this exact candidate. RAM boot via the same device's
ADB5037 connection returned Sending OKAY (3.601 s), Booting OKAY (0.193 s),
total 3.836 s. Transcript: `logs/venus-guide-adt-fix-phone.txt` in the workspace.
The new screen/kernel result is pending the user's observation.

The user then supplied `G:\216f880c02fc58cb6fb54c076389fd52.jpg`: all three
entry bands appeared, followed by original AMFI's `No PMGR?` panic. The
interrupt-parent null dereference is passed on the phone. The new dependency
and completed static ABI audit are recorded in `PMGR-DEPENDENCY.md`.

The missing Node runtime for docs verification was supplied locally as
Node v24.10.0, with the distribution archive hash verified against nodejs.org.
The build ran in the existing G:-backed WSL filesystem; no system Node install
was required. Command: `python3 /mnt/g/UniXNU-Port/tools/check-guide-docs.py`.
