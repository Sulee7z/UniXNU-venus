# Official-guide alignment

Reviewed on 2026-10-25, starting at https://unixnu.com/zh/porting/.
The website and its linked Markdown sources were read through the eight-step
workflow and all porting-sidebar chapters. The local reference implementation
is UniXNU `16e592abee8a550dec8154ed1f38b5ebc4f16213` in
`G:\UniXNU-Port\sources\UniXNU-guide`.

## Reading coverage

Under `https://unixnu.com/zh/`:

- `porting/`: welcome, steps, migration, device-repository, soc-support,
  device-tree, uefi-firmware, dual-system-partition, drivers, platform, ufs,
  display, input, gpu, network, power, bring-up, log-capture, records.
- `reference/components`, `building`, `drivers/overview`,
  `contributing/documentation`, `xnu/source-and-patches`.
- `concepts/prelink`, `concepts/payload`, `guide/requirements`,
  `guide/userdata`, `guide/debugging`, `drivers/arm-cpu`,
  `drivers/arm-dt-platform`.

Component metadata, profile files, the resolver, hardware converter, patch
planner and prelink implementation were also inspected for the selected work.

## Scope and findings

The user temporarily removed Android retention from the goal. The former
pinned-F2FS-file design is deferred. The storage target follows the guide's
userdata OS/SystemOS manifest layout, followed by an explicitly allocated
Data store. No phone partition was changed by this migration.

The preceding work was a native-kernel diagnostic pipeline with valid phone
observations, but lacked the guide's device/profile/record entry points and
the Apple prelinked components needed for the intended userspace path.

The default guide OS profile is iPadOS 17.7.11 (21H461), iPad7,1/J120, matching
XNU 10063.141.1. This is the selected ABI baseline, not a claim that an iPhone
UI identity has been implemented. Apple identity comes from the OS profile;
hardware values come from Venus.

The queried `UniXNU/UniXNU-sm8350-common` repository returned HTTP 404. A local
SM8350 description was therefore added and is explicitly selected as an
unpublished local source. It does not provide UFS, GPU or peripheral platform
operations. In particular, ShengUfs uses a different PHY and Adreno740 is
for a different GPU generation.

## Implemented and checked

1. Added `board.toml`, `venus_defconfig`, feed/local-override files, ordered
   patch series, README, AGENTS, proprietary input hashes and record workflow.
2. Added a shared SM8350 CPU/GIC/timer DTSI and a Venus DTS. The shared ADT
   converter requires one continuous bank; the selected real bank is
   0xc0000000 + 0x1c0000000. The other bank remains in the evidence. This is
   DRAM geometry; actual allocations still depend on firmware reservations.
3. Imported all 21 fixed live reservations, retaining no-map attributes.
   The checker compared eight CPU affinities, the single enabled CPU, GIC,
   timer and PSCI with the hash-pinned live FDT. dtc produced no warnings.
4. Ran official defconfig, source fetch, status and tree commands. References
   are locked in `unixnu.lock`; selected components also have catalog and
   superproject pins. The SoC/device local sources remain unpublished.
5. Ran the official record checker: all 13 areas passed. Generated a host-test
   ADT through the shared converter with an explicitly identified fixture seed.
6. Verified IPSW identity and fetched/decompressed its pinned kernelcache,
   original Apple DeviceTree and two trust caches. OS/SystemOS disk images
   and a Data seed have not been downloaded or assembled.
7. Built the native kernel and completed the official XnuPrelink step with
   the selected profile's original Apple components.

## Build findings

- The current OS progress patch assumes a conditional PMGR call site omitted
  from the generic profile. `profile-prerequisites.series` explicitly places
  the existing `sheng-platform-power.patch` before it. `XNU_SHENG_PMGR` stays
  disabled; no Sheng platform operation is enabled by this compatibility fix.
  The resulting 57-patch sequence applied successfully.
- The two XnuPrelink patch files checked out on Windows had CRLF endings.
  They were normalized to LF and checked against their Git index with
  `git diff --exit-code`; their patch contents are unchanged.
- The first build on `/mnt/g` hit the 1200-second runner limit. The successful
  build uses `/root/unixnu-build/venus-guide-out` in the existing G:-backed
  WSL VHDX. Source caches were reused; compile records were regenerated for
  their new absolute paths. `tools/build-venus-guide.sh` exports results to G:.
- The official first pass intentionally stops before all archives are linked.
  Its missing mockfs symbols are followed by successful archive construction,
  final kernel linking and prelink. The complete build exited zero.

Output: `G:\UniXNU-Port\artifacts\venus-guide-linux\kernel\kernel.macho`

SHA256: `8d7a798ed7971fae50e7ec938859d8d34414e37a801aaabab525a5884f6526c6`

Size: 51011584 bytes. `kernel.json` records 30 executable Apple components
and the codeless IOHIDEventDriver. Prelink reports executable bytes unchanged
and runtime unqualified at build time. Subsequent QEMU platform/crypto/timer
and APFS-load checks are recorded in `PRELINKED-RUNTIME.md`; phone execution
of the new candidate is still pending. Legacy device checkpoints do not
transfer automatically.

Evidence summaries are in `evidence/format2-check.json` and
`evidence/official-build.json`. Detailed logs are under
`G:\UniXNU-Port\artifacts\venus-guide-linux\logs` and
`G:\UniXNU-Port\logs\venus-guide-*.log`.

## Next dependencies in guide order

1. Verify the new prelinked kernel's entry/platform path in QEMU; then test
   the matching Venus ADT/firmware handoff and recover readable kernel logs.
2. Audit the shared initrd and AdvancedLogDxe integration against Venus's
   concatenated Android-v3 ramdisk, and verify the new firmware/container.
3. Implement SM8350 UFS ownership/PHY/clock/SMMU and known-block reads.
   Recheck actual GPT/LUN/block units before adding userdata geometry.
4. Assemble OS/SystemOS and a matching Data seed, determine root UUID and
   trust-cache packaging, then validate root mount and launchd.
5. Adapt OS framebuffer presentation/brightness, input and the A660 backend,
   followed by network, audio and power, following their individual guides.
