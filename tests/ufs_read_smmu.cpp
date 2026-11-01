// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <vector>
#include <utility>
#include "SmmuTakeover.h"
#include "VenusUfsReadPlan.h"
int main()
{
  std::array<uint32_t, 0xd0000 / 4> r{};
  std::vector<std::pair<unsigned, uint32_t>> writes;
  auto reset = [&] {
    r.fill(0); writes.clear(); r[0] = 0x290406;
    r[0x20/4] = 0x4c017e59; r[0x24/4] = 0x6000004b; r[0x28/4] = 0x5111;
    r[0x808/4] = 0x800000e0; r[0xc08/4] = 2;
    r[0x1008/4] = 0x1f000; r[0x1808/4] = 1; r[0x82000/4] = 0xa9f00e0;
  };
  auto read = [&](unsigned at) { assert(!(at & 3)); return r.at(at/4); };
  auto write = [&](unsigned at, uint32_t v) { writes.emplace_back(at, v); r.at(at/4) = v; };
  auto plan = [&] { return VenusUfsReadPlan::prepare(0xe0000000, 0x22000, read); };
  reset(); auto p = plan(); assert(!p.error && p.route.bank == 74 && p.route.retarget);
  auto original = r;
  assert(!VenusUfsReadPlan::configure(p, read, write));
  assert(read(0xc08) == 74 && writes.size() == 4);
  for (auto [at, value] : writes) {
    (void)value;
    assert(at == 0xca000 || at == 0x1928 || at == 0x1128 || at == 0xc08);
    original[at/4] = r[at/4];
  }
  assert(original == r); // Including all of the original bank 2 and its SMR.
  for (auto change : {std::pair<unsigned,uint32_t>{0x80c, 0x800000e0}, {0x808,0x800100e0},
                     {0x808,0}, {0xc08,0x10002},
                     {0x20,0x4c017e81}, {0x24,0xe000004b}, {0x28,0x5116}, {0,0x29040e}}) {
    reset(); r[change.first/4] = change.second; p = plan(); assert(p.error);
    assert(VenusUfsReadPlan::configure(p, read, write) && writes.empty());
  }
  for (auto change : {std::pair<unsigned,uint32_t>{0xc08,3}, {0x1928,1}, {0x28,0x5112}, {0xca000,1}}) {
    reset(); p = plan(); r[change.first/4] = change.second;
    assert(VenusUfsReadPlan::configure(p, read, write) && writes.empty());
  }
  reset(); p = plan(); r[0x80c/4] = 0x800000e1; r[0xc0c/4] = 74;
  assert(VenusUfsReadPlan::configure(p, read, write) && writes.empty());
  reset(); assert(VenusUfsReadPlan::prepare(0xfffffffffULL, 2, read).error);
  for (auto change : {std::pair<unsigned,uint32_t>{0x1128,0x1f000}, {0x1928,0x10001}}) {
    reset(); r[change.first/4] = change.second; p = plan();
    assert(!p.error && p.route.bank == 73 && p.examined == 2);
    assert(p.candidates[0].contextRead && p.candidates[0].reason);
    auto before = r;
    assert(!VenusUfsReadPlan::configure(p, read, write));
    assert(read(change.first) == change.second);
    for (auto [at, value] : writes) { (void)value; before[at/4] = r[at/4]; }
    assert(before == r);
  }
  reset(); for (unsigned i = 0; i < 8; ++i) r[(0x1128 - i * 4)/4] = 0x1f000;
  p = plan(); assert(p.error && p.examined == 8 && p.candidates[7].bank == 67);
  assert(VenusUfsReadPlan::configure(p, read, write) && writes.empty());
  // Real Venus reset-state observations: initialize unused M-clear banks,
  // rather than rejecting non-M bits before their first configuration write.
  for (uint32_t value : {0x12520708U, 0x004a250eU, 0x34934318U, 0x20600512U,
                        0x20f06308U, 0x01b1c50eU, 0x0a1ca314U, 0x22900110U}) {
    reset(); r[0xca000/4] = value; p = plan();
    assert(!p.error && p.route.bank == 74 && p.examined == 1);
    assert(!VenusUfsReadPlan::configure(p, read, write));
    assert(read(0xca000) == 0 && read(0xc08) == 74 && read(0x82000) == 0xa9f00e0);
    reset(); r[0xca000/4] = value; p = plan();
    auto dropDisable = [&](unsigned at, uint32_t v) { if (at != 0xca000) write(at, v); };
    assert(VenusUfsReadPlan::configure(p, read, dropDisable));
    assert(read(0xc08) == 2 && read(0x1928) == 0); // Failed zero readback cannot expose DMA.
  }
  reset(); r[0xca000/4] = 0x12520708; p = plan(); r[0xca000/4] ^= 0x100000;
  assert(!VenusUfsReadPlan::configure(p, read, write)); // Non-M reset bits need not be stable.
  reset(); p = plan();
  auto ignored = [&](unsigned at, uint32_t value) { if (at != 0x1928) write(at, value); };
  assert(VenusUfsReadPlan::configure(p, read, ignored));
  assert(read(0xc08) == 2); // Failed format write must precede stream retarget.
  puts("PASS: exact Venus SID, complete-table checks, stale ownership/context rejection, width limits and old-bank preservation");
}
