// SPDX-License-Identifier: MIT
// Protected Data journal/backups: launchd cleans /tmp before user tasks run.
// Cache invalidation uses the original rename/parent/media contract; extra
// FULLFSYNC telemetry never masks or prevents that independent transaction.
#ifndef VENUS_SCALE_REFRESH_012_H
#define VENUS_SCALE_REFRESH_012_H
#define VENUS_GESTALT_BACKUP_DIRECTORY "/private/var/db/venus-scale-012"
static void venus_scale012_observe(const char *,unsigned,int);
#define VENUS_GESTALT_EVENT(phase,index,status) venus_scale012_observe(phase,index,status)
#include "BootGestaltCache.h"

static unsigned venus_scale012_attempted;
static proc_t venus_scale012_process;
static uint64_t venus_scale012_scratch;
static int venus_scale012_fd=-1;
volatile int venus_scale012_journal_status=-1,venus_scale012_full_sync_status=-1;
volatile uint32_t venus_scale012_source_uid,venus_scale012_source_mode,venus_scale012_source_size;
volatile int venus_scale012_cache_failure_phase;
static const char venus_scale012_report[]="/private/var/db/venus-scale-012/refresh.jsonl";
__attribute__((noinline)) void venus_scale012_checkpoint(void){__asm__ volatile("" ::: "memory");}

static int venus_scale012_emit(const char *phase,unsigned index,int status) {
    char line[320];int32_t result=0;int fd=venus_scale012_fd;
    if(fd<0)return EBADF;
    int length=snprintf(line,sizeof(line),"{\"schema_version\":1,\"probe\":\"venus-scale-refresh-012\","
        "\"phase\":\"%s\",\"index\":%u,\"status\":%d,\"moved\":%u,\"missing\":%u,\"data_stage\":%u,\"data_status\":%d}\n",
        phase,index,status,venus_gestalt_moved,venus_gestalt_missing,native_owner_data_stage,native_owner_data_status);
    if(length<0||(unsigned)length>=sizeof(line))return EOVERFLOW;
    int error=copyout(line,venus_scale012_scratch+0x200,(unsigned)length);if(error)return error;
    struct write_args wr={.fd=fd,.cbuf=venus_scale012_scratch+0x200,.nbyte=(unsigned)length};user_ssize_t written=0;
    if((error=write(venus_scale012_process,&wr,&written)))return error;
    if(written!=length)return EIO;
    struct fsync_args sync={.fd=fd};return fsync(venus_scale012_process,&sync,&result);
}
static void venus_scale012_observe(const char *phase,unsigned index,int status) {
    if(index==0){
        if(!strcmp(phase,"source_uid"))venus_scale012_source_uid=(uint32_t)status;
        if(!strcmp(phase,"source_mode"))venus_scale012_source_mode=(uint32_t)status;
        if(!strcmp(phase,"source_size"))venus_scale012_source_size=(uint32_t)status;
    }
    if(status){
        if(!strcmp(phase,"source_validation"))venus_scale012_cache_failure_phase=3;
        if(!strcmp(phase,"rename"))venus_scale012_cache_failure_phase=4;
    }
    int error=venus_scale012_emit(phase,index,status);
    if(error&&!venus_scale012_journal_status)venus_scale012_journal_status=error;
}
static int venus_scale012_prepare_directory(proc_t p,uint64_t scratch) {
    struct stat64 root={0},dir={0};int32_t result=0;
    int error=venus_gestalt_stat(p,scratch,"/private/var",&root);if(error)return error;
    if((error=copyout(VENUS_GESTALT_BACKUP_DIRECTORY,scratch,sizeof(VENUS_GESTALT_BACKUP_DIRECTORY))))return error;
    struct mkdir_args create={.path=scratch,.mode=0700};error=mkdir(p,&create,&result);
    if(error&&error!=EEXIST)return error;
    if((error=venus_gestalt_stat(p,scratch,VENUS_GESTALT_BACKUP_DIRECTORY,&dir)))return error;
    if(!S_ISDIR(dir.st_mode)||dir.st_uid!=0||(dir.st_mode&07777)!=0700)return EPERM;
    if(dir.st_dev!=root.st_dev)return EXDEV;
    return venus_gestalt_sync_directory(p,scratch,"/private/var/db");
}
static void venus_scale012_refresh_after_policy(proc_t p,uint64_t scratch) {
    unsigned enabled=0;int32_t result=0;
    if(!PE_parse_boot_argn("venus-gestalt-refresh",&enabled,sizeof(enabled))||enabled!=1||venus_scale012_attempted)return;
    venus_scale012_attempted=1;
    if(native_owner_data_stage!=4||native_owner_data_status||native_owner_data_readonly){venus_scale012_journal_status=ENXIO;return;}
    int error=venus_scale012_prepare_directory(p,scratch);if(error){venus_scale012_journal_status=error;return;}
    if((error=copyout(venus_scale012_report,scratch,sizeof(venus_scale012_report)))){venus_scale012_journal_status=error;return;}
    struct open_args op={.path=scratch,.flags=O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,.mode=0644};
    if((error=open(p,&op,&result))){venus_scale012_journal_status=error;return;}
    venus_scale012_fd=result;venus_scale012_process=p;venus_scale012_scratch=scratch;venus_scale012_journal_status=0;
    error=venus_scale012_emit("begin",3,-1);
    if(!error){
        int directory_status=venus_gestalt_sync_directory(p,scratch,VENUS_GESTALT_BACKUP_DIRECTORY);
        venus_scale012_observe("journal_directory_sync",3,directory_status);
        struct fcntl_args full={.fd=venus_scale012_fd,.cmd=F_FULLFSYNC,.arg=0};
        venus_scale012_full_sync_status=sys_fcntl(p,&full,&result);
        venus_scale012_observe("journal_full_sync",3,venus_scale012_full_sync_status);
        int medium_status=native_ufs_store_sync()?0:EIO;
        venus_scale012_observe("journal_medium_sync",3,medium_status);
        // No extra telemetry failure is substituted for the cache transaction's own result.
        int cache_status=venus_boot_gestalt_cache(p,scratch);
        venus_scale012_observe("complete",3,cache_status);
        int final_directory=venus_gestalt_sync_directory(p,scratch,VENUS_GESTALT_BACKUP_DIRECTORY);
        venus_scale012_observe("final_directory_sync",3,final_directory);
        int final_medium=native_ufs_store_sync()?0:EIO;
        venus_scale012_observe("final_medium_sync",3,final_medium);
    }else venus_scale012_journal_status=error;
    struct close_args close_args={.fd=venus_scale012_fd};int closed=sys_close(p,&close_args,&result);
    if(closed&&!venus_scale012_journal_status)venus_scale012_journal_status=closed;venus_scale012_fd=-1;
    printf("VENUS scale012 journal=%d full=%d cache=%d moved=%x missing=%x\n",venus_scale012_journal_status,
        venus_scale012_full_sync_status,venus_gestalt_status,venus_gestalt_moved,venus_gestalt_missing);
}
#endif
