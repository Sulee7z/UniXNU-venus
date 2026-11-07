// SPDX-License-Identifier: BSD-2-Clause-Patent
// Previous Venus STM producer/report protocol, bound to the actual25F84 HID ABI.
#include "VenusStProtocol.h"
#include "Touch061Projection.h"
#include <IOKit/IOService.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <IOKit/IOWorkLoop.h>
#include <IOKit/IOTimerEventSource.h>
#include <libkern/c++/OSArray.h>
#include <libkern/c++/OSDictionary.h>
#include <libkern/c++/OSIterator.h>
#include <libkern/c++/OSString.h>
#include <pexpert/pexpert.h>
#include <string.h>

extern "C" uintptr_t native_kext_symbol(const char *,const char *);
extern "C" void venus_st_probe(void);
extern "C" bool venus_st_snapshot(struct vst_state *);
extern "C" void native_touch_set_sink(void (*)(void *),void *);
extern "C" {
extern volatile uint32_t venus_st_stage,venus_st_frames,venus_st_errors,venus_st_chip_id,venus_st_messages;
extern volatile uint32_t venus_st_firmware_version,native_touch_hid_reports;
extern volatile int venus_st_status;
volatile uint32_t venus_touch061_stage,venus_touch061_reports,venus_touch061_edge_events;
volatile int venus_touch061_status=-1;
}

