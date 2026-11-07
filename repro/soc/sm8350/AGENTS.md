# SM8350 source ownership

This local source owns generic CPU, GIC, PSCI and timer resources for SM8350.
Read README.md, soc.toml and the pinned Linux DTS before changing resources.
Board memory, firmware, storage, display and peripheral wiring remain in the
Venus repository. This source currently covers single-CPU native entry only.
Use the consuming device's assumption and evidence records. Do not turn an
assumed PAC capability into a hardware verification result.
