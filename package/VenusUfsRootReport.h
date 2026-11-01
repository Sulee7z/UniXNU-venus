// SPDX-License-Identifier: BSD-2-Clause-Patent
static bool venusRootClocksReady(void)
{
  OSSharedPtr<IOMemoryMap> map;
  uintptr_t gcc = mapPhys(GCC_BASE + 0x77000, 4096, map);
  return gcc && (read32(gcc, 4) & 0x80000000U) &&
    VenusUfsSurvey::clockUsable(read32(gcc, 0x10)) && VenusUfsSurvey::clockUsable(read32(gcc, 0x18)) &&
    VenusUfsSurvey::clockUsable(read32(gcc, 0x5c)) && VenusUfsSurvey::clockUsable(read32(gcc, 0xcc));
}
static void venusBankRefusal(const VenusUfsReadPlan::Plan &plan)
{
  native_ufs_status = kIOReturnNotReady;
  gRootDiagnostic.result = kIOReturnNotReady;
  gRootDiagnostic.smmuBank = plan.route.bank;
  gRootDiagnostic.sctlr = plan.sctlr;
  gRootDiagnostic.cbar = plan.cbar;
  gRootDiagnostic.cba2r = plan.cba2r;
  rootDiagnosticFailure(plan.error);
  panic("VENUS UFS ROOT: %s", plan.error);
}