namespace {
const char kFamily[]="com.apple.iokit.IOHIDFamily";
constexpr unsigned kDeviceSlots=334,kWorkLoop=215,kTransport=275,kProduct=277,kDescriptor=284,kReport=285;
constexpr unsigned kDriverSlots=359,kDispatch=302,kType=42,kInteger=47,kSetInteger=48,kFixed=49;
enum : uint32_t {kDigitizer=11,kX=0xb0000,kY=0xb0001,kIndex=0xb0005,kMask=0xb0007,kTouch=0xb0009,kTouchMask=2,kFromEdge=0x800};
const uint8_t kKeyboard[]={
 0x05,0x01,0x09,0x06,0xa1,0x01,0x85,0x01,
 0x05,0x07,0x19,0xe0,0x29,0xe7,0x15,0x00,0x25,0x01,0x75,0x01,0x95,0x08,0x81,0x02,
 0x75,0x08,0x95,0x01,0x81,0x03,0x19,0x00,0x29,0x65,0x15,0x00,0x25,0x65,0x75,0x08,0x95,0x06,0x81,0x00,
 0x85,0x02,0x05,0x0c,0x09,0x40,0x09,0x30,0x09,0xe9,0x09,0xea,0x15,0x00,0x25,0x01,
 0x75,0x01,0x95,0x04,0x81,0x02,0x75,0x04,0x95,0x01,0x81,0x03,0xc0
};
#define VST061_FINGER \
 0x09,0x22,0xa1,0x02,0x09,0x42,0x15,0,0x25,1,0x75,1,0x95,1,0x81,2,0x09,0x47,0x81,2,0x75,6,0x95,1,0x81,3, \
 0x09,0x51,0x75,8,0x95,1,0x15,0,0x26,0xff,0,0x81,2,0x05,1,0x09,0x30,0x15,0,0x26,0xff,0x7f,0x75,0x10,0x95,1,0x81,2,0x09,0x31,0x81,2,0x05,0x0d,0xc0,
const uint8_t kTouchDescriptor[]={0x05,0x0d,0x09,4,0xa1,1,0x85,3,
 VST061_FINGER VST061_FINGER VST061_FINGER VST061_FINGER VST061_FINGER
 VST061_FINGER VST061_FINGER VST061_FINGER VST061_FINGER VST061_FINGER
 0x09,0x54,0x75,8,0x95,1,0x15,0,0x25,10,0x81,2,0xc0};

uintptr_t deviceTable[2+kDeviceSlots+1],originalDevice[kDeviceSlots];
uintptr_t *edgeTable;
uintptr_t originalDispatch;
using Children=OSArray *(*)(OSObject *);
Children getChildren;
bool fromEdge[256];
IOWorkLoop *touchLoop;
IOTimerEventSource *touchTimer;
IOService *touchDevice;
IORegistryEntry *touchDriver;
struct vst_hid_state previous={};
uint32_t sequence,attempted,lastHardwareStage=~0u,lastContactCount=~0u,ticks;
int lastHardwareStatus=0x7fffffff;

template<typename R,typename... A> R eventCall(void *object,unsigned slot,A... args) {
    return reinterpret_cast<R (*)(void *,A...)>((*reinterpret_cast<uintptr_t **>(object))[slot])(object,args...);
}

bool markFinger(OSObject *event) {
    if(eventCall<uint32_t>(event,kType)!=kDigitizer)return false;
    const uint32_t id=(uint32_t)eventCall<int32_t,uint32_t,IOOptionBits>(event,kInteger,kIndex,0);
    if(id>=256)return false;
    const uint32_t mask=(uint32_t)eventCall<int32_t,uint32_t,IOOptionBits>(event,kInteger,kMask,0);
    const bool touching=eventCall<int32_t,uint32_t,IOOptionBits>(event,kInteger,kTouch,0)!=0;
    if((mask&kTouchMask)&&touching) {
        const int32_t x=eventCall<int32_t,uint32_t,IOOptionBits>(event,kFixed,kX,0);
        const int32_t y=eventCall<int32_t,uint32_t,IOOptionBits>(event,kFixed,kY,0);
        __atomic_store_n(&fromEdge[id],vst061_at_edge(x,y),__ATOMIC_RELAXED);
    }
    bool edge=__atomic_load_n(&fromEdge[id],__ATOMIC_RELAXED);
    if(edge)eventCall<void,uint32_t,int32_t,IOOptionBits>(event,kSetInteger,kMask,(int32_t)(mask|kFromEdge),0);
    if(!touching&&(mask&kTouchMask))__atomic_store_n(&fromEdge[id],false,__ATOMIC_RELAXED);
    return edge;
}

void dispatch(IOService *self,OSObject *event,IOOptionBits options) {
    if(event&&event->metaCast("IOHIDEvent")&&eventCall<uint32_t>(event,kType)==kDigitizer) {
        OSArray *children=getChildren(event);
        bool edge=false;
        if(children&&OSDynamicCast(OSArray,children)&&children->getCount()) {
            for(unsigned i=0;i<children->getCount();++i) {
                OSObject *child=children->getObject(i);
                if(child&&child->metaCast("IOHIDEvent"))edge|=markFinger(child);
            }
            if(edge) {
                const uint32_t mask=(uint32_t)eventCall<int32_t,uint32_t,IOOptionBits>(event,kInteger,kMask,0);
                eventCall<void,uint32_t,int32_t,IOOptionBits>(event,kSetInteger,kMask,(int32_t)(mask|kFromEdge),0);
            }
        } else edge=markFinger(event);
        if(edge)__atomic_fetch_add(&venus_touch061_edge_events,1,__ATOMIC_RELAXED);
    }
    reinterpret_cast<void (*)(IOService *,OSObject *,IOOptionBits)>(originalDispatch)(self,event,options);
}

IORegistryEntry *findDriver(IORegistryEntry *parent,unsigned depth) {
    if(!parent||!depth)return nullptr;
    OSIterator *iterator=parent->getChildIterator(gIOServicePlane);if(!iterator)return nullptr;
    IORegistryEntry *found=nullptr;
    while(OSObject *object=iterator->getNextObject()) {
        IORegistryEntry *entry=OSDynamicCast(IORegistryEntry,object);if(!entry)continue;
        if(entry->metaCast("IOHIDEventDriver")){found=entry;found->retain();break;}
        if((found=findDriver(entry,depth-1)))break;
    }
    iterator->release();return found;
}

bool prepareDriver() {
    if(touchDriver)return true;
    IORegistryEntry *driver=findDriver(touchDevice,4);if(!driver)return false;
    uintptr_t *table=*reinterpret_cast<uintptr_t **>(driver);
    uintptr_t target=native_kext_symbol(kFamily,"__ZN16IOHIDEventDriver13dispatchEventEP10IOHIDEventj");
    getChildren=reinterpret_cast<Children>(native_kext_symbol(kFamily,"__ZN10IOHIDEvent11getChildrenEv"));
    if(!target||!getChildren||table[kDriverSlots]!=0||!table[kDriverSlots-1]||table[kDispatch]!=target) {
        venus_touch061_status=kIOReturnUnsupported;driver->release();return false;
    }
    bool properties=true;
    for(IORegistryEntry *entry=driver;entry;entry=entry==driver?driver->getParentEntry(gIOServicePlane):nullptr) {
        properties=properties&&entry->setProperty("Built-In",kOSBooleanTrue)&&entry->setProperty("DisplayIntegrated",kOSBooleanTrue)&&
            entry->setProperty("PrimaryUsagePage",(unsigned long long)0x0d,32)&&entry->setProperty("PrimaryUsage",(unsigned long long)4,32);
    }
    if(!properties){venus_touch061_status=kIOReturnNoMemory;driver->release();return false;}
    // Copy the complete, measured359-slot table, not the former17 table.
    edgeTable=static_cast<uintptr_t *>(IOMalloc((2+kDriverSlots+1)*sizeof(uintptr_t)));
    if(!edgeTable){venus_touch061_status=kIOReturnNoMemory;driver->release();return false;}
    memcpy(edgeTable,table-2,(2+kDriverSlots+1)*sizeof(uintptr_t));
    originalDispatch=table[kDispatch];edgeTable[2+kDispatch]=reinterpret_cast<uintptr_t>(&dispatch);
    __atomic_store_n(reinterpret_cast<uintptr_t **>(driver),edgeTable+2,__ATOMIC_RELEASE);
    touchDriver=driver;venus_touch061_stage=4;venus_touch061_status=0;
    IOLog("VST061: original IOHIDEventDriver attached, edge slot302/getType42 verified\n");
    return true;
}

void send() {
    if(!touchDevice||!prepareDriver())return;
    struct vst_state state;
    if(!venus_st_snapshot(&state)||state.sequence==sequence)return;
    // Match the formerly successful mainline producer: palms/hover do not
    // become confident fingers. Vanished IDs still receive an explicit lift.
    struct vst_hid_state next;uint8_t report[62];
    if(vst061_report(&state,&previous,report,&next))return;
    IOBufferMemoryDescriptor *buffer=IOBufferMemoryDescriptor::withBytes(report,sizeof(report),kIODirectionNone);
    using Handle=IOReturn (*)(IOService *,IOMemoryDescriptor *,uint32_t,IOOptionBits);
    IOReturn result=buffer?reinterpret_cast<Handle>(originalDevice[kReport])(touchDevice,buffer,0,0):kIOReturnNoMemory;
    OSSafeReleaseNULL(buffer);venus_touch061_status=result;
    if(result)return; // Keep previous state and retry, never lose a lift on error.
    previous=next;sequence=state.sequence;venus_touch061_reports=venus_touch061_reports+1;
    native_touch_hid_reports=native_touch_hid_reports+1;
    if(venus_touch061_reports<=16||venus_touch061_reports%120==0||lastContactCount!=report[61]) {
        IOLog("VST061: report=%u sequence=%u contacts=%u status=0 edge=%u\n",
            venus_touch061_reports,sequence,report[61],venus_touch061_edge_events);
        lastContactCount=report[61];
    }
}

IOReturn action(OSObject *,void *,void *,void *,void *) {send();return kIOReturnSuccess;}
void notify(void *) {if(touchLoop)touchLoop->runAction(action,touchDevice);}
void tick(OSObject *,IOTimerEventSource *timer) {
    ++ticks;send();
    if(lastHardwareStage!=venus_st_stage||lastHardwareStatus!=venus_st_status||ticks%600==0) {
        lastHardwareStage=venus_st_stage;lastHardwareStatus=venus_st_status;
        IOLog("VST061: hardware stage=%u status=%d chip=%x fw=%x messages=%u frames=%u errors=%u hid-stage=%u reports=%u\n",
            venus_st_stage,venus_st_status,venus_st_chip_id,venus_st_firmware_version,venus_st_messages,venus_st_frames,venus_st_errors,
            venus_touch061_stage,venus_touch061_reports);
    }
    timer->setTimeoutMS(100);
}

IOWorkLoop *getLoop(const IOService *) {return touchLoop;}
OSString *transport(const IOService *) {return OSString::withCString("SPI");}
OSString *product(const IOService *) {return OSString::withCString("Venus ST Touch Screen");}
IOReturn descriptor(const IOService *,IOMemoryDescriptor **out) {
    if(!out)return kIOReturnBadArgument;
    uint8_t report[sizeof(kKeyboard)+sizeof(kTouchDescriptor)];
    memcpy(report,kKeyboard,sizeof(kKeyboard));memcpy(report+sizeof(kKeyboard),kTouchDescriptor,sizeof(kTouchDescriptor));
    *out=IOBufferMemoryDescriptor::withBytes(report,sizeof(report),kIODirectionNone);
    return *out?kIOReturnSuccess:kIOReturnNoMemory;
}

bool bindDevice() {
    uintptr_t address=native_kext_symbol(kFamily,"__ZTV11IOHIDDevice");if(!address)return false;
    const uintptr_t *table=reinterpret_cast<const uintptr_t *>(address)+2;
    if(table[kDeviceSlots]!=0||!table[kDeviceSlots-1])return false;
    const struct {unsigned slot;const char *name;} checks[]={
        {22,"__ZN11IOHIDDevice4freeEv"},{190,"__ZN11IOHIDDevice5startEP9IOService"},
        {kTransport,"__ZNK11IOHIDDevice18newTransportStringEv"},
        {kProduct,"__ZNK11IOHIDDevice16newProductStringEv"},
        {kReport,"__ZN11IOHIDDevice12handleReportEP18IOMemoryDescriptor15IOHIDReportTypej"}};
    for(const auto &check:checks)if(table[check.slot]!=native_kext_symbol(kFamily,check.name))return false;
    memcpy(deviceTable,table-2,sizeof(deviceTable));memcpy(originalDevice,table,sizeof(originalDevice));
    deviceTable[2+kWorkLoop]=reinterpret_cast<uintptr_t>(&getLoop);
    deviceTable[2+kTransport]=reinterpret_cast<uintptr_t>(&transport);
    deviceTable[2+kProduct]=reinterpret_cast<uintptr_t>(&product);
    deviceTable[2+kDescriptor]=reinterpret_cast<uintptr_t>(&descriptor);
    return true;
}
}

