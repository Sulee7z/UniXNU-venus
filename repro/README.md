# Source rebuild work

This directory is being assembled from the source recipes of the user-confirmed
066 Venus build. No kernel object, static driver archive, Apple executable,
SDK binary, device identifier or signing private key belongs in this directory.

The native closure contains 1,069 kernel link objects, plus source-built platform,
UFS, HID, display, pthread and cryptography components. Source files and generated
public headers must be locked by SHA-256 before a clean rebuild is accepted.

Apple KDK 25F84 headers, a matching prepared kernel SDK, the XNU-enabled LLVM
toolchain and factory firmware inputs remain external prerequisites. Their
locations must be supplied through local configuration, not a previous build
directory. Original Data seeds remain separate private installation inputs.

Published as a source snapshot at the user's request. Native source rebuilding
and prelinking completed; standard clean-checkout packaging remains unqualified.
The main branch is not modified.
