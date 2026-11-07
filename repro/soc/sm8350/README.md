# Local SM8350 native-entry support

The payload handoff exports `/cpus/timebase-frequency` from the declared
19.2 MHz timer and exports the GIC at `/arm-io/intc`, as ArmCpu expects.

Format-2 SoC source for the Venus iPhone27 arm64e development target. It supplies
CPU affinities, GICv3 ranges, PSCI SMC and the 19.2 MHz virtual-timer description.
The resources come from Linux v6.12 sm8350.dtsi, whose downloaded SHA256 is
c217376cecfe22f567eea7d31ff66d14ade316c38e5a4b52e2c104bdb7b58616.

All eight CPU nodes are described; the board enables its boot CPU only for the
first native-entry build. This is local source development, with no published
Git revision. It does not implement UFS, GPU power, touch, or board firmware.

The selected xnu-12377 series retains virtual timer initialization and omits
the precautionary CNTP_CTL_EL0 access, as required by the existing SM8350
bring-up path. Native PAC implementation is selected under the user's explicit
development assumption. Actual PAC hardware qualification remains separate.

The optional platform-power patch supplies only a conditional call site needed
by the shared boot-progress patch. It carries no SM8550 register operations and
does not supply a board power implementation.
