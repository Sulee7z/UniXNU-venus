// SPDX-License-Identifier: MIT
// Original documented cache invalidation, after normal Data/watchdog policy.
// Persist begin/end before depending on launchd or an unregistered user job.
#ifndef VENUS_SCALE_REFRESH_011_H
#define VENUS_SCALE_REFRESH_011_H
#define VENUS_GESTALT_BACKUP_SUFFIX ".venus-scale-011.bak"
#include "BootGestaltCache.h"

static unsigned venus_scale011_attempted;
volatile int venus_scale011_journal_status=-1;
static const char venus_scale011_report[]="/private/var/tmp/venus-scale-011.jsonl";
__attribute__((noinline)) void venus_scale011_checkpoint(void) {__asm__ volatile("" ::: "memory");}

static int venus_scale011_sync_parent(proc_t p,uint64_t scratch) {
    int32_t result=0;int error=copyout("/private/var/tmp",scratch,sizeof("/private/var/tmp"));
    if(error)return error;
    struct open_args op={.path=scratch,.flags=O_RDONLY|O_DIRECTORY|O_NOFOLLOW,.mode=0};
    if((error=open(p,&op,&result)))return error;
    int fd=result;struct fsync_args sync={.fd=fd};error=fsync(p,&sync,&result);
    struct close_args close_args={.fd=fd};int closed=sys_close(p,&close_args,&result);
    return error?error:closed;
}

static int venus_scale011_emit(proc_t p,uint64_t scratch,int fd,const char *phase,int status) {
    char line[320];int32_t result=0;
    int length=snprintf(line,sizeof(line),"{\"schema_version\":1,\"probe\":\"venus-scale-refresh-011\","
        "\"phase\":\"%s\",\"status\":%d,\"moved\":%u,\"missing\":%u,\"data_stage\":%u,\"data_status\":%d}\n",
        phase,status,venus_gestalt_moved,venus_gestalt_missing,native_owner_data_stage,native_owner_data_status);
    if(length<0||(unsigned)length>=sizeof(line))return EOVERFLOW;
    int error=copyout(line,scratch+0x200,(unsigned)length);
    if(error)return error;
    struct write_args write_args={.fd=fd,.cbuf=scratch+0x200,.nbyte=(unsigned)length};user_ssize_t written=0;
    if((error=write(p,&write_args,&written)))return error;
    if(written!=length)return EIO;
    struct fsync_args sync={.fd=fd};if((error=fsync(p,&sync,&result)))return error;
    if((error=venus_scale011_sync_parent(p,scratch)))return error;
    struct fcntl_args full={.fd=fd,.cmd=F_FULLFSYNC,.arg=0};
    if((error=sys_fcntl(p,&full,&result)))return error;
    return native_ufs_store_sync()?0:EIO;
}

static void venus_scale011_refresh_after_policy(proc_t p,uint64_t scratch) {
    unsigned enabled=0;int32_t result=0;
    if(!PE_parse_boot_argn("venus-gestalt-refresh",&enabled,sizeof(enabled))||enabled!=1||venus_scale011_attempted)return;
    venus_scale011_attempted=1;
    if(native_owner_data_stage!=4||native_owner_data_status||native_owner_data_readonly){venus_scale011_journal_status=ENXIO;return;}
    int error=copyout(venus_scale011_report,scratch,sizeof(venus_scale011_report));
    if(error){venus_scale011_journal_status=error;return;}
    struct open_args op={.path=scratch,.flags=O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,.mode=0644};
    error=open(p,&op,&result);
    if(error){venus_scale011_journal_status=error;return;} // Existing marker keeps all old reports/backups intact.
    int fd=result;
    error=venus_scale011_emit(p,scratch,fd,"begin",-1);
    if(!error){
        int cache_status=venus_boot_gestalt_cache(p,scratch);
        error=venus_scale011_emit(p,scratch,fd,"complete",cache_status);
        if(!error)error=cache_status;
    }
    venus_scale011_journal_status=error;
    struct close_args close_args={.fd=fd};int closed=sys_close(p,&close_args,&result);
    if(!venus_scale011_journal_status)venus_scale011_journal_status=closed;
    printf("VENUS scale011 journal=%d cache=%d moved=%x missing=%x\n",venus_scale011_journal_status,
           venus_gestalt_status,venus_gestalt_moved,venus_gestalt_missing);
}
#endif
