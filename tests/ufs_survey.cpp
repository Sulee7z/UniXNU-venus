// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <map>
#include <vector>
#include "../package/VenusUfsSurvey.h"

int main()
{
  std::map<unsigned, uint32_t> g, h, s;
  std::vector<unsigned> hr, sr;
  auto reset = [&] {
    g = {{4, 0x80000000}, {0x10, 1}, {0x18, 0x80000003}, {0x5c, 1}, {0xcc, 1}};
    h = {{0, 0x1587031f}, {8, 0x300}, {0x30, 0x10f}, {0x34, 1},
         {0x50, 0x9d987000}, {0x54, 1}, {0x60, 1}};
    s = {{0x20, 4}, {0x24, 0x60000003}, {0x808, 0x800000e0}, {0xc08, 2},
         {0x80c, 0x800000e1}, {0xc0c, 2}, {0x1008, 0x1f000}, {0x1808, 1},
         {130 * 4096, 1}, {130 * 4096 + 0x20, 0x12345000}};
    hr.clear(); sr.clear();
  };
  auto collect = [&] {
    return VenusUfsSurvey::collect(
      [&](unsigned o, uint32_t &v) { assert(o < 4096 && !(o & 3)); v = g[o]; return true; },
      [&](unsigned o, uint32_t &v) { assert(o < 0x3000 && !(o & 3)); hr.push_back(o); v = h[o]; return true; },
      [&](unsigned o, uint32_t &v) { assert(o < 0xd0000 && !(o & 3)); sr.push_back(o); v = s[o]; return true; });
  };
  reset(); auto r = collect();
  assert(!r.errors && r.hcRead && r.smmuRead && r.cbRead);
  assert(r.transferBase == 0x19d987000ULL && r.matches == 1 && r.cb == 2 && r.users == 2);
  assert(r.cbar == 0x1f000 && r.ttbr0 == 0x12345000);
  for (unsigned offset : {4U, 0x10U, 0x18U, 0x5cU, 0xccU}) {
    reset(); g[offset] = 0; r = collect(); assert(!r.hcRead && hr.empty());
  }
  reset(); g[0x18] = 0x80000001; r = collect(); assert(!r.hcRead && hr.empty());
  reset(); s[0x800] = 0x800000e0; s[0xc00] = 2; r = collect(); assert(r.matches == 2 && !r.cbRead);
  reset(); s[0x808] |= 0x10000; r = collect(); assert(r.matches == 1 && !r.cbRead);
  reset(); s[0xc08] = 0x10002; r = collect(); assert(!r.cbRead);
  for (uint32_t idr1 : {0x60000000U, 0x70000003U, 0x600000ffU, 0xe0000003U}) {
    reset(); s[0x24] = idr1; r = collect(); assert(r.errors & 8); assert(!r.cbRead);
  }
  reset(); s[0x20] = 129; r = collect(); assert(r.errors & 8);
  reset(); s[0xc08] = 3; r = collect(); assert(r.errors & 8);
  auto fail = [](unsigned, uint32_t &) { return false; };
  auto forbidden = [](unsigned, uint32_t &) { assert(false); return false; };
  r = VenusUfsSurvey::collect(fail, forbidden, forbidden); assert(r.errors == 1);
  puts("PASS: readonly UFS survey, clock gates, shared/ambiguous streams, bounded SMMU geometry and mapping failure");
}
