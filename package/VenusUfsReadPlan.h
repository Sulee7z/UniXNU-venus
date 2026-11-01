// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
// Included after SmmuTakeover.h. Only the explicitly selected block-read probe
// uses this stricter handoff policy; it never creates a previously absent SID.
namespace VenusUfsReadPlan {
struct Candidate {
  unsigned bank = 0xffffffffU;
  uint32_t cbar = 0, cba2r = 0, sctlr = 0;
  const char *reason = nullptr;
  bool contextRead = false;
};
struct Plan {
  UfsSmmuPlan route;
  uint64_t dma = 0, bytes = 0;
  uint32_t scr0 = 0, idr0 = 0, idr1 = 0, idr2 = 0;
  uint32_t cbar = 0, cba2r = 0, sctlr = 0;
  const char *error = nullptr;
  unsigned examined = 0;
  Candidate candidates[8];
};
template<class Read>
Plan prepare(uint64_t dma, uint64_t bytes, Read read)
{
  Plan p;
  p.dma = dma; p.bytes = bytes;
  p.scr0 = read(0); p.idr0 = read(0x20); p.idr1 = read(0x24); p.idr2 = read(0x28);
  // Require enabled clients, ordinary SMR-valid semantics, and the complete
  // accessible stream table. Do not truncate a larger table or enable EXIDS.
  if ((p.scr0 & ((1U << 3) | 1U)) || !(p.idr0 & (1U << 27)) ||
      !(p.idr0 & 255) || (p.idr0 & 255) > 128) {
    p.error = "unsupported SMMU stream mode"; return p;
  }
  // Apply both the original ownership checks and this board's context-state
  // checks to each candidate. Do not stop at the first M-clear bank if its
  // remaining state is unqualified. Keep the original eight-bank bound.
  for (unsigned attempt = 0; attempt < 8; ++attempt) {
    p.route = planUfsSmmuBank(0xe0, dma, bytes, read, attempt, true);
    Candidate &c = p.candidates[p.examined++];
    c.bank = p.route.bank; c.reason = p.route.error;
    if (p.route.error) {
      if (!__builtin_strcmp(p.route.error, "reserved context bank already used") ||
          !__builtin_strcmp(p.route.error, "reserved context bank not bypass")) continue;
      p.error = p.route.error; return p;
    }
    if ((!p.route.retarget && !p.route.reuse) || p.route.smr != 0x800000e0U ||
        (p.route.s2cr & ~255U) || (p.route.s2cr & 255) >= (p.idr1 & 255)) {
      p.error = "missing exact firmware UFS route"; return p;
    }
    c.cbar = read(0x1000 + 4 * p.route.bank);
    c.cba2r = read(0x1800 + 4 * p.route.bank);
    c.sctlr = read((p.route.pages + p.route.bank) * 4096);
    c.contextRead = true;
    p.cbar = c.cbar; p.cba2r = c.cba2r; p.sctlr = c.sctlr;
    // Match the successful SM8350 initialization order: an unreferenced,
    // M-clear bank can have nonzero reset fields before SCTLR is written.
    // Venus photos show CBAR=CBA2R=0 and M=0 in all eight unused candidates.
    // Full SCTLR=0 is a POST-write requirement, enforced by configureUfsSmmu.
    bool resetState = !p.route.reuse && !p.cbar && !p.cba2r;
    if ((p.sctlr & 1) || (!resetState && p.sctlr) ||
        (p.cbar && p.cbar != 0x10000) || (p.cba2r & ~1U)) {
      c.reason = "unqualified context state"; continue;
    }
    return p;
  }
  p.error = "no qualified context in bounded bank scan";
  return p;
}
template<class Read, class Write>
const char *configure(const Plan &p, Read read, Write write)
{
  if (p.error) return p.error;
  // Rescan all stream users and the chosen bank immediately before any write.
  // In particular, a different SID newly sharing the candidate bank refuses.
  Plan q = prepare(p.dma, p.bytes, read);
  if (q.error) return q.error;
  bool resetState = !p.route.reuse && !p.cbar && !p.cba2r;
  // Before initializing an unused reset-state bank, only M is an activity
  // condition; unspecified non-M reset bits are not an ownership token.
  uint32_t sctlrMask = resetState ? 1U : 0xffffffffU;
  if (q.scr0 != p.scr0 || q.idr0 != p.idr0 || q.idr1 != p.idr1 || q.idr2 != p.idr2 ||
      q.cbar != p.cbar || q.cba2r != p.cba2r || ((q.sctlr ^ p.sctlr) & sctlrMask) ||
      q.route.slot != p.route.slot || q.route.bank != p.route.bank || q.route.pages != p.route.pages ||
      q.route.smr != p.route.smr || q.route.s2cr != p.route.s2cr ||
      q.route.reuse != p.route.reuse || q.route.retarget != p.route.retarget)
    return "SMMU ownership changed before configuration";
  return configureUfsSmmu(p.route, 0xe0, read, write);
}
}
