// SPDX-License-Identifier: MIT
// Exercises the source-extracted NativeRamBlock publication tail with the real
// overlay/direct I/O cores. A caching consumer models early discovery, not APFS.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include "DirectDisk.h"
static unsigned requestedMode=2, native_ram_block_ready=0;
static unsigned native_data_persist_state=0,native_data_persist_gpt=0,native_data_persist_gpt_after=0;
static unsigned native_ufs_store_mode() {return requestedMode;}
static void IOLog(const char *,unsigned) {}
struct Medium {
  std::vector<uint8_t> bytes;
  bool fail=false;
  explicit Medium(uint64_t pages):bytes(persist::windowBlocks(pages)*4096){}
  bool read(uint64_t b,uint32_t n,void *p) {
    if(fail)return false;assert((b+n)*4096<=bytes.size());memcpy(p,bytes.data()+b*4096,n*4096);return true;
  }
  bool write(uint64_t b,uint32_t n,const void *p) {
    assert((b+n)*4096<=bytes.size());memcpy(bytes.data()+b*4096,p,n*4096);return true;
  }
  bool sync(){return true;}
};
struct Disk {
  static constexpr uint64_t pages=16;
  Medium &medium;
  RamSparseDisk seed={};
  std::vector<uint8_t *> seedPages;
  std::vector<uint8_t> bits,stage;
  uint8_t seedHash[32]={7};
  persist::Overlay overlay;
  bool direct=false,online=false,isBig=true,published=false;
  unsigned attachments=0;
  uint64_t cachedCheckpoint=0;
  explicit Disk(Medium &m):medium(m),seedPages(pages,nullptr),bits(4096),stage(4096) {
    seed.bytes=pages*4096;seed.pages=seedPages.data();
    native_ram_block_ready=0;native_data_persist_state=0;
    native_data_persist_gpt=0;native_data_persist_gpt_after=0;
  }
  void attachStore() {
    ++attachments;
    auto result=overlay.open(medium,pages,seedHash,false,bits.data());
    if(result==persist::Open::Failed){native_data_persist_state=4;return;}
    direct=true;native_data_persist_state=result==persist::Open::Resumed?2:3;
  }
  uint64_t readCheckpoint() {
    uint64_t value=0;
    if(!direct)return value; // immutable seed has checkpoint 0
    struct Buffer {
      uint64_t *value;
      uint64_t copy(uint64_t at,const void *p,uint64_t n){assert(at==0&&n==8);memcpy(value,p,n);return n;}
      uint64_t read(uint64_t,void *,uint64_t){assert(false);return 0;}
    } buffer{&value};
    bool error=false;
    assert(directDiskIO(seed,overlay,medium,stage.data(),1,false,0,8,buffer,&error)==8&&!error);
    return value;
  }
  void registerService() {assert(online);published=true;cachedCheckpoint=readCheckpoint();}
  bool oldPublication() {
#include "publication-before.inc"
  }
  bool newPublication() {
#include "publication-after.inc"
  }
};
int main() {
  Medium medium(Disk::pages);
  uint8_t digest[32]={7},bits[4096]={},page[4096]={};persist::Overlay initial;
  assert(initial.open(medium,Disk::pages,digest,false,bits)==persist::Open::Fresh);
  const uint64_t latestCheckpoint=42;memcpy(page,&latestCheckpoint,8);
  assert(initial.writePage(medium,0,page));
  Disk old(medium);assert(old.oldPublication());old.attachStore();
  assert(old.cachedCheckpoint==0&&old.readCheckpoint()==42); // old cached/actual views disagree
  Disk fixed(medium);assert(fixed.newPublication());
  assert(fixed.cachedCheckpoint==42&&fixed.readCheckpoint()==42&&fixed.attachments==1);
  Disk nextBoot(medium);assert(nextBoot.newPublication()&&nextBoot.cachedCheckpoint==42);
  medium.fail=true;Disk failed(medium);assert(!failed.newPublication()&&!failed.published&&!native_ram_block_ready);
  medium.fail=false;requestedMode=0;Disk disabled(medium);
  assert(disabled.newPublication()&&disabled.cachedCheckpoint==0&&!disabled.attachments);
  requestedMode=1;Disk unsupported(medium);
  assert(!unsupported.newPublication()&&!unsupported.published&&!unsupported.attachments);
  puts("PASS: old publication caches seed checkpoint; restored publication sees durable checkpoint on first read and next boot; failures never publish, mode0 preserved, unsupported big read-only refused");
}
