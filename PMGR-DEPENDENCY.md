# AMFI PMGR service dependency

Latest photo: `G:\216f880c02fc58cb6fb54c076389fd52.jpg`.
Image: `artifacts/venus-guide-adt-fix/boot-venus-unixnu.img`, SHA256
`cedcfa3ac0e61cc6338ab7d31f55a1230a5d3bd4802b7ba140e314a6858549f3`.

The user observed green/blue/magenta bands followed by:
`AMFI: No PMGR?`, `ConfigurationSettings.cpp:235`.
The previous CNTP undefined instruction and IODT interrupt-parent null
dereference are passed. The present failure is the original Apple component's
missing platform service, not a root-volume observation.

## Contract audit completed

Command:

```
python3 /mnt/g/UniXNU-Port/sources/UniXNU-guide/scripts/audit-amfi-pmgr-contract.py --candidate /mnt/g/UniXNU-Port/artifacts/venus-guide-virtual-timer/kernel/kernel.macho --kernelcache /mnt/g/UniXNU-Port/artifacts/venus-guide/ipsw/21H461/kernelcache.decompressed
```

Result: exit zero. Log: `G:\UniXNU-Port\logs\venus-amfi-pmgr-audit.log`.
Report: `sources/UniXNU-guide/build/amfi-pmgr-contract/report.json` under
the workspace. The audit now accepts the original kernelcache explicitly,
and records both candidate and kernelcache hashes.

Verified against the exact original executable bytes and rebound imports:

- Service class: `ApplePMGRNub`.
- Nub provider field offset: 0x88.
- Read/write provider vtable slots: 320/321 (byte offsets 0xa00/0xa08).
- AMFI reads a 32-bit value, ORs bit 2 and invokes the corresponding write.
- The original target AppleT8011PMGR implementations return 0xffffffff on
  this read and return immediately from this write, without MMIO.
- AMFI executable SHA256:
  `a1088aaabc259418ed503d08df29b6146470b8c962696c688122a1f60a141db6`.
- ApplePMGR executable SHA256:
  `2c433279d004803b7ef02948e550ad6b77aa3f84b02a06a357e00fa738310a99`.

These are static contract facts. No platform service or hardware power
function has been implemented or validated by this audit.

## Reference reviewed and next implementation

Read UniXNU-sheng `0e1f6e52638137db15905db8d775ad73757f39fa`:

- `package/ShengPlatformPower.cpp` (MIT).
- `scripts/build-sheng-platform-power.py`.
- `scripts/check-sheng-pmgr-observation.py`.

The reference preserves the original ApplePMGRNub and original AON methods,
uses a guarded provider with the exact original storage/vtable ABI, and has
separate lifecycle, publication and unimplemented-operation tests. It does
not implement Snapdragon clocks, sleep or CPU power control.

Next steps:

1. Adapt the build input paths to `kits/venus` and the selected bootstrap
   candidate/kernelcache; retain original source/runtime identifiers and ABI
   checks (provider size 0x4b8a8, nub size 0x740, 340 provider slots).
2. Add the reviewed archive recipe to the complete archive list and enable
   the existing `XNU_SHENG_PMGR` call site only with its implementation linked.
   The existing shell linker expects `build/sheng-platform-power/libShengPlatformPower.a`.
3. Verify unpublished lifecycle, real service publication and refusal behavior
   in QEMU. `sheng-pmgr=2` selects reference publication; the boot argument alone
   cannot supply the missing archive/service.
4. Build a separate candidate and request its specific RAM-boot approval.

The implementation steps above are now complete through QEMU verification:
`CONFIG_XNU_SHENG_PMGR=y`, the audited archive is linked, and publication is
selected with `sheng-pmgr=2`. Lifecycle, publication, unsupported-operation
and original-AMFI-call tests passed. Kernel and payload reached IOFindBSDRoot.
See `ZETA-REUSE.md` and `evidence/pmgr-integration.json` for the new candidate.
The phone subsequently passed the AMFI failure and reached the IOMedia
matching timeout (`Failed to mount root device`, IOKitBSDInit.cpp:984).
Root/Data/userland remain unverified. The next blocker is physical storage
and a correctly described root volume.
