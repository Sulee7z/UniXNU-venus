// Production cache/journal transaction under a persistent namespace model.
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <fcntl.h>
typedef void *proc_t;
typedef long user_ssize_t;
struct stat64{uint32_t st_dev,st_uid;unsigned st_mode;int64_t st_size;};
struct lstat64_args{uint64_t path,ub;};
struct renameatx_np_args{int fromfd;uint64_t from;int tofd;uint64_t to;unsigned flags;};
struct open_args{uint64_t path;int flags,mode;};
struct fsync_args{int fd;};struct close_args{int fd;};
struct write_args{int fd;uint64_t cbuf;unsigned nbyte;};
struct fcntl_args{int fd,cmd;uint64_t arg;};
#ifdef SCALE_REFRESH_TEST_012
struct mkdir_args{uint64_t path;int mode;};
static int directory_exists,bad_directory;
static int mock_mkdir(proc_t,struct mkdir_args*,int32_t*);
#define mkdir mock_mkdir
#endif
#ifndef F_FULLFSYNC
#define F_FULLFSYNC 51
#endif
#ifndef RENAME_EXCL
#define RENAME_EXCL 4
#define RENAME_NOFOLLOW_ANY 128
#endif
static unsigned native_owner_data_stage=4,native_owner_data_status,native_owner_data_readonly;
static int requested,events,renames,exists_mask,backup_mask,journal_exists;
static int unowned_cache,bad_unowned_cache;
static int fail_rename,fail_write,fail_fsync,fail_fullsync,fail_medium_after,medium_calls;
static char journal[8192];static unsigned journal_length;static unsigned char scratch[4096];
static int copyout(const void *p,uint64_t dst,size_t n){assert(dst>=(uintptr_t)scratch&&dst+n<=(uintptr_t)scratch+sizeof scratch);memcpy((void*)dst,p,n);return 0;}
static int copyin(uint64_t src,void *p,size_t n){assert(src>=(uintptr_t)scratch&&src+n<=(uintptr_t)scratch+sizeof scratch);memcpy(p,(void*)src,n);return 0;}
static size_t strlcpy(char *dst,const char *src,size_t n){size_t size=strlen(src);if(n){size_t take=size<n-1?size:n-1;memcpy(dst,src,take);dst[take]=0;}return size;}
static int PE_parse_boot_argn(const char *key,void *value,int size){assert(!strcmp(key,"venus-gestalt-refresh")&&size==4);memcpy(value,&requested,4);return requested!=0;}
static int lstat64(proc_t,struct lstat64_args*,int32_t*);
static int renameatx_np(proc_t,struct renameatx_np_args*,int32_t*);
static int mock_open(proc_t,struct open_args*,int32_t*);
static int mock_fsync(proc_t,struct fsync_args*,int32_t*);
static int sys_close(proc_t,struct close_args*,int32_t*);
static int sys_fcntl(proc_t,struct fcntl_args*,int32_t*);
static int mock_write(proc_t,struct write_args*,user_ssize_t*);
static int native_ufs_store_sync(void){events++;medium_calls++;return !fail_medium_after||medium_calls<fail_medium_after;}
#define open mock_open
#define fsync mock_fsync
#define write mock_write
#ifdef SCALE_REFRESH_TEST_012
#include "BootScaleRefresh012.h"
#else
#include "BootScaleRefresh011.h"
#endif
static int index_of(const char *path){for(int i=0;i<3;++i)if(!strcmp(path,venus_gestalt_paths[i]))return i;assert(0);return -1;}
static int lstat64(proc_t p,struct lstat64_args *args,int32_t *result){
    (void)p;(void)result;events++;const char *path=(char*)args->path;
    struct stat64 st={.st_dev=7,.st_uid=501,.st_mode=S_IFREG|0600,.st_size=7477};
    if(!strcmp(path,"/private/var")){st.st_mode=S_IFDIR|0755;st.st_uid=0;}
#ifdef SCALE_REFRESH_TEST_012
    else if(!strcmp(path,VENUS_GESTALT_BACKUP_DIRECTORY)){
        if(!directory_exists)return ENOENT;st.st_mode=S_IFDIR|0700;st.st_uid=bad_directory?501:0;
    }
#endif
    else if(!(exists_mask&(1<<index_of(path))))return ENOENT;
    if((unowned_cache==1&&!strcmp(path,venus_gestalt_paths[0]))||(unowned_cache==2&&!strcmp(path,venus_gestalt_paths[1]))){st.st_uid=(uint32_t)-2;st.st_mode=S_IFREG|(bad_unowned_cache?0600:0);}
    return copyout(&st,args->ub,sizeof(st));
}
static int renameatx_np(proc_t p,struct renameatx_np_args *args,int32_t *result){
    (void)p;(void)result;events++;assert(args->flags==(RENAME_EXCL|RENAME_NOFOLLOW_ANY));
    int index=index_of((char*)args->from);char expected[256];
#ifdef SCALE_REFRESH_TEST_012
    snprintf(expected,sizeof(expected),"%s/cache-%u.plist",VENUS_GESTALT_BACKUP_DIRECTORY,index);
#else
    snprintf(expected,sizeof(expected),"%s.venus-scale-011.bak",(char*)args->from);
#endif
    assert(!strcmp((char*)args->to,expected));
    if(fail_rename)return EIO;if(backup_mask&(1<<index))return EEXIST;
    exists_mask&=~(1<<index);backup_mask|=1<<index;renames++;return 0;
}
static int mock_open(proc_t p,struct open_args *args,int32_t *result){
    (void)p;events++;
    if(args->flags==(O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW)){
#ifdef SCALE_REFRESH_TEST_012
        assert(!strcmp((char*)args->path,venus_scale012_report)&&args->mode==0644);
#else
        assert(!strcmp((char*)args->path,venus_scale011_report)&&args->mode==0644);
#endif
        if(journal_exists)return EEXIST;journal_exists=1;*result=21;return 0;
    }
    assert(args->flags==(O_RDONLY|O_DIRECTORY|O_NOFOLLOW));*result=17;return 0;
}
static int mock_fsync(proc_t p,struct fsync_args *args,int32_t *result){(void)p;(void)result;events++;assert(args->fd==17||args->fd==21);return fail_fsync?EIO:0;}
static int sys_close(proc_t p,struct close_args *args,int32_t *result){(void)p;(void)result;events++;assert(args->fd==17||args->fd==21);return 0;}
static int sys_fcntl(proc_t p,struct fcntl_args *args,int32_t *result){(void)p;(void)result;events++;assert(args->fd==21&&args->cmd==F_FULLFSYNC);return fail_fullsync?EIO:0;}
static int mock_write(proc_t p,struct write_args *args,user_ssize_t *written){
    (void)p;events++;assert(args->fd==21&&args->nbyte<0x200);
    if(fail_write)return EIO;assert(journal_length+args->nbyte<sizeof(journal));
    memcpy(journal+journal_length,(void*)args->cbuf,args->nbyte);journal_length+=args->nbyte;journal[journal_length]=0;*written=args->nbyte;return 0;
}
static void reset(void){
    requested=events=renames=backup_mask=journal_exists=unowned_cache=bad_unowned_cache=fail_rename=fail_write=fail_fsync=fail_fullsync=fail_medium_after=medium_calls=journal_length=0;
    exists_mask=1;native_owner_data_stage=4;native_owner_data_status=native_owner_data_readonly=0;
    venus_gestalt_requested=venus_gestalt_moved=venus_gestalt_missing=0;venus_gestalt_status=-1;
#ifdef SCALE_REFRESH_TEST_012
    directory_exists=bad_directory=venus_scale012_attempted=0;
    venus_scale012_journal_status=venus_scale012_full_sync_status=-1;venus_scale012_fd=-1;
#else
    venus_scale011_attempted=0;venus_scale011_journal_status=-1;
#endif
    journal[0]=0;memset(scratch,0xa5,sizeof(scratch));
}
static void run(void){
#ifdef SCALE_REFRESH_TEST_012
    venus_scale012_refresh_after_policy(NULL,(uintptr_t)scratch);
#else
    venus_scale011_refresh_after_policy(NULL,(uintptr_t)scratch);
#endif
    for(unsigned i=0x400;i<0x700;++i)assert(scratch[i]==0xa5);
}
#ifdef SCALE_REFRESH_TEST_012
static int mock_mkdir(proc_t p,struct mkdir_args *args,int32_t *result){
    (void)p;(void)result;events++;assert(!strcmp((char*)args->path,VENUS_GESTALT_BACKUP_DIRECTORY)&&args->mode==0700);
    if(directory_exists)return EEXIST;directory_exists=1;return 0;
}
#endif
int main(void){
#ifdef SCALE_REFRESH_TEST_012
    reset();run();assert(!events);requested=2;run();assert(!events);
    reset();requested=1;run();assert(renames==1&&backup_mask==1&&exists_mask==0&&venus_gestalt_missing==6&&!venus_gestalt_status);
    assert(strstr(journal,"\"phase\":\"complete\",\"index\":3,\"status\":0"));int before=events;run();assert(events==before);
    venus_scale012_attempted=venus_gestalt_requested=0;exists_mask=1;run();assert(renames==1&&exists_mask==1&&venus_scale012_journal_status==EEXIST);
    reset();requested=1;fail_fullsync=1;run();assert(renames==1&&venus_scale012_full_sync_status==EIO&&venus_gestalt_status==0&&strstr(journal,"\"phase\":\"journal_full_sync\",\"index\":3,\"status\":5"));
    reset();requested=unowned_cache=1;run();assert(renames==1&&venus_gestalt_status==0);
    reset();requested=unowned_cache=bad_unowned_cache=1;run();assert(!renames&&venus_gestalt_status==EPERM);
    reset();requested=1;unowned_cache=exists_mask=2;run();assert(!renames&&venus_gestalt_status==EPERM);
    reset();requested=1;fail_medium_after=1;run();assert(renames==1&&backup_mask==1&&venus_gestalt_status==EIO&&strstr(journal,"\"phase\":\"cache_medium_sync\",\"index\":3,\"status\":5"));
    reset();requested=1;backup_mask=1;run();assert(!renames&&exists_mask==1&&venus_gestalt_status==EEXIST);
    reset();requested=1;fail_rename=1;run();assert(!renames&&exists_mask==1&&venus_gestalt_status==EIO);
    reset();requested=1;fail_write=1;run();assert(!renames&&exists_mask==1&&venus_scale012_journal_status==EIO);
    reset();requested=1;fail_fsync=1;run();assert(!renames&&exists_mask==1);
    reset();requested=1;directory_exists=bad_directory=1;run();assert(!renames&&!journal_exists&&venus_scale012_journal_status==EPERM);
    reset();requested=1;native_owner_data_readonly=1;run();assert(!events&&!renames);
    puts("PASS: actual012 protected journal/backups, canonical transaction independent of extra FULLFSYNC, real errors retained, exclusive repeat refusal, env preservation");
#else
    reset();run();assert(!events);requested=2;run();assert(!events);
    reset();requested=1;run();assert(renames==1&&backup_mask==1&&exists_mask==0&&venus_gestalt_missing==6&&!venus_scale011_journal_status);
    assert(strstr(journal,"\"phase\":\"begin\"")&&strstr(journal,"\"phase\":\"complete\",\"status\":0"));int before=events;run();assert(events==before);
    venus_scale011_attempted=0;venus_gestalt_requested=0;exists_mask=1;run();assert(renames==1&&exists_mask==1&&backup_mask==1&&venus_scale011_journal_status==EEXIST);
    reset();requested=1;backup_mask=1;run();assert(!renames&&exists_mask==1&&strstr(journal,"\"status\":17"));
    reset();requested=1;fail_rename=1;run();assert(!renames&&exists_mask==1&&strstr(journal,"\"phase\":\"complete\",\"status\":5"));
    reset();requested=1;fail_write=1;run();assert(!renames&&exists_mask==1&&venus_scale011_journal_status==EIO);
    reset();requested=1;fail_fsync=1;run();assert(!renames&&exists_mask==1&&venus_scale011_journal_status==EIO);
    reset();requested=1;fail_fullsync=1;run();assert(!renames&&exists_mask==1&&venus_scale011_journal_status==EIO);
    reset();requested=1;fail_medium_after=2;run();assert(renames==1&&backup_mask==1&&strstr(journal,"\"phase\":\"complete\",\"status\":5"));
    reset();requested=1;native_owner_data_readonly=1;run();assert(!events&&!renames);
    puts("PASS: actual011 journal/cache code: gates, exclusive backups, current1/6 masks, durable begin before rename, failures, repeated boot refusal, env preservation");
#endif
    return 0;
}
