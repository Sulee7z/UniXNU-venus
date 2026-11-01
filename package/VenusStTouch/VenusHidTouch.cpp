// SPDX-License-Identifier: MIT
// Own Venus digitizer consumer, bound to the qualified original17 IOHIDDevice.
#include "OriginalHidDeviceABI.h"
#include "VenusStProtocol.h"
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOWorkLoop.h>
#include <IOKit/IOTimerEventSource.h>
#include <libkern/c++/OSString.h>
#include <libkern/c++/OSIterator.h>
#include <libkern/c++/OSArray.h>
#include <libkern/c++/OSKext.h>
#include <pexpert/pexpert.h>
#include <mach/kmod.h>
extern kmod_info_t g_kernel_kmod_info;
extern "C" bool venus_st_snapshot(struct vst_state *);
extern "C" void venus_st_set_sink(void (*)(void *),void *);
extern "C" void venus_st_probe(void);
extern "C" void venus_hid_static_init(void) __asm__("__GLOBAL__sub_I_VenusHidTouch.cpp");
extern "C" {
volatile uint32_t venus_st_hid_reports,venus_st_hid_ready,venus_st_hid_phase,venus_st_hid_ticks;
char venus_st_hid_registry[1024];
volatile int venus_st_hid_status=-1,venus_st_hid_meta_status=-1,venus_st_hid_start_status=-1,venus_st_hid_report_status=-1,venus_st_hid_match_status=-1;
}
static const uint8_t keyboardDescriptor[]={
 0x05,0x01,0x09,0x06,0xa1,0x01,0x85,0x01,
 0x05,0x07,0x19,0xe0,0x29,0xe7,0x15,0x00,0x25,0x01,
 0x75,0x01,0x95,0x08,0x81,0x02,
 0x75,0x08,0x95,0x01,0x81,0x03,
 0x19,0x00,0x29,0x65,0x15,0x00,0x25,0x65,
 0x75,0x08,0x95,0x06,0x81,0x00,
 0x85,0x02,0x05,0x0c,0x09,0x40,0x09,0x30,0x09,0xe9,0x09,0xea,0x15,0x00,0x25,0x01,
 0x75,0x01,0x95,0x04,0x81,0x02,
 0x75,0x04,0x95,0x01,0x81,0x03,0xc0
};
#define VST_FINGER \
 0x09,0x22,0xa1,0x02,0x09,0x42,0x15,0,0x25,1,0x75,1,0x95,1,0x81,2,0x09,0x47,0x81,2,0x75,6,0x95,1,0x81,3, \
 0x09,0x51,0x75,8,0x95,1,0x15,0,0x26,0xff,0,0x81,2,0x05,1,0x09,0x30,0x15,0,0x26,0xff,0x7f,0x75,0x10,0x95,1,0x81,2,0x09,0x31,0x81,2,0x05,0x0d,0xc0,
static const uint8_t descriptor[]={0x05,0x0d,0x09,4,0xa1,1,0x85,3,
 VST_FINGER VST_FINGER VST_FINGER VST_FINGER VST_FINGER
 VST_FINGER VST_FINGER VST_FINGER VST_FINGER VST_FINGER
 0x09,0x54,0x75,8,0x95,1,0x15,0,0x25,10,0x81,2,0xc0};
