// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <array>
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <utility>
#include "VenusUfsGptRead.h"
using namespace VenusUfsGptRead;
int main()
{
  std::vector<uint8_t> disk(256 * 4096);
  std::array<uint8_t, 32768> scratch;
  std::vector<std::pair<uint64_t,unsigned>> requests;
  auto put32 = [](uint8_t *p, uint32_t v) { for (unsigned i=0;i<4;++i) p[i]=uint8_t(v>>(8*i)); };
  auto put64 = [&](uint8_t *p, uint64_t v) { put32(p,uint32_t(v)); put32(p+4,uint32_t(v>>32)); };
  uint8_t *h = disk.data()+4096, *b = disk.data()+255*4096, *a = disk.data()+8192;
  auto fixHeader = [&](uint8_t *p) { put32(p+16,crc32(p,92,true)); };
  auto reset = [&] {
    std::fill(disk.begin(),disk.end(),0); requests.clear(); scratch.fill(0xa5);
    for (uint8_t *p : {h,b}) {
      memcpy(p,"EFI PART",8); put32(p+8,0x10000); put32(p+12,92);
      put64(p+40,6); put64(p+48,250); p[56]=0x42; put32(p+80,128); put32(p+84,128);
    }
    put64(h+24,1); put64(h+32,255); put64(h+72,2);
    put64(b+24,255); put64(b+32,1); put64(b+72,251);
    a[0]=1; put64(a+32,6); put64(a+40,100);
    a[128]=2; put64(a+160,101); put64(a+168,200);
    memcpy(disk.data()+251*4096,a,16384);
    for (uint8_t *p : {h,b}) { put32(p+88,crc32(a,16384)); fixHeader(p); }
  };
  unsigned failAt = 0;
  auto read = [&](uint64_t lba, unsigned blocks, uint8_t *out) {
    assert(blocks && blocks <= 4 && lba < 256 && blocks <= 256-lba);
    assert((lba==1 && blocks==1) || (lba==2 && blocks==4) || (lba>=251 && blocks==1));
    requests.emplace_back(lba,blocks);
    if (failAt && requests.size()==failAt) return false;
    memcpy(out,disk.data()+lba*4096,blocks*4096); return true;
  };
  auto run = [&] { return collect(4096,255,scratch.data(),scratch.size(),read); };
  reset(); auto r=run(); assert(!r.error && r.used==2 && r.entries==128 && r.reads==7);
  // Independent IEEE CRC32 standard check vector.
  assert(crc32(reinterpret_cast<const uint8_t *>("123456789"),9)==0xcbf43926);
  for (unsigned n=1;n<=7;++n) { reset(); failAt=n; r=run(); assert(r.error && r.reads==n); }
  failAt=0;
  for (auto mutation : {std::pair<unsigned,uint64_t>{24,2},{32,254},{40,5},{48,252},{72,0},{72,65},{80,129},{84,256}}) {
    reset(); put64(h+mutation.first,mutation.second); fixHeader(h);
    r=run(); assert(r.error && r.reads==1);
  }
  reset(); h[16]^=1; assert(run().error && requests.size()==1);
  reset(); a[0]^=1; assert(run().error && requests.size()==2);
  reset(); put64(a+160,100); put32(h+88,crc32(a,16384)); fixHeader(h);
  assert(run().error && requests.size()==2);
  reset(); b[56]^=1; fixHeader(b); assert(run().error && requests.size()==3);
  reset(); put64(b+72,250); fixHeader(b); assert(run().error && requests.size()==3);
  reset(); disk[251*4096+100]^=1; assert(run().error && requests.size()==4);
  reset(); assert(collect(512,255,scratch.data(),scratch.size(),read).error && requests.empty());
  assert(collect(4096,0xffffffffULL,scratch.data(),scratch.size(),read).error && requests.empty());
  assert(collect(4096,255,scratch.data(),32767,read).error && requests.empty());
  puts("PASS: bounded primary/backup GPT reads, independent CRC vector, capacity/geometry/entry/mirror faults and short-read failures");
}
