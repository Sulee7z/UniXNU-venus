// SPDX-License-Identifier: MIT
#pragma once
#include <cassert>
#include <cstdint>
#include <cstring>
#include <map>
#include <string>
#include <vector>

using IOReturn = int;
using kern_return_t = int;
struct kmod_info_t { const char *name; };
constexpr int kIOReturnSuccess=0, kIOReturnNotReady=-1, kIOReturnNotFound=-2,
    kIOReturnNoResources=-3, kIOReturnInvalid=-4, kIOReturnNoMemory=-5,
    kIOReturnError=-6, kIOReturnNotAttached=-7;
enum Failure { None, NoCore, Load, NoParent, ParentSize, Begin, End, ObjectSize,
               Allocate, Init, NameProperty, ClassProperty, GrantProperty, Attach };
extern Failure failure;
extern unsigned bootEnabled, slept, completeAfter, released, registrations;
extern bool initializedClass;
extern std::vector<std::string> calls;
extern "C" volatile int venus_gpu_startup_done;

class OSSymbol {
public:
    std::string name;
    explicit OSSymbol(const char *value) : name(value) {}
    static const OSSymbol *withCString(const char *value) { return new OSSymbol(value); }
    void release() const { delete this; }
};
#define OSSafeReleaseNULL(p) do { if (p) (p)->release(); (p)=nullptr; } while (0)

class OSMetaClass {
public:
    unsigned getClassSize() const { return failure==ParentSize ? 144 : 136; }
    static const OSMetaClass *getMetaClassWithName(const OSSymbol *name) {
        assert(name->name=="IOAcceleratorES");
        static OSMetaClass parent;
        return failure==NoParent ? nullptr : &parent;
    }
    static void *preModLoad(const char *) {
        calls.push_back("begin-class");
        return failure==Begin ? nullptr : &calls;
    }
    static int postModLoad(void *handle) {
        assert(handle==&calls && initializedClass);
        calls.push_back("end-class");
        return failure==End ? -77 : 0;
    }
};

class IOService {
    std::map<std::string,std::string> properties;
    bool attached=false;
public:
    bool init() { calls.push_back("init-device"); return failure!=Init; }
    bool setProperty(const char *key,const char *value) {
        calls.push_back(key);
        if ((failure==NameProperty && !strcmp(key,"MetalPluginName")) ||
            (failure==ClassProperty && !strcmp(key,"MetalPluginClassName")) ||
            (failure==GrantProperty && !strcmp(key,"NativeSandboxGrantProcess"))) return false;
        properties[key]=value;
        return true;
    }
    static IOService *getPlatform() { static IOService platform; return &platform; }
    bool attach(IOService *platform) {
        assert(platform==getPlatform());
        calls.push_back("attach");
        attached=failure!=Attach;
        return attached;
    }
    void registerService() {
        // A synchronous discovery callback must see a complete usable device.
        assert(attached && initializedClass);
        assert(properties.at("MetalPluginName")=="NativeAdrenoMetal");
        assert(properties.at("MetalPluginClassName")=="NativeAdrenoMetalDevice");
        assert(properties.at("NativeSandboxGrantProcess")=="backboardd");
        calls.push_back("discover");
        registrations++;
    }
    void release() { released++; delete this; }
};

inline bool PE_parse_boot_argn(const char *name,void *output,int bytes) {
    assert(!strcmp(name,"zeta-gpu-metal") && bytes==sizeof(unsigned));
    *static_cast<unsigned *>(output)=bootEnabled;
    return true;
}
inline void IOSleep(unsigned ms) {
    slept+=ms;
    if (completeAfter && slept>=completeAfter)
        __atomic_store_n(&venus_gpu_startup_done,1,__ATOMIC_RELEASE);
}
inline void IOLog(const char *,...) {}
