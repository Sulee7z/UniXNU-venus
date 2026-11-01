// SPDX-License-Identifier: MIT
// Board integration of the existing NativeAdrenoAccelerator adapter. It has a
// real iOS17 IOAcceleratorES parent; the private GPU service is not that parent.
#include <IOKit/IOService.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOPlatformExpert.h>
#include <libkern/c++/OSMetaClass.h>
#include <libkern/c++/OSSymbol.h>
#include <mach/kmod.h>

extern "C" kern_return_t OSKextLoadKextWithIdentifier(const char *);
extern "C" kmod_info_t g_kernel_kmod_info;
extern "C" void native_adreno_accelerator_static_init(void)
    __asm__("__GLOBAL__sub_I_NativeAdrenoAccelerator.cpp");
extern "C" IOService *native_adreno_accelerator_allocate(void);
extern "C" unsigned native_adreno_accelerator_instance_size(void);
extern "C" IOService *native_adreno_published_service(void);
extern "C" volatile int venus_gpu_startup_done;

extern "C" {
volatile unsigned venus_metal_stage = 0;
volatile int venus_metal_status = -1;
volatile int venus_metal_kext_status = -1;
volatile unsigned venus_metal_prelaunch_wait_ms = 0;
}

static bool enabled() {
    unsigned value = 0;
    PE_parse_boot_argn("zeta-gpu-metal", &value, sizeof value);
    return value == 1;
}

static IOReturn finish(IOReturn result) {
    venus_metal_status = result;
    return result;
}

extern "C" IOReturn venus_metal_publish(void) {
    if (!enabled()) return kIOReturnNotReady;
    if (venus_metal_stage) return venus_metal_status;
    venus_metal_stage = 1;
    venus_metal_status = kIOReturnNotReady;
    // The wrapper delegates client operations to this initialized transport.
    // Never expose a Metal device before the real GPU core has been published.
    if (!native_adreno_published_service()) return venus_metal_status;
    venus_metal_kext_status = OSKextLoadKextWithIdentifier("com.apple.iokit.IOGPUFamily");
    if (venus_metal_kext_status) return finish(venus_metal_kext_status);
    const OSSymbol *name = OSSymbol::withCString("IOAcceleratorES");
    const OSMetaClass *parent = name ? OSMetaClass::getMetaClassWithName(name) : nullptr;
    OSSafeReleaseNULL(name);
    if (!parent || parent->getClassSize() != 136)
        return finish(kIOReturnNotFound);
    venus_metal_stage = 2;
    void *handle = OSMetaClass::preModLoad(g_kernel_kmod_info.name);
    if (!handle) return finish(kIOReturnNoResources);
    native_adreno_accelerator_static_init();
    venus_metal_status = OSMetaClass::postModLoad(handle);
    if (venus_metal_status) return venus_metal_status;
    if (native_adreno_accelerator_instance_size() != 136)
        return finish(kIOReturnInvalid);
    venus_metal_stage = 3;
    IOService *accelerator = native_adreno_accelerator_allocate();
    if (!accelerator) return finish(kIOReturnNoMemory);
    if (!accelerator->init()) {
        accelerator->release();
        return finish(kIOReturnError);
    }
    // IOKit matching can run as soon as registerService is called. All discovery
    // properties must exist first (also the ordering in HackiOS metal-enable).
    if (!accelerator->setProperty("MetalPluginName", "NativeAdrenoMetal") ||
        !accelerator->setProperty("MetalPluginClassName", "NativeAdrenoMetalDevice") ||
        !accelerator->setProperty("NativeSandboxGrantProcess", "backboardd")) {
        accelerator->release();
        return finish(kIOReturnNoMemory);
    }
    venus_metal_stage = 4;
    if (!accelerator->attach(IOService::getPlatform())) {
        accelerator->release();
        return finish(kIOReturnNotAttached);
    }
    accelerator->registerService();
    venus_metal_status = kIOReturnSuccess;
    venus_metal_stage = 5;
    return kIOReturnSuccess;
}

extern "C" void venus_metal_wait_before_launchd(void) {
    if (!enabled()) return;
    // The GPU thread owns initialization and completion. Waiting here only
    // orders startup before Metal's first process-local device enumeration.
    // A failure/timeout leaves the ordinary software UI startup available.
    unsigned elapsed = 0;
    while (!__atomic_load_n(&venus_gpu_startup_done, __ATOMIC_ACQUIRE) && elapsed < 30000) {
        IOSleep(10);
        elapsed += 10;
    }
    venus_metal_prelaunch_wait_ms = elapsed;
    IOLog("venus-metal: prelaunch done=%d wait=%u stage=%u status=%#x kext=%#x\n",
        __atomic_load_n(&venus_gpu_startup_done, __ATOMIC_ACQUIRE), elapsed,
        venus_metal_stage, unsigned(venus_metal_status), unsigned(venus_metal_kext_status));
}
