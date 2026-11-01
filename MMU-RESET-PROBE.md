# Post-MMU reset observation

Candidate: `artifacts/venus-xnu-mmu-reset/boot-venus-unixnu.img`.
SHA256 `82bf166cddce680e286f8860f779e78035f98d466e673b1abcc3806039f64f7a`.
Size: 34734080 bytes.

The stage-3 code replaces the verified instruction after MMU enable,
preserves its original entry semantics, waits six seconds using CNTVCT and
the live CNTFRQ value, then requests PSCI SMC SYSTEM_RESET. It uses the original
validated probe caves. The panic renderer is omitted because the combined
stage-3/renderer did not fit in that known padding. The original native kernel
and the successful no-reset blue/magenta probe remain unchanged.

The copied kernel's source-crypto integrity field is normally resealed.
No kernel crypto selftest or original input-instruction validation is skipped.

QEMU observed the real SMC opcode before execution with x0=0x84000009,
SCTLR.M set and active 4K TTBRs. The code at this stage still runs through
the identity-mapped physical alias: the observer derives that address from
the actual DarwinBoot allocation and checks allocation consistency in the
new run. The earlier virtual-address breakpoint could not observe this site.
QEMU's PSCI conduit differs from the phone, so the observer stops before SMC
and does not claim the actual phone reset is proven.

The phone's six-second automatic reset is an intentional test and requires
an explicit popup approval. No Android partition or data-file change is part
of this test. If no reset happens, MMU/counter/reset behaviour remains ambiguous
and another independent checkpoint is needed.

Phone result: the user approved the RAM boot and intentional reset, then
confirmed no button press and an automatic reboot about six seconds after
the bands appeared. Android returned with sys.boot_completed=1 and the
original boot_a SHA256 unchanged. Actual post-MMU probe execution is therefore
observed on Mi 11. Later platform/init/userspace stages remain unverified.