extern "C" void venus_touch061_probe(void) {
    unsigned mode=0;PE_parse_boot_argn("venus-st-touch",&mode,sizeof(mode));
    unsigned empty=0;if(mode!=3||!__atomic_compare_exchange_n(&attempted,&empty,1,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return;
    venus_touch061_stage=1;
    auto allocate=reinterpret_cast<void *(*)(size_t)>(native_kext_symbol(kFamily,"__ZN11IOHIDDevicenwEm"));
    auto construct=reinterpret_cast<void (*)(void *,const OSMetaClass *)>(native_kext_symbol(kFamily,"__ZN11IOHIDDeviceC2EPK11OSMetaClass"));
    auto meta=reinterpret_cast<const OSMetaClass *>(native_kext_symbol(kFamily,"__ZN11IOHIDDevice10gMetaClassE"));
    if(!allocate||!construct||!meta||meta->getClassSize()!=208||!bindDevice()) {
        venus_touch061_status=kIOReturnUnsupported;IOLog("VST061: current HID ABI refused\n");return;
    }
    venus_touch061_stage=2;
    OSDictionary *match=IOService::serviceMatching("IOHIDResource");
    IOService *resource=match?IOService::waitForMatchingService(match,1000000000ULL):nullptr;
    OSSafeReleaseNULL(match);
    if(!resource&&(resource=IOService::getResourceService()))resource->retain();
    touchLoop=resource?IOWorkLoop::workLoop():nullptr;
    if(!touchLoop){venus_touch061_status=kIOReturnNoMemory;OSSafeReleaseNULL(resource);return;}
    void *memory=allocate(meta->getClassSize());
    if(memory){construct(memory,meta);*reinterpret_cast<uintptr_t **>(memory)=deviceTable+2;touchDevice=static_cast<IOService *>(memory);}
    bool valid=touchDevice&&touchDevice->init();
    if(valid) {
        valid=touchDevice->setProperty("HIDDefaultBehavior",true)&&touchDevice->setProperty("DigitizerCollectionDispatch",true)&&
            touchDevice->setProperty("Built-In",kOSBooleanTrue)&&touchDevice->setProperty("DisplayIntegrated",kOSBooleanTrue)&&
            touchDevice->setProperty("VendorID",(unsigned long long)0x0483,32)&&touchDevice->setProperty("ProductID",(unsigned long long)0x3936,32);
    }
    bool attached=valid&&touchDevice->attach(resource);
    bool started=attached&&touchDevice->start(resource);
    OSSafeReleaseNULL(resource);
    if(!started) {
        venus_touch061_status=kIOReturnError;if(attached)touchDevice->detach(touchDevice->getProvider());
        OSSafeReleaseNULL(touchDevice);OSSafeReleaseNULL(touchLoop);IOLog("VST061: device start refused\n");return;
    }
    touchTimer=IOTimerEventSource::timerEventSource(touchDevice,tick);
    if(!touchTimer||touchLoop->addEventSource(touchTimer)!=kIOReturnSuccess) {
        venus_touch061_status=kIOReturnNoMemory;IOLog("VST061: owned timer failed\n");return;
    }
    touchDevice->registerService();venus_touch061_stage=3;venus_touch061_status=0;
    venus_st_probe();native_touch_set_sink(notify,touchDevice);touchTimer->setTimeoutMS(100);
    IOLog("VST061: original334-slot HID device started, preserved035 STM producer enabled\n");
}
