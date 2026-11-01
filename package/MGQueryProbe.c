// SPDX-License-Identifier: MIT
// One userspace observation of actual IOKit/MobileGestalt results. No property
// setters, cache deletion, BRK, reset, or source-disk writes. stdout is the report.
// LP64 C ABI: public CoreFoundation/IOKit APIs and the two-argument MGCopyAnswer
// interface (theos/headers MobileGestalt.h), also checked against 21H461 readers.
#include <stdint.h>
#include <stddef.h>

extern void *dlopen(const char *,int);
extern void *dlsym(void *,const char *);
extern int dlclose(void *);
extern int printf(const char *,...);
extern int getpid(void);
extern unsigned getuid(void);
extern int sysctlbyname(const char *,void *,size_t *,void *,size_t);

typedef const void *CFRef;
typedef unsigned long CFTypeID;
typedef long CFIndex;
typedef unsigned char Boolean;
typedef uint32_t Port;

static CFRef (*string_create)(CFRef,const char *,uint32_t);
static void (*release)(CFRef);
static CFTypeID (*type_id)(CFRef),(*data_type)(void),(*number_type)(void);
static CFIndex (*data_length)(CFRef);
static const unsigned char *(*data_bytes)(CFRef);
static Boolean (*number_value)(CFRef,int,void *);
static Port (*registry_entry)(Port,const char *);
static CFRef (*registry_property)(Port,CFRef,CFRef,uint32_t);
static int (*port_release)(Port);
static float (*mg_float)(CFRef,float);
static CFRef (*mg_copy)(CFRef,CFRef);
static CFRef (*mg_copy_error)(CFRef,CFRef,int *);

static uint32_t float_bits(float f) {
    union {float f;uint32_t u;} v={.f=f};return v.u;
}
static CFRef key(const char *s) {return string_create(NULL,s,0x08000100u);}

static void value_report(CFRef value) {
    if(!value){printf("{\"state\":\"null\"}");return;}
    CFTypeID type=type_id(value);
    if(type==data_type()) {
        CFIndex n=data_length(value);const unsigned char *p=data_bytes(value);
        printf("{\"state\":\"data\",\"length\":%ld,\"hex\":\"",n);
        if(n>=0 && p)for(CFIndex i=0;i<n && i<64;++i)printf("%02x",p[i]);
        printf("\",\"truncated\":%s}",n>64?"true":"false");
    } else if(type==number_type()) {
        float f=0;Boolean ok=number_value(value,5,&f); // kCFNumberFloat32Type
        if(ok)printf("{\"state\":\"number\",\"float32_bits\":\"%08x\"}",float_bits(f));
        else printf("{\"state\":\"number_conversion_failed\"}");
    } else printf("{\"state\":\"other_type\",\"type_id\":%lu}",type);
}

static void dt_report(const char *path) {
    Port entry=registry_entry(0,path);
    printf("{\"path\":\"%s\",\"entry_found\":%s",path,entry?"true":"false");
    if(entry) {
        static const char *const properties[]={"display-scale","display-rotation"};
        for(unsigned i=0;i<2;++i) {
            CFRef k=key(properties[i]),v=k?registry_property(entry,k,NULL,0):NULL;
            printf(",\"%s\":",properties[i]);value_report(v);
            if(v)release(v);if(k)release(k);
        }
        printf(",\"release_status\":%d",port_release(entry));
    }
    printf("}");
}

