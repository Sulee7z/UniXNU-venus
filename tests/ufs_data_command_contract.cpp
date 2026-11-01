// SPDX-License-Identifier: BSD-2-Clause-Patent
// Production commands + exact Venus store callbacks + overlay. Hardware/DMA and
// durable/cache media are modeled; no APFS namespace or real device is tested.
#include "tests/RootCommandsBridge.cpp"
#include "PersistOverlay.h"
#include <array>
#include <map>
#include <algorithm>
constexpr uint64_t storeFirst=59299519, pages=2097152;
static uint64_t gStoreRegionFirst=storeFirst,gStoreRegionBlocks=persist::windowBlocks(pages);
static unsigned storeMode(){return 2;}
#include "store-callbacks.inc"
using Page=std::array<uint8_t,4096>;
static std::map<uint64_t,Page> durable,cached;
static std::array<uint8_t,kDmaBytes> dma;
static std::array<uint32_t,64> regs;
static uint64_t clockUs;
static unsigned fuaWrites,flushes,ringCount;
static bool failScsi,timeoutCommand,failFua;
static uint64_t hardware(unsigned op,uint64_t address,uint64_t value,void *bytes){
    if(op==0)return regs.at(address/4);
    if(op==2||op==3){
        assert(address>=gHost.phys&&address-gHost.phys+value<=dma.size());
        auto *at=dma.data()+address-gHost.phys;
        if(op==2)memcpy(at,bytes,value);else memcpy(bytes,at,value);
    }
    if(op==4)return clockUs;
    if(op==5)clockUs+=value;
    if(op!=1)return 0;
    if(address==0x20){regs[0x20/4]&=~uint32_t(value);return 0;}
    regs.at(address/4)=uint32_t(value);
    if(address!=0x58)return 0;
    ++ringCount;if(timeoutCommand)return 0;
    const uint8_t *cmd=dma.data()+kUcdOffset;const uint8_t *cdb=cmd+16;
    assert(cmd[0]==1&&cmd[2]==0);
    const uint64_t lba=loadBe32(cdb+2);const unsigned count=(unsigned(cdb[7])<<8)|cdb[8];
    const unsigned transfer=loadBe32(cmd+12);
    bool failure=failScsi||(failFua&&cdb[0]==0x2a&&(cdb[1]&8));
    if(!failure&&cdb[0]==0x2a){
        assert(cmd[1]==0x20&&transfer==count*4096&&lba>=storeFirst&&lba+count<=storeFirst+gStoreRegionBlocks);
        assert((*reinterpret_cast<uint32_t*>(dma.data())>>25&3)==1);
        const bool fua=(cdb[1]&8)!=0;
        for(unsigned i=0;i<count;i++){
            Page p;memcpy(p.data(),dma.data()+kDataOffset+i*4096,4096);
            (fua?durable:cached)[lba+i]=p;
        }
        if(fua)++fuaWrites;
    }else if(!failure&&cdb[0]==0x28){
        assert(cmd[1]==0x40&&transfer==count*4096);
        for(unsigned i=0;i<count;i++){
            auto cache=cached.find(lba+i),saved=durable.find(lba+i);
            if(cache!=cached.end())memcpy(dma.data()+kDataOffset+i*4096,cache->second.data(),4096);
            else if(saved!=durable.end())memcpy(dma.data()+kDataOffset+i*4096,saved->second.data(),4096);
            else memset(dma.data()+kDataOffset+i*4096,0xff,4096);
        }
    }else if(!failure&&cdb[0]==0x35){
        assert(cmd[1]==0&&transfer==0);
        for(unsigned i=1;i<10;i++)assert(cdb[i]==0);
        for(const auto &entry:cached)durable[entry.first]=entry.second;
        cached.clear();++flushes;
    }
    uint8_t *rsp=dma.data()+kUcdOffset+kRspOffset;
    memset(rsp,0,512);rsp[0]=0x21;rsp[2]=0;rsp[3]=0;rsp[7]=failure?2:0;
    *reinterpret_cast<uint32_t*>(dma.data()+8)=0;
    regs[0x58/4]=0;regs[0x20/4]=1;
    return 0;
}
static void resetTransport(){
    dma.fill(0);regs.fill(0);clockUs=0;failScsi=timeoutCommand=failFua=false;
    ufs_test_reset(hardware,0x8cb5e9000);assert(ufs_test_store_open(storeFirst,gStoreRegionBlocks));
}
struct Ops{
    bool read(uint64_t b,uint32_t n,void*p){return native_ufs_store_read(b,n,p);}
    bool write(uint64_t b,uint32_t n,const void*p){return native_ufs_store_write(b,n,p);}
    bool sync(){return native_ufs_store_sync();}
};
int main(){
    resetTransport();Page marker;marker.fill(0x4b);const auto original=marker;
    const unsigned before=ringCount;
    assert(!native_ufs_store_write(gStoreRegionBlocks,1,marker.data())&&ringCount==before);
    assert(!native_ufs_store_write(gStoreRegionBlocks-1,2,marker.data())&&ringCount==before);
    assert(native_ufs_store_write(100,1,marker.data())&&fuaWrites==1&&cached.empty());
    cached.clear();resetTransport();Page read;
    assert(native_ufs_store_read(100,1,read.data())&&read==original);
    // An ordinary non-FUA write is only cached; the real SYNCHRONIZE CACHE
    // command persists it. This checks the sync path separately from FUA.
    assert(hostWrite4k(0,storeFirst+101,1,marker.data(),false)==0&&cached.size()==1);
    assert(native_ufs_store_sync()&&flushes==1&&cached.empty());
    resetTransport();assert(native_ufs_store_read(101,1,read.data())&&read==original);
    // Real persistent header/bitmap/page ordering through real store callbacks.
    Ops ops;std::array<uint8_t,64*4096> bits;uint8_t digest[32]={7};persist::Overlay overlay;
    assert(overlay.open(ops,pages,digest,false,bits.data())==persist::Open::Fresh);
    assert(overlay.writePage(ops,123,marker.data()));
    resetTransport();std::array<uint8_t,64*4096> bits2;persist::Overlay reopened;
    assert(reopened.open(ops,pages,digest,false,bits2.data())==persist::Open::Resumed&&reopened.has(123));
    assert(native_ufs_store_read(persist::pageBlock(pages,123),1,read.data())&&read==marker);
    resetTransport();failFua=true;
    assert(!native_ufs_store_write(102,1,marker.data())&&durable.find(storeFirst+102)==durable.end());
    resetTransport();failScsi=true;assert(!native_ufs_store_sync());
    resetTransport();timeoutCommand=true;assert(!native_ufs_store_write(103,1,marker.data())&&ufs_test_poisoned());
    const auto quarantinedRing=ringCount;
    assert(!native_ufs_store_write(104,1,marker.data())&&ringCount==quarantinedRing);
    puts("PASS: exact store callbacks, successful WRITE10 FUA/UPIU/UTRD, SYNCHRONIZE CACHE10, overlay header/bitmap/page reopen, window bounds, SCSI failures and timeout quarantine");
}
