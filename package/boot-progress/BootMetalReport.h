// SPDX-License-Identifier: MIT
// One bounded prelaunchd GPU/Metal status snapshot. The plugin's post-launch
// JSONL is separate: this file tells whether the accelerator was published
// before launchd, independent of userland cache permissions.
#ifndef VENUS_METAL_REPORT_H
#define VENUS_METAL_REPORT_H
#ifndef VENUS_METAL_REPORT_DIRECTORY
#define VENUS_METAL_REPORT_DIRECTORY "/private/var/db/venus-metal-041"
#endif
extern volatile uint32_t native_gpu_power_stage;
extern volatile int native_gpu_addon_stage,native_gpu_addon_status;
extern volatile unsigned venus_metal_stage;
extern volatile int venus_metal_status,venus_metal_kext_status,venus_gpu_startup_done;
volatile int venus_metal_report_status=-1,venus_metal_report_full_status=-1,venus_metal_report_medium_status=-1;
volatile unsigned venus_metal_report_bytes,venus_metal_report_readback_ok;
__attribute__((noinline)) void venus_metal_report_checkpoint(void){__asm__ volatile("":::"memory");}
static int venus_metal_write_report(proc_t p,uint64_t scratch) {
    static const char directory[]=VENUS_METAL_REPORT_DIRECTORY;
    static const char path[]=VENUS_METAL_REPORT_DIRECTORY "/startup.json";
    struct stat64 root={0},dir={0};int32_t result=0;int error;
    if(native_owner_data_stage!=4||native_owner_data_status||native_owner_data_readonly)return ENXIO;
    error=venus_gestalt_stat(p,scratch,"/private/var",&root);if(error)return error;
    if((error=copyout(directory,scratch,sizeof directory)))return error;
    struct mkdir_args md={.path=scratch,.mode=0700};error=mkdir(p,&md,&result);if(error&&error!=EEXIST)return error;
    if((error=venus_gestalt_stat(p,scratch,directory,&dir)))return error;
    if(!S_ISDIR(dir.st_mode)||dir.st_uid!=0||(dir.st_mode&07777)!=0700||dir.st_dev!=root.st_dev)return EPERM;
    char text[512];int length=snprintf(text,sizeof text,
        "{\"schema\":1,\"sample\":\"prelaunchd\",\"gpu_power_stage\":%u,\"addon_stage\":%d,\"addon_status\":%d,"
        "\"metal_stage\":%u,\"metal_status\":%d,\"kext_status\":%d,\"gpu_done\":%d}\n",
        native_gpu_power_stage,native_gpu_addon_stage,native_gpu_addon_status,
        venus_metal_stage,venus_metal_status,venus_metal_kext_status,venus_gpu_startup_done);
    if(length<=0||(size_t)length>=sizeof text)return EOVERFLOW;
    if((error=copyout(path,scratch,sizeof path)))return error;
    struct open_args op={.path=scratch,.flags=O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW,.mode=0600};
    if((error=open(p,&op,&result)))return error;
    int fd=result;
    for(unsigned sent=0;sent<(unsigned)length;) {
        unsigned piece=(unsigned)length-sent;if(piece>0x1f0)piece=0x1f0;
        if((error=copyout(text+sent,scratch+0x200,piece)))break;
        struct write_args wr={.fd=fd,.cbuf=scratch+0x200,.nbyte=piece};user_ssize_t count=0;
        error=write(p,&wr,&count);if(error)break;if(count!=piece){error=EIO;break;}sent+=piece;venus_metal_report_bytes=sent;
    }
    for(unsigned readback=0;!error&&readback<(unsigned)length;) {
        unsigned piece=(unsigned)length-readback;if(piece>0x1f0)piece=0x1f0;
        struct pread_args rd={.fd=fd,.buf=scratch+0x200,.nbyte=piece,.offset=readback};user_ssize_t count=0;char bytes[0x1f0];
        error=pread(p,&rd,&count);if(error)break;
        if(count!=piece){error=EIO;break;}
        error=copyin(scratch+0x200,bytes,piece);if(!error&&memcmp(bytes,text+readback,piece))error=EIO;
        readback+=piece;if(!error&&readback==(unsigned)length)venus_metal_report_readback_ok=1;
    }
    if(!error){struct fsync_args sync={.fd=fd};error=fsync(p,&sync,&result);}
    if(!error){struct fcntl_args full={.fd=fd,.cmd=F_FULLFSYNC,.arg=0};venus_metal_report_full_status=sys_fcntl(p,&full,&result);}
    struct close_args cl={.fd=fd};int closed=sys_close(p,&cl,&result);if(!error)error=closed;
    if(!error)error=venus_gestalt_sync_directory(p,scratch,directory);
    if(!error)error=venus_gestalt_sync_directory(p,scratch,"/private/var/db");
    if(!error){venus_metal_report_medium_status=native_ufs_store_sync()?0:EIO;error=venus_metal_report_medium_status;}
    return error;
}
static void venus_metal_report_after_policy(proc_t p,uint64_t scratch) {
    static int attempted;
    if(attempted)return;attempted=1;
    venus_metal_report_status=venus_metal_write_report(p,scratch);
    printf("venus-metal: startup report=%d full=%d media=%d readback=%u\n",venus_metal_report_status,
           venus_metal_report_full_status,venus_metal_report_medium_status,venus_metal_report_readback_ok);
    venus_metal_report_checkpoint();
}
#endif
