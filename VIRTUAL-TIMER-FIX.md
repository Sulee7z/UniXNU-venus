# SM8350 EL1 physical-timer trap

Photo `G:\a217923c0c9828c9afd5ef414e0eef34.jpg` shows an actual XNU panic:
`Undefined kernel instruction: pc=0xfffffff00741a378 instr=d51be228`,
`sleh.c:1045`. The panic renderer worked after the new prelinked handoff.

Disassembly of that exact payload kernel places the instruction inside
`fiq_context_init`: it first writes CNTV_CTL_EL0, then writes CNTP_CTL_EL0.
The second instruction faults on this phone. The port already uses the
virtual architectural timer, so the SoC patch removes the precautionary
physical-timer mask write and leaves virtual-timer programming intact.
It is selected by the SM8350 series only.

Patch: `UniXNU-sm8350-common/patches/xnu/sm8350-virtual-timer-only.patch`.
SHA256: `920f7f8f780a52365989011c2550ee961e2dbb07c5a11e39581c366782bfefa5`.

The source was rebuilt and prelinked through the official command, not
patched in the deployed executable. Recreating xnu-work exposed a dependency
order issue: existing compile records skipped bootstrap, leaving omitted
TrustCache headers unavailable to archive builders. The complete archive
list now starts with the existing `prepare-xnu-source.py`, using the selected
profile's original Apple header versions and hash validation.

## Verification

- Old kernel contains the photographed CNTP write at exactly 0xfffffff00741a378.
- Rebuilt and final payload kernels contain no CNTP_CTL write in
  fiq_context_init and retain one CNTV_CTL write at 0xfffffff00741a370.
- Both kernels reached a real QEMU rtclock_intr return with a matched stack,
  GIC ready and timer IRQ activity. The rebuilt prelinked kernel also retained
  successful original Apple crypto initialization.
- Boot-image roundtrip, 21 reservations and 16 allocation-range checks passed.

The helper `scripts/check-virtual-timer-fix.py` records code bytes, input
hashes and runtime observations in `evidence/virtual-timer-fix.json`.
QEMU does not reproduce the phone's EL2 access policy; the opcode check
establishes removal of the actual photographed fault instruction.

## Candidate and phone-test attempt

`G:\UniXNU-Port\artifacts\venus-guide-virtual-timer\phone\boot-venus-unixnu.img`

SHA256: `f4381b3598ca76b6cb7eba9f6eeb74690987a51dadf75de7acd278b6402f616b`

Size: 168960000 bytes. Retains entry/panic diagnostics and the compiled
Advanced Logger QR menu. No timed reset is selected. Root/Data/userland
remain absent; this test asks whether the first physical-timer panic is
passed and which kernel initialization stage follows.

Rebuilt kernel SHA256:
`478b3a2c234e24cf0dcad0d71c422d592247cfd385db7ee59e5b49d7f8b825cb`.
Final payload kernel SHA256:
`641313d097fb9295b2415adfd2064d223b4a9337563b17d94810555a82734e0f`.

The user approved this image's RAM boot. Using the verified Android ADB5037
connection, the runner entered fastboot and received Sending OKAY (3.580 s)
and Booting OKAY (0.193 s), total 3.814 s. Transcript:
`G:\UniXNU-Port\logs\venus-guide-virtual-timer-phone.txt`.
The new kernel-screen result remains pending; transport success alone does
not establish that the photographed fault has been passed on the phone.

Subsequent photo `G:\54aa65409b42226aadab1ec2adc131c1.jpg` confirms a later
fault in IODT interrupt-parent resolution, with allocated page counters now
present. The CNTP instruction fault is passed. See `ADT-IRQ-FIX.md` for the
shared-converter cause, exact QEMU reproduction and next candidate.
