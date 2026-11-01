// SPDX-License-Identifier: MIT
// Source-extracted start/publication tail, real overlay and first-reader cache.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include "DirectDisk.h"
static unsigned requestedMode=2,native_ram_block_ready=0;
static unsigned native_data_persist_state=0,native_data_persist_gpt=0,native_data_persist_gpt_after=0;
static unsigned native_ufs_store_mode(){return requestedMode;}
static void IOLog(const char *,unsigned){}
struct Disk;
static Disk *deferredData=nullptr;
static bool systemosDone=false;
struct Medium {
    std::vector<uint8_t> bytes;bool fail=false;unsigned reads=0;
    Medium():bytes(persist::windowBlocks(16)*4096){}
    bool read(uint64_t b,uint32_t n,void *p){++reads;if(fail)return false;assert((b+n)*4096<=bytes.size());memcpy(p,bytes.data()+b*4096,n*4096);return true;}
    bool write(uint64_t b,uint32_t n,const void *p){assert((b+n)*4096<=bytes.size());memcpy(bytes.data()+b*4096,p,n*4096);return true;}
    bool sync(){return true;}
};
struct Disk {
    Medium &medium;RamSparseDisk seed={};std::vector<uint8_t*> pages;
    std::vector<uint8_t> bits,stage;persist::Overlay overlay;
    uint8_t digest[32]={7};bool online=false,direct=false,isBig=true,published=false;
    uint64_t cached=0;unsigned attachments=0;
    Disk(Medium &m):medium(m),pages(16,nullptr),bits(4096),stage(4096){seed.bytes=16*4096;seed.pages=pages.data();native_ram_block_ready=0;}
    ~Disk(){if(deferredData==this)deferredData=nullptr;}
    void attachStore(){
        assert(systemosDone);++attachments;auto opened=overlay.open(medium,16,digest,false,bits.data());
        if(opened==persist::Open::Failed){native_data_persist_state=4;return;}
        direct=true;native_data_persist_state=opened==persist::Open::Resumed?2:3;
    }
    void registerService(){
        assert(online);published=true;if(!direct)return;assert(systemosDone);
        struct Buffer {
            uint64_t *result;
            uint64_t copy(uint64_t at,const void*p,uint64_t n){assert(at==0&&n==8);memcpy(result,p,n);return n;}
            uint64_t read(uint64_t,void*,uint64_t){assert(false);return 0;}
        } buffer{&cached};bool error=false;
        assert(directDiskIO(seed,overlay,medium,stage.data(),1,false,0,8,buffer,&error)==8&&!error);
    }
    bool start(){
#include "deferred-start.inc"
    }
    bool publishForData(){
#include "deferred-publish.inc"
    }
};
int main(){
    Medium m;uint8_t digest[32]={7},bits[4096]={},page[4096]={};persist::Overlay initial;
    assert(initial.open(m,16,digest,false,bits)==persist::Open::Fresh);
    const uint64_t checkpoint=42;memcpy(page,&checkpoint,8);assert(initial.writePage(m,0,page));
    unsigned reads=m.reads;Disk data(m);assert(data.start());
    assert(!data.online&&!data.published&&!data.attachments&&m.reads==reads&&deferredData==&data);
    // SystemOS stage sees no Data publication or persistent Data transport.
    Disk duplicate(m);assert(!duplicate.start()&&deferredData==&data);
    systemosDone=true;assert(data.publishForData());
    assert(data.published&&data.cached==42&&data.attachments==1&&deferredData==nullptr);
    assert(data.publishForData()&&data.attachments==1);
    systemosDone=false;Disk next(m);assert(next.start()&&!next.published);
    systemosDone=true;assert(next.publishForData()&&next.cached==42);
    m.fail=true;Disk failed(m);assert(failed.start()&&!failed.published);
    assert(!failed.publishForData()&&!failed.published&&!failed.online&&!native_ram_block_ready);
    deferredData=nullptr;m.fail=false;requestedMode=0;systemosDone=false;
    Disk off(m);assert(off.start()&&off.published&&!off.attachments&&deferredData==nullptr);
    requestedMode=1;Disk unsupported(m);assert(!unsupported.start()&&!unsupported.published);
    puts("PASS: no Data discovery/I-O before SystemOS stage; restored first read/next boot match; idempotent publication; duplicate/failure/mode0/big-read-only controls");
}
