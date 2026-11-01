// SPDX-License-Identifier: MIT
// Venus adaptation of none24smu/zeta + UniXNU NativeMetal discovery. The original
// Metal loader calls initWithAcceleratorPort and registers the returned device.
#import <Foundation/Foundation.h>
#include <objc/runtime.h>
#include <dlfcn.h>
#include <unistd.h>
#include <sys/stat.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
#include <pwd.h>
#include "NativeBridgeMetalFrontend.h"
#include "bridge/NativeMetalObjects.h"
#include "VenusMetalCache.h"
#include "VenusMetalDiagnostics.h"

@interface _MTLDevice : NSObject
@end
@interface NativeAdrenoMetalDevice : _MTLDevice
- (id)initWithAcceleratorPort:(unsigned)port;
@end
static bool pluginPath(char out[1024],const char *name,bool beside) {
    Dl_info info={};
    if(!dladdr((const void *)&pluginPath,&info) || !info.dli_fname)return false;
    if(strlcpy(out,info.dli_fname,1024)>=1024)return false;
    char *slash=strrchr(out,'/');if(!slash)return false;*slash=0;
    if(beside){slash=strrchr(out,'/');if(!slash)return false;*slash=0;}
    return strlcat(out,"/",1024)<1024 && strlcat(out,name,1024)<1024;
}
static bool listedClient() {
    char path[1024];if(!pluginPath(path,"NativeAdrenoMetal.clients",true))return false;
    FILE *file=fopen(path,"r");if(!file)return false;
    char text[1024]={};const size_t n=fread(text,1,sizeof text-1,file);fclose(file);text[n]=0;
    for(char *save=nullptr,*name=strtok_r(text," ,\t\r\n",&save);name;name=strtok_r(nullptr," ,\t\r\n",&save))
        if(!strcmp(name,getprogname()))return true;
    return false;
}
static id refusal(const char *phase,const char *reason) {
    NSLog(@"venus-metal: process=%s phase=%s refused=%s",getprogname(),phase,reason?reason:"");
    venus_metal_diag(phase,reason?reason:"");
    return nil;
}
static id deviceForPort(unsigned port) {
    venus_metal_diag("entry","initWithAcceleratorPort");
    char marker[1024],loader[1024];
    if(!pluginPath(marker,"NativeAdrenoMetal.publish",true) || access(marker,R_OK))return refusal("publish","marker unavailable");
    if(!listedClient())return refusal("client","process not selected");
    if(!pluginPath(loader,"libvulkan_freedreno.dylib",false) || access(loader,R_OK))return refusal("loader","Turnip unavailable");
    uint64_t registryID=0;
    void *iokit=dlopen("/System/Library/Frameworks/IOKit.framework/IOKit",RTLD_NOW|RTLD_LOCAL);
    if(!iokit)return refusal("registry",dlerror());
    auto entryID=(int (*)(unsigned,uint64_t *))dlsym(iokit,"IORegistryEntryGetRegistryEntryID");
    const int error=entryID?entryID(port,&registryID):-1;dlclose(iokit);
    if(error || !registryID)return refusal("registry","entry ID unavailable");
    venus_metal_diag("registry","accelerator registry entry resolved");

    // Same process-local constraints as zeta's publish::deviceForPort. The
    // frontend imports plain IOSurface rows; Apple framebuffer compression is
    // a different layout, not a GPU-rendering enable switch.
    if(setenv("CA_DISABLE_FRAMEBUFFER_COMPRESSION","1",1))return refusal("format",strerror(errno));
    CFPreferencesSetAppValue(CFSTR("CAEnableFramebufferCompression"),kCFBooleanFalse,kCFPreferencesCurrentApplication);
    CFPreferencesSetAppValue(CFSTR("CAEnableIOSurfaceCompression"),kCFBooleanFalse,kCFPreferencesCurrentApplication);

    char prefixes[3][1024]={},cache[1024];
    // Keep persistent shader artifacts ahead of the boot-cleaned temp path.
    if(const passwd *user=getpwuid(getuid());user && user->pw_dir && user->pw_dir[0]) {
        int n=snprintf(prefixes[0],sizeof prefixes[0],"%s/Library/Caches/com.apple.backboardd",user->pw_dir);
        if(n<0 || (size_t)n>=sizeof prefixes[0] || (mkdir(prefixes[0],0700) && errno!=EEXIST) ||
           access(prefixes[0],W_OK|X_OK))prefixes[0][0]=0;
    }
    const int selectors[2]={_CS_DARWIN_USER_CACHE_DIR,_CS_DARWIN_USER_TEMP_DIR};
    for(unsigned i=0;i<2;++i) {
        size_t needed=confstr(selectors[i],prefixes[i+1],sizeof prefixes[i+1]);
        if(!needed || needed>sizeof prefixes[i+1])prefixes[i+1][0]=0;
    }
    for(unsigned i=0;i<3;++i) {
        if(!prefixes[i][0])continue;
        int status=venus_metal_cache_path(cache,sizeof cache,prefixes[i]);
        if(!status)status=venus_metal_cache_prepare(cache);
        if(status){NSLog(@"venus-metal: cache candidate=%u refused=%s",i,strerror(status));venus_metal_diag("cache",strerror(status));continue;}
        venus_metal_diag("cache-ready",cache);
        id device=nil;
        @try {device=native_bridge_metal_open(loader,cache,registryID,nullptr);}
        @catch(NSException *exception){NSLog(@"venus-metal: device exception=%@ reason=%@",exception.name,exception.reason);venus_metal_diag("exception",exception.reason.UTF8String);}
        if(device){NSLog(@"venus-metal: process=%s device returned cache=%u registry=%llu",getprogname(),i,(unsigned long long)registryID);venus_metal_diag("device","Metal device created");return device;}
        NSLog(@"venus-metal: device candidate=%u refused=%s",i,nmb_last_error());
        venus_metal_diag("device",nmb_last_error());
    }
    return refusal("device","no usable device/cache candidate");
}
@implementation NativeAdrenoMetalDevice
- (id)initWithAcceleratorPort:(unsigned)port {
    self=[super init];if(!self || !port)return nil;
    if([[NSProcessInfo processInfo] operatingSystemVersion].majorVersion!=17 || class_getInstanceSize(objc_getClass("_MTLDevice"))!=536)return refusal("ABI","expected iOS17 _MTLDevice536");
    static id device=nil;
    static bool attempted=false;
    @synchronized([NativeAdrenoMetalDevice class]) {
        if(!attempted){attempted=true;device=deviceForPort(port);}
        return device;
    }
}
@end
