// Execute production MGQueryProbe.c using explicit CF/IOKit/MG stand-ins.
#define dlopen probe_dlopen
#define dlsym probe_dlsym
#define dlclose probe_dlclose
#define getpid probe_getpid
#define getuid probe_getuid
#define sysctlbyname probe_sysctl
#define main probe_main
#include "MGQueryProbe.c"
#undef main
#include <string.h>
#include <stdlib.h>
#include <assert.h>

static int libfail,apifail,copies,queries,releases;
static const uint32_t scale_data=2;
static const unsigned char screen_data[24]={255,255,255,255,255,255,255,255,255,255,255,255};
static CFRef mock_string(CFRef allocator,const char *s,uint32_t encoding){assert(!allocator&&encoding==0x08000100);return s;}
static void mock_release(CFRef value){assert(value);++releases;}
static CFTypeID mock_type(CFRef value){(void)value;return 19;}
static CFTypeID mock_datatype(void){return 19;}
static CFTypeID mock_numbertype(void){return 20;}
static CFIndex mock_length(CFRef value){return value==screen_data?24:4;}
static const unsigned char *mock_bytes(CFRef value){return value;}
static Boolean mock_number(CFRef value,int type,void *out){(void)value;(void)type;(void)out;assert(0);return 0;}
static Port mock_entry(Port port,const char *path){assert(port==0);return !strcmp(path,"IODeviceTree:/chosen")?43:0;}
static CFRef mock_property(Port entry,CFRef name,CFRef allocator,uint32_t options){
    assert(entry==43&&!allocator&&!options);
    return !strcmp(name,"display-scale")?&scale_data:NULL;
}
static int mock_port_release(Port port){assert(port==43);return 0;}
static float mock_float(CFRef question,float fallback){
    assert(!strcmp(question,"main-screen-scale"));
    static const float expected[]={1.0f,2.0f,7.0f};assert(fallback==expected[queries]);++queries;return 0.0f;
}
static CFRef mock_copy(CFRef question,CFRef options){assert(!options);++copies;return !strcmp(question,"MainScreenStaticInfo")?screen_data:NULL;}
static CFRef mock_copy_error(CFRef question,CFRef options,int *error){*error=0;return mock_copy(question,options);}
int probe_sysctl(const char *name,void *out,size_t *n,void *newvalue,size_t length){
    const char *value="01234567-89AB-CDEF-0123-456789ABCDEF";
    assert(!strcmp(name,"kern.bootsessionuuid")&&!newvalue&&!length&&*n>strlen(value));
    strcpy(out,value);*n=strlen(value)+1;return 0;
}
int probe_getpid(void){return 100;}
unsigned probe_getuid(void){return 501;}
void *probe_dlopen(const char *name,int flags){assert(flags==2);return libfail?NULL:(void *)name;}
int probe_dlclose(void *handle){assert(handle);return 0;}
void *probe_dlsym(void *handle,const char *name){
    assert(handle);if(apifail&&!strcmp(name,"MGGetFloat32Answer"))return NULL;
#define MAP(symbol,target) if(!strcmp(name,symbol))return (void *)target
    MAP("CFStringCreateWithCString",mock_string);MAP("CFRelease",mock_release);
    MAP("CFGetTypeID",mock_type);MAP("CFDataGetTypeID",mock_datatype);MAP("CFNumberGetTypeID",mock_numbertype);
    MAP("CFDataGetLength",mock_length);MAP("CFDataGetBytePtr",mock_bytes);MAP("CFNumberGetValue",mock_number);
    MAP("IORegistryEntryFromPath",mock_entry);MAP("IORegistryEntryCreateCFProperty",mock_property);MAP("IOObjectRelease",mock_port_release);
    MAP("MGGetFloat32Answer",mock_float);MAP("MGCopyAnswer",mock_copy);MAP("MGCopyAnswerWithError",mock_copy_error);
#undef MAP
    return NULL;
}
int main(int argc,char **argv){
    if(argc>1){libfail=!strcmp(argv[1],"library-failure");apifail=!strcmp(argv[1],"api-failure");}
    int rc=probe_main();
    if(!libfail&&!apifail){assert(queries==3&&copies==2&&releases>0&&rc==0);}
    else assert(!queries&&!copies&&rc!=0);
    return 0;
}