int main(void) {
    char boot[64]={0};size_t bootlen=sizeof(boot);
    int bootrc=sysctlbyname("kern.bootsessionuuid",boot,&bootlen,NULL,0);
    // UUID is the only variable string printed in JSON. Refuse malformed bytes.
    int uuid_ok=bootrc==0 && bootlen>0 && bootlen<=sizeof(boot);
    for(size_t i=0;i<sizeof(boot) && boot[i];++i)
        if(!((boot[i]>='0'&&boot[i]<='9')||(boot[i]>='a'&&boot[i]<='f')||
             (boot[i]>='A'&&boot[i]<='F')||boot[i]=='-'))uuid_ok=0;
    boot[sizeof(boot)-1]=0;
    printf("{\"schema_version\":1,\"probe\":\"venus-mg-query-v1\",\"pid\":%d,\"uid\":%u,"
           "\"boot_uuid_status\":%d,\"boot_uuid\":\"%s\",",getpid(),getuid(),bootrc,uuid_ok?boot:"");
    void *cf=dlopen("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation",2);
    void *io=dlopen("/System/Library/Frameworks/IOKit.framework/IOKit",2);
    void *mg=dlopen("/usr/lib/libMobileGestalt.dylib",2);
    printf("\"libraries\":{\"CoreFoundation\":%s,\"IOKit\":%s,\"MobileGestalt\":%s},",
           cf?"true":"false",io?"true":"false",mg?"true":"false");
    if(!cf||!io||!mg){printf("\"complete\":false,\"error\":\"dlopen\"}\n");return 2;}
#define LOAD(target,type,handle,name) target=(type)dlsym(handle,name)
    LOAD(string_create,CFRef (*)(CFRef,const char *,uint32_t),cf,"CFStringCreateWithCString");
    LOAD(release,void (*)(CFRef),cf,"CFRelease");
    LOAD(type_id,CFTypeID (*)(CFRef),cf,"CFGetTypeID");
    LOAD(data_type,CFTypeID (*)(void),cf,"CFDataGetTypeID");
    LOAD(number_type,CFTypeID (*)(void),cf,"CFNumberGetTypeID");
    LOAD(data_length,CFIndex (*)(CFRef),cf,"CFDataGetLength");
    LOAD(data_bytes,const unsigned char *(*)(CFRef),cf,"CFDataGetBytePtr");
    LOAD(number_value,Boolean (*)(CFRef,int,void *),cf,"CFNumberGetValue");
    LOAD(registry_entry,Port (*)(Port,const char *),io,"IORegistryEntryFromPath");
    LOAD(registry_property,CFRef (*)(Port,CFRef,CFRef,uint32_t),io,"IORegistryEntryCreateCFProperty");
    LOAD(port_release,int (*)(Port),io,"IOObjectRelease");
    LOAD(mg_float,float (*)(CFRef,float),mg,"MGGetFloat32Answer");
    LOAD(mg_copy,CFRef (*)(CFRef,CFRef),mg,"MGCopyAnswer");
    LOAD(mg_copy_error,CFRef (*)(CFRef,CFRef,int *),mg,"MGCopyAnswerWithError");
#undef LOAD
    if(!string_create||!release||!type_id||!data_type||!number_type||!data_length||!data_bytes||
       !number_value||!registry_entry||!registry_property||!port_release||!mg_float||!mg_copy) {
        printf("\"complete\":false,\"error\":\"missing_api\"}\n");return 3;
    }
    // Before calling any MG answer API, record both meaningful user API paths.
    printf("\"device_tree\":[");dt_report("IODeviceTree:/chosen");printf(",");
    dt_report("IODeviceTree:/device-tree/chosen");printf("],\"float_answers\":[");
    const float defaults[]={1.0f,2.0f,7.0f};CFRef q=key("main-screen-scale");
    if(!q){printf("],\"complete\":false,\"error\":\"key_allocation\"}\n");return 4;}
    for(unsigned i=0;i<3;++i) {
        float actual=mg_float(q,defaults[i]);
        printf("%s{\"default_bits\":\"%08x\",\"return_bits\":\"%08x\"}",
               i?",":"",float_bits(defaults[i]),float_bits(actual));
    }
    release(q);printf("],\"copy_answers\":{");
    static const char *const questions[]={"main-screen-scale","MainScreenStaticInfo"};
    for(unsigned i=0;i<2;++i) {
        int error=-1;q=key(questions[i]);
        CFRef answer=q?(mg_copy_error?mg_copy_error(q,NULL,&error):mg_copy(q,NULL)):NULL;
        printf("%s\"%s\":{\"error_available\":%s,\"error\":%d,\"answer\":",i?",":"",questions[i],
               mg_copy_error?"true":"false",error);
        value_report(answer);printf("}");
        if(answer)release(answer);if(q)release(q);
    }
    printf("},\"complete\":true}\n");
    dlclose(mg);dlclose(io);dlclose(cf);return 0;
}