// iPadOS17's IOHIDEventDriver never sets kIOHIDDigitizerEventFromEdgeTip.
// SpringBoard/UIKit edge gestures (including the lock-screen swipe-up) then
// see edge type 0 and ignore the gesture, while ordinary taps still work.
// The reference ShengHidInput driver adds the bit in a copy of the event
// driver's dispatch vtable. The event ABI is the same iPadOS17/21H461 ABI
// used here.
namespace edge {
enum {kSlots=256,kDispatch=198,kGetType=18,kGetInteger=23,kSetInteger=24,kGetFixed=25,kContacts=256};
enum : uint32_t {kDigitizer=11,kX=0xB0000,kY=0xB0001,kIndex=0xB0005,kMask=0xB0007,kTouch=0xB0009,kMaskTouch=2,kFromEdgeTip=0x800};
// 48 panel pixels on the 1440x3200 Venus panel, in IOFixed 16.16 coordinates.
static const int32_t kEdgeX=48*65536/1440,kEdgeY=48*65536/3200;
static uintptr_t originalDispatch;
static bool fromEdge[kContacts];
template <typename R,typename... A> static R call(void *object,unsigned slot,A... args) {
    return reinterpret_cast<R (*)(void *,A...)>((*reinterpret_cast<uintptr_t **>(object))[slot])(object,args...);
}
static bool mark(void *child) {
    if(call<uint32_t,IOOptionBits>(child,kGetType,0)!=kDigitizer)return false;
    const uint32_t index=(uint32_t)call<int32_t,uint32_t,IOOptionBits>(child,kGetInteger,kIndex,0);
    if(index>=kContacts)return false;
    const uint32_t mask=(uint32_t)call<int32_t,uint32_t,IOOptionBits>(child,kGetInteger,kMask,0);
    const bool touch=call<int32_t,uint32_t,IOOptionBits>(child,kGetInteger,kTouch,0)!=0;
    if((mask&kMaskTouch) && touch) {
        const int32_t x=call<int32_t,uint32_t,IOOptionBits>(child,kGetFixed,kX,0),y=call<int32_t,uint32_t,IOOptionBits>(child,kGetFixed,kY,0);
        fromEdge[index]=x<kEdgeX || x>65536-kEdgeX || y<kEdgeY || y>65536-kEdgeY;
    }
    const bool edged=fromEdge[index];
    if(edged)call<void,uint32_t,int32_t,IOOptionBits>(child,kSetInteger,kMask,(int32_t)(mask|kFromEdgeTip),0);
    if(!touch && (mask&kMaskTouch))fromEdge[index]=false;
    return edged;
}
static void dispatch(IOService *self,OSObject *event,IOOptionBits options) {
    if(event && call<uint32_t,IOOptionBits>(event,kGetType,0)==kDigitizer) {
        OSArray *children=*reinterpret_cast<OSArray **>(reinterpret_cast<uint8_t *>(event)+24);
        if(children && OSDynamicCast(OSArray,children) && children->getCount()) {
            bool any=false;
            for(unsigned i=0;i<children->getCount();++i) {
                OSObject *child=children->getObject(i);
                if(child && child->metaCast("IOHIDEvent"))any|=mark(child);
            }
            if(any) {
                const uint32_t mask=(uint32_t)call<int32_t,uint32_t,IOOptionBits>(event,kGetInteger,kMask,0);
                call<void,uint32_t,int32_t,IOOptionBits>(event,kSetInteger,kMask,(int32_t)(mask|kFromEdgeTip),0);
            }
        } else if(!children) mark(event);
    }
    reinterpret_cast<void (*)(IOService *,OSObject *,IOOptionBits)>(originalDispatch)(self,event,options);
}
static void install(IORegistryEntry *driver) {
    if(originalDispatch || !driver)return;
    uintptr_t *table=*reinterpret_cast<uintptr_t **>(driver);
    uintptr_t *copy=static_cast<uintptr_t *>(IOMalloc(kSlots*sizeof(uintptr_t)));
    if(!copy)return;
    memcpy(copy,table,kSlots*sizeof(uintptr_t));
    originalDispatch=copy[kDispatch];copy[kDispatch]=(uintptr_t)&dispatch;
    __asm__ volatile("dmb ish":::"memory");
    *reinterpret_cast<uintptr_t **>(driver)=copy;
}
}
class VenusHidTouch : public IOHIDDevice {
    OSDeclareDefaultStructors(VenusHidTouch)
    IOWorkLoop *loop=nullptr;IOTimerEventSource *timer=nullptr;IOLock *lifecycle=nullptr;
    struct vst_hid_state previous={};uint32_t sequence=0;bool ready=false,stopping=false;
    static void describe(IORegistryEntry *parent,unsigned depth,size_t &used) {
        if(depth>4 || used>sizeof(venus_st_hid_registry)-128)return;
        int n=snprintf(venus_st_hid_registry+used,sizeof(venus_st_hid_registry)-used,"%u:%s[%s];",depth,parent->getName(),parent->getMetaClass()->getClassName());
        if(n<=0 || static_cast<size_t>(n)>=sizeof(venus_st_hid_registry)-used)return;used+=n;
        OSIterator *it=parent->getChildIterator(gIOServicePlane);if(!it)return;
        while(OSObject *object=it->getNextObject())if(IORegistryEntry *entry=OSDynamicCast(IORegistryEntry,object))describe(entry,depth+1,used);
        it->release();
    }
    static IORegistryEntry *eventDriver(IORegistryEntry *parent,unsigned depth) {
        if(!depth)return nullptr;OSIterator *it=parent->getChildIterator(gIOServicePlane);if(!it)return nullptr;
        IORegistryEntry *found=nullptr;
        while(OSObject *object=it->getNextObject()) {
            IORegistryEntry *entry=OSDynamicCast(IORegistryEntry,object);if(!entry)continue;
            if(entry->metaCast("IOHIDEventDriver")){found=entry;break;}
            if((found=eventDriver(entry,depth-1)))break;
        }
        it->release();return found;
    }
    void prepare() {
        if(ready)return;
        size_t used=0;describe(this,0,used);
        IORegistryEntry *driver=eventDriver(this,4);if(!driver)return;
        for(IORegistryEntry *entry=driver;entry;entry=entry==driver?driver->getParentEntry(gIOServicePlane):nullptr) {
            entry->setProperty("Built-In",kOSBooleanTrue);entry->setProperty("DisplayIntegrated",kOSBooleanTrue);
            entry->setProperty("PrimaryUsagePage",(unsigned long long)0x0d,32);entry->setProperty("PrimaryUsage",(unsigned long long)4,32);
        }
        edge::install(driver);
        ready=true;venus_st_hid_ready=1;venus_st_hid_phase=6;
    }
    void send() {
        if(__atomic_load_n(&stopping,__ATOMIC_ACQUIRE))return;prepare();if(!ready)return;
        struct vst_state snapshot;if(!venus_st_snapshot(&snapshot) || snapshot.sequence==sequence)return;
        uint8_t report[62];struct vst_hid_state next;
        if(vst_hid_report(&snapshot,&previous,report,&next))return;
        IOBufferMemoryDescriptor *buffer=IOBufferMemoryDescriptor::withBytes(report,sizeof report,kIODirectionNone);
        venus_st_hid_report_status=buffer?handleReport(buffer,0,0):kIOReturnNoMemory;OSSafeReleaseNULL(buffer);
        venus_st_hid_status=venus_st_hid_report_status;
        if(!venus_st_hid_status){previous=next;sequence=snapshot.sequence;venus_st_hid_reports=venus_st_hid_reports+1;venus_st_hid_phase=7;}
    }
    static IOReturn action(OSObject *owner,void *,void *,void *,void *) {VenusHidTouch *self=OSDynamicCast(VenusHidTouch,owner);if(self)self->send();return kIOReturnSuccess;}
    static void notify(void *context) {
        VenusHidTouch *self=static_cast<VenusHidTouch *>(context);if(!self || !self->lifecycle)return;
        IOLockLock(self->lifecycle);IOWorkLoop *loop=__atomic_load_n(&self->stopping,__ATOMIC_ACQUIRE)?nullptr:self->loop;if(loop)loop->retain();IOLockUnlock(self->lifecycle);
        if(loop){loop->runAction(action,self);loop->release();}
    }
    static void tick(OSObject *owner,IOTimerEventSource *source) {VenusHidTouch *self=OSDynamicCast(VenusHidTouch,owner);if(self){venus_st_hid_ticks=venus_st_hid_ticks+1;self->send();if(!__atomic_load_n(&self->stopping,__ATOMIC_ACQUIRE))source->setTimeoutMS(100);}}
public:
    IOWorkLoop *getWorkLoop() const override {return loop;}
    OSString *newTransportString() const override {return OSString::withCString("SPI");}
    OSString *newProductString() const override {return OSString::withCString("Venus ST Touch Screen");}
    IOReturn newReportDescriptor(IOMemoryDescriptor **out) const override {
        if(!out)return kIOReturnBadArgument;
        unsigned char combined[sizeof keyboardDescriptor+sizeof descriptor];
        memcpy(combined,keyboardDescriptor,sizeof keyboardDescriptor);
        memcpy(combined+sizeof keyboardDescriptor,descriptor,sizeof descriptor);
        *out=IOBufferMemoryDescriptor::withBytes(combined,sizeof combined,kIODirectionNone);
        return *out?kIOReturnSuccess:kIOReturnNoMemory;
    }
    bool start(IOService *provider) override {
        lifecycle=IOLockAlloc();loop=lifecycle?IOWorkLoop::workLoop():nullptr;
        if(!loop)return false;
        // Original17 generic event-driver matching uses HIDDefaultBehavior.
        // Provide our workloop before the original base starts its interface.
        if(!setProperty("HIDDefaultBehavior",true))return false;
        setProperty("DigitizerCollectionDispatch",true);
        setProperty("Built-In",kOSBooleanTrue);setProperty("DisplayIntegrated",kOSBooleanTrue);
        setProperty("VendorID",(unsigned long long)0x0483,32);setProperty("ProductID",(unsigned long long)0x3936,32);
        if(!IOHIDDevice::start(provider))return false;
        timer=IOTimerEventSource::timerEventSource(this,tick);
        if(!loop || !timer || loop->addEventSource(timer)!=kIOReturnSuccess){OSSafeReleaseNULL(timer);OSSafeReleaseNULL(loop);IOHIDDevice::stop(provider);return false;}
        registerService();venus_st_set_sink(notify,this);timer->setTimeoutMS(100);return true;
    }
    void stop(IOService *provider) override {
        if(lifecycle)IOLockLock(lifecycle);__atomic_store_n(&stopping,true,__ATOMIC_RELEASE);if(lifecycle)IOLockUnlock(lifecycle);
        venus_st_set_sink(nullptr,nullptr);
        if(timer){timer->cancelTimeout();if(loop)loop->removeEventSource(timer);}
        OSSafeReleaseNULL(timer);IOHIDDevice::stop(provider);
    }
    void free() override {OSSafeReleaseNULL(timer);OSSafeReleaseNULL(loop);if(lifecycle)IOLockFree(lifecycle);lifecycle=nullptr;IOHIDDevice::free();}
};
OSDefineMetaClassAndStructors(VenusHidTouch,IOHIDDevice)
extern "C" void venus_st_hid_start(IOService *resource) {
    static bool attempted;if(attempted)return;
    unsigned mode=0;PE_parse_boot_argn("venus-st-touch",&mode,sizeof mode);if(!mode || mode>3 || !resource)return;
    attempted=true;venus_st_probe();if(mode<3)return;
    venus_st_hid_phase=1;
    // Mainline uses the regular IOHIDEventDriver with a combined keyboard +
    // digitizer descriptor; the event driver then owns the edge vtable.
    venus_st_hid_match_status=OSKext::loadKextWithIdentifier("com.apple.iokit.IOHIDEventDriver",
        true,false,kOSKextExcludeNone,kOSKextExcludeNone,nullptr);
    if(venus_st_hid_match_status){venus_st_hid_status=venus_st_hid_match_status;return;}
    void *handle=OSMetaClass::preModLoad(g_kernel_kmod_info.name);if(!handle){venus_st_hid_status=kIOReturnError;return;}
    venus_hid_static_init();venus_st_hid_meta_status=OSMetaClass::postModLoad(handle);venus_st_hid_status=venus_st_hid_meta_status;if(venus_st_hid_status)return;
    venus_st_hid_phase=2;
    VenusHidTouch *device=new VenusHidTouch;bool attached=false;
    if(device && device->init()){venus_st_hid_phase=3;attached=device->attach(resource);}
    if(attached)venus_st_hid_phase=4;
    const bool started=attached && device->start(resource);
    venus_st_hid_start_status=started?0:kIOReturnError;venus_st_hid_status=venus_st_hid_start_status;
    if(started)venus_st_hid_phase=5;
    else {if(attached)device->detach(resource);OSSafeReleaseNULL(device);}
}
