// SPDX-License-Identifier: MIT
#include "metal_publication_shim.h"
#include "../package/Adreno660/VenusMetalPublication.cpp"

Failure failure=None;
unsigned bootEnabled=1,slept=0,completeAfter=0,released=0,registrations=0;
bool initializedClass=false;
std::vector<std::string> calls;
static IOService *allocated;
extern "C" {
kmod_info_t g_kernel_kmod_info={"kernel"};
volatile int venus_gpu_startup_done=0;
kern_return_t OSKextLoadKextWithIdentifier(const char *name) {
    assert(!strcmp(name,"com.apple.iokit.IOGPUFamily"));
    calls.push_back("load-parent");
    return failure==Load ? -77 : 0;
}
void native_adreno_accelerator_static_init() {
    assert(!calls.empty() && calls.back()=="begin-class");
    initializedClass=true;
    calls.push_back("init-class");
}
IOService *native_adreno_accelerator_allocate() {
    assert(initializedClass && calls.back()=="end-class");
    calls.push_back("allocate");
    allocated=failure==Allocate ? nullptr : new IOService;
    return allocated;
}
unsigned native_adreno_accelerator_instance_size() { return failure==ObjectSize ? 144 : 136; }
IOService *native_adreno_published_service() {
    static IOService core;
    return failure==NoCore ? nullptr : &core;
}
}

static void reset(Failure selected=None) {
    failure=selected;
    bootEnabled=1; slept=completeAfter=released=registrations=0;
    initializedClass=false; allocated=nullptr; calls.clear();
    venus_metal_stage=0; venus_metal_status=-1; venus_metal_kext_status=-1;
    venus_metal_prelaunch_wait_ms=0;
    __atomic_store_n(&venus_gpu_startup_done,0,__ATOMIC_RELEASE);
}

int main() {
    reset(); bootEnabled=0;
    assert(venus_metal_publish()==kIOReturnNotReady && calls.empty());
    venus_metal_wait_before_launchd();
    assert(!slept && !venus_metal_stage);
    const Failure cases[]={NoCore,Load,NoParent,ParentSize,Begin,End,ObjectSize,
                           Allocate,Init,NameProperty,ClassProperty,GrantProperty,Attach};
    for (auto test:cases) {
        reset(test);
        assert(venus_metal_publish()!=0 && !registrations && venus_metal_stage<5);
        assert(!allocated || released==1);
        auto count=calls.size();
        assert(venus_metal_publish()!=0 && calls.size()==count); // no duplicate class initialization
    }
    reset();
    assert(venus_metal_publish()==0 && venus_metal_stage==5 && registrations==1);
    const std::vector<std::string> expected={"load-parent","begin-class","init-class","end-class",
        "allocate","init-device","MetalPluginName","MetalPluginClassName","NativeSandboxGrantProcess",
        "attach","discover"};
    assert(calls==expected);
    assert(venus_metal_publish()==0 && registrations==1);
    delete allocated;
    reset(); completeAfter=20;
    venus_metal_wait_before_launchd();
    assert(slept==20 && venus_metal_prelaunch_wait_ms==20);
    reset();
    venus_metal_wait_before_launchd();
    assert(slept==30000 && venus_metal_prelaunch_wait_ms==30000);
    reset(); __atomic_store_n(&venus_gpu_startup_done,1,__ATOMIC_RELEASE);
    venus_metal_wait_before_launchd();
    assert(slept==0);
}
