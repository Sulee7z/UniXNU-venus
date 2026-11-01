// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once

namespace VenusUfsSurvey {
struct Result {
  uint32_t errors = 0;
  uint32_t gdsc = 0, axi = 0, ahb = 0, unipro = 0, aggregate = 0;
  uint32_t hcRead = 0, cap = 0, version = 0, hcs = 0, hce = 0, is = 0, ie = 0;
  uint32_t transferRun = 0, transferDoorbell = 0, taskRun = 0, taskDoorbell = 0;
  uint64_t transferBase = 0, taskBase = 0;
  uint32_t smmuRead = 0, scr0 = 0, idr0 = 0, idr1 = 0, idr2 = 0, gfsr = 0;
  uint32_t slots = 0, matches = 0, slot = 0xffffffff, smr = 0, s2cr = 0;
  uint32_t cbRead = 0, cb = 0xffffffff, users = 0, cbar = 0, cba2r = 0, sctlr = 0;
  uint64_t ttbr0 = 0;
};

inline bool clockUsable(uint32_t value)
{
  return (value & 1) && (!(value & 0x80000000U) || (value & 2));
}

// Callbacks expose reads only. Offsets are bounded by the board's mapped GCC,
// UFSHCI and SMMUv2 windows; this code neither allocates DMA nor changes MMIO.
template<class GccRead, class HostRead, class SmmuRead>
Result collect(GccRead gcc, HostRead hc, SmmuRead smmu)
{
  Result r;
  if (!gcc(0x004, r.gdsc) || !gcc(0x010, r.axi) || !gcc(0x018, r.ahb) ||
      !gcc(0x05c, r.unipro) || !gcc(0x0cc, r.aggregate)) {
    r.errors |= 1;
    return r;
  }
  if ((r.gdsc & 0x80000000U) && clockUsable(r.axi) && clockUsable(r.ahb) &&
      clockUsable(r.unipro) && clockUsable(r.aggregate)) {
    uint32_t lo = 0, hi = 0;
    bool ok = hc(0x00, r.cap) && hc(0x08, r.version) && hc(0x20, r.is) && hc(0x24, r.ie) &&
              hc(0x30, r.hcs) && hc(0x34, r.hce) && hc(0x50, lo) && hc(0x54, hi);
    r.transferBase = (uint64_t(hi) << 32) | lo;
    ok = ok && hc(0x58, r.transferDoorbell) && hc(0x60, r.transferRun) &&
         hc(0x70, lo) && hc(0x74, hi);
    r.taskBase = (uint64_t(hi) << 32) | lo;
    ok = ok && hc(0x78, r.taskDoorbell) && hc(0x80, r.taskRun);
    r.hcRead = ok;
    if (!ok) r.errors |= 2;
  }
  if (!smmu(0x00, r.scr0) || !smmu(0x20, r.idr0) || !smmu(0x24, r.idr1) ||
      !smmu(0x28, r.idr2) || !smmu(0x48, r.gfsr)) {
    r.errors |= 4;
    return r;
  }
  r.smmuRead = 1;
  r.slots = r.idr0 & 0xff;
  uint32_t banks = r.idr1 & 0xff;
  uint32_t pages = 1U << (((r.idr1 >> 28) & 7) + 1);
  if ((r.idr1 & 0x80000000U) || !r.slots || r.slots > 128 || !banks || banks > 128 || pages > 128 ||
      (pages + banks) * 4096U > 0xd0000U) {
    r.errors |= 8;
    return r;
  }
  uint32_t smrs[128] = {}, s2crs[128] = {};
  for (unsigned i = 0; i < r.slots; ++i) {
    if (!smmu(0x800 + 4 * i, smrs[i]) || !smmu(0xc00 + 4 * i, s2crs[i])) {
      r.errors |= 4;
      return r;
    }
    uint32_t mask = (smrs[i] >> 16) & 0x7fff;
    if ((smrs[i] & 0x80000000U) && !(((smrs[i] ^ 0xe0U) & 0x7fff) & ~mask)) {
      ++r.matches;
      r.slot = i;
      r.smr = smrs[i];
      r.s2cr = s2crs[i];
    }
  }
  if (r.matches != 1 || ((r.smr >> 16) & 0x7fff) || ((r.s2cr >> 16) & 3)) return r;
  r.cb = r.s2cr & 0xff;
  if (r.cb >= banks) {
    r.errors |= 8;
    return r;
  }
  for (unsigned i = 0; i < r.slots; ++i) {
    if ((smrs[i] & 0x80000000U) && !(s2crs[i] & 0x30000) && (s2crs[i] & 0xff) == r.cb) ++r.users;
  }
  uint32_t lo = 0, hi = 0;
  uint32_t base = (pages + r.cb) * 4096;
  bool ok = smmu(0x1000 + 4 * r.cb, r.cbar) && smmu(0x1800 + 4 * r.cb, r.cba2r) &&
            smmu(base, r.sctlr) && smmu(base + 0x20, lo) && smmu(base + 0x24, hi);
  r.ttbr0 = (uint64_t(hi) << 32) | lo;
  r.cbRead = ok;
  if (!ok) r.errors |= 4;
  return r;
}
}
