# Venus porting work

Read README.md, board.toml and porting.toml before implementation. Follow
https://unixnu.com/zh/porting/steps and the relevant platform/driver guide.
Use the format-2 component catalog, OS profile and ordered patch series.
Read the selected implementation and verify SM8350 hardware and OS ABI
requirements before adopting it. Update findings/evidence with each change.

The user supplied the official dual-system guide for renewed evaluation.
Use explicit root-partition selection. The user chose a separate 64 GiB unixnu
partition and permits Android userdata/metadata to be erased and reinitialized
as part of a specifically approved deployment sequence. The approved GPT change
and Android reset have completed; Android boot is confirmed. Further root-image
flashing and RAM boots need their own exact-operation authorization. Keep the old
pinned-file proposal deferred. Ask before each phone reboot, RAM boot or storage write,
including the exact image and operation. Local work remains on G: or the
existing G:-backed WSL environment. Do not use subagents. Do not commit or
publish without an explicit request.

The user authorizes ordinary reads and writes throughout G: and its WSL
workspace. Request that whole scope if a tool requires directory approval;
do not ask the user separately for routine project file operations. This is
not an authorization for phone reboots, RAM boots or partition/device writes.

Run the official porting-record checker and checks relevant to the change.
Distinguish the legacy native-kernel hardware results from this format-2
configuration, prelinked builds and iOS userspace observations.
