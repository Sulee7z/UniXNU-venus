# True kernel-entry probes

The user's `20261025_143236.JPG` confirms a visible UniXNU menu followed by
DarwinBoot's handoff page, EL1 and 4 KiB-granule support. DarwinEnter paints
the green band after ExitBootServices and before its final branch. Green
therefore proves loader execution, not native XNU initialization.

Latest candidate:
`artifacts/venus-xnu-probe/boot-venus-unixnu.img`
SHA256 `2d527562432aec86aa1b4969d306b5e99e19be09e850b7b03938418fe1922931`.

The COPY of native XNU has:

- Blue band: actual Mach-O/XNU entry instructions executed with MMU off.
- Magenta band: actual kernel instruction just before SCTLR/MMU enable.
- Panic renderer after the kernel's framebuffer mapping exists.
- No timed reset probe.

Implementation reference: UniXNU-sheng commit
0e1f6e52638137db15905db8d775ad73757f39fa,
scripts/patch-xnu-entry-probe.py. The script rebases through LC_UNIXTHREAD
and resolves native symbols/SCTLR instruction sequences, refusing mismatched
sites or occupied caves. It does not copy Sheng's hardware addresses.

Text instrumentation changes integrity input. The modified copy is resealed
using the real source corecrypto HMAC build contract; selftests are retained.
The original native kernel and previous artifacts are unchanged.

QEMU with actual GOP exercised this probe-enabled kernel through UniXNU and
DarwinBoot: native 4K, crypto initialization, GIC readiness, one timer IRQ and
rtclock_intr return observed; no deadline interruption. This is an offline
result. The user approved the new candidate's RAM boot. Fastboot returned
Sending/Booting OKAY (0.958 s); no partition was flashed. Actual kernel
entry/colour-band result remains pending the user's photo.

The user confirmed green, blue and magenta bands on Mi 11. Actual XNU entry
and the verified instruction site just before MMU enable have executed.
Post-MMU startup and userspace are still unverified. The next optional
stage-3 reset diagnostic uses CNTVCT at the observed 19.2 MHz timebase, then
PSCI SMC SYSTEM_RESET after six seconds. It requires separate approval for
the RAM boot and intentional automatic reset. A missing reset is ambiguous
until reset/counter behaviour is verified; it is not proof of MMU failure.
