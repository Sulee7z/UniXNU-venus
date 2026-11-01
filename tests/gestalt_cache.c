// Test the actual opt-in cache transaction against a persistent namespace model.
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <fcntl.h>
typedef void *proc_t;
struct stat64 {uint32_t st_dev,st_uid;unsigned st_mode;int64_t st_size;};
struct lstat64_args {uint64_t path,ub;};
struct renameatx_np_args {int fromfd;uint64_t from;int tofd;uint64_t to;unsigned flags;};
struct open_args {uint64_t path;int flags,mode;};
struct fsync_args {int fd;};
struct close_args {int fd;};
static unsigned native_owner_data_stage=4,native_owner_data_status,native_owner_data_readonly;
static int requested,events,renames,closed,fail_rename,fail_fsync,fail_transport,bad_type,bad_device;
static unsigned exists_mask,backup_mask;
static unsigned char scratch[4096];
static int copyout(const void *p,uint64_t dst,size_t n){assert(dst>=(uintptr_t)scratch&&dst+n<=(uintptr_t)scratch+sizeof scratch);memcpy((void *)(uintptr_t)dst,p,n);return 0;}
static int copyin(uint64_t src,void *p,size_t n){assert(src>=(uintptr_t)scratch&&src+n<=(uintptr_t)scratch+sizeof scratch);memcpy(p,(void *)(uintptr_t)src,n);return 0;}
static size_t strlcpy(char *d,const char *s,size_t n){size_t z=strlen(s);if(n){size_t k=z<n-1?z:n-1;memcpy(d,s,k);d[k]=0;}return z;}
static int PE_parse_boot_argn(const char *key,void *v,int n){assert(!strcmp(key,"venus-gestalt-refresh")&&n==4);memcpy(v,&requested,4);return requested!=0;}
static int lstat64(proc_t,struct lstat64_args *,int32_t *);
static int renameatx_np(proc_t,struct renameatx_np_args *,int32_t *);
static int mock_open(proc_t,struct open_args *,int32_t *);
static int mock_fsync(proc_t,struct fsync_args *,int32_t *);
static int sys_close(proc_t,struct close_args *,int32_t *);
static int native_ufs_store_sync(void){++events;return !fail_transport;}
#define open mock_open
#define fsync mock_fsync
#include "BootGestaltCache.h"
static int index_of(const char *s){for(int i=0;i<3;++i)if(!strcmp(s,venus_gestalt_paths[i]))return i;assert(0);return -1;}
static int lstat64(proc_t p,struct lstat64_args *a,int32_t *r){
 (void)p;(void)r;++events;const char *s=(const char *)(uintptr_t)a->path;
 struct stat64 st={.st_dev=7,.st_uid=501,.st_mode=S_IFREG|0600,.st_size=13};
 if(!strcmp(s,"/private/var")){st.st_mode=S_IFDIR|0755;st.st_uid=0;}
 else {int i=index_of(s);if(!(exists_mask&(1u<<i)))return ENOENT;if(bad_type)st.st_mode=S_IFLNK|0777;if(bad_device)st.st_dev=8;}
 return copyout(&st,a->ub,sizeof(st));
}
static int renameatx_np(proc_t p,struct renameatx_np_args *a,int32_t *r){
 (void)p;(void)r;++events;
 assert(a->fromfd==AT_FDCWD&&a->tofd==AT_FDCWD&&a->flags==(RENAME_EXCL|RENAME_NOFOLLOW_ANY));
 const char *from=(const char *)(uintptr_t)a->from,*to=(const char *)(uintptr_t)a->to;
 int i=index_of(from);char want[256];snprintf(want,sizeof want,"%s%s",from,VENUS_GESTALT_BACKUP_SUFFIX);assert(!strcmp(to,want));
 if(fail_rename)return EIO;if(backup_mask&(1u<<i))return EEXIST;
 assert(exists_mask&(1u<<i));exists_mask&=~(1u<<i);backup_mask|=1u<<i;++renames;return 0;
}
static int mock_open(proc_t p,struct open_args *a,int32_t *r){(void)p;++events;assert(a->flags==(O_RDONLY|O_DIRECTORY|O_NOFOLLOW));*r=17;return 0;}
static int mock_fsync(proc_t p,struct fsync_args *a,int32_t *r){(void)p;(void)r;++events;assert(a->fd==17);return fail_fsync?EIO:0;}
static int sys_close(proc_t p,struct close_args *a,int32_t *r){(void)p;(void)r;++events;assert(a->fd==17);++closed;return 0;}
static void reset(void){requested=events=renames=closed=fail_rename=fail_fsync=fail_transport=bad_type=bad_device=0;exists_mask=7;backup_mask=0;native_owner_data_stage=4;native_owner_data_status=native_owner_data_readonly=0;venus_gestalt_requested=venus_gestalt_moved=venus_gestalt_missing=0;venus_gestalt_status=-1;}
static int run(void){return venus_boot_gestalt_cache(NULL,(uintptr_t)scratch);}
int main(void){
 reset();assert(run()==0&&events==0);requested=2;assert(run()==0&&events==0);
 reset();requested=1;assert(run()==0&&renames==3&&closed==3&&exists_mask==0&&backup_mask==7&&venus_gestalt_moved==7);
 int before=events;assert(run()==0&&events==before);
 // A later process can create fresh caches while old bytes/names remain saved.
 exists_mask=7;venus_gestalt_requested=0;assert(run()==EEXIST&&backup_mask==7&&exists_mask==7&&renames==3);
 reset();requested=1;exists_mask=0;assert(run()==0&&venus_gestalt_missing==7&&!renames);
 reset();requested=1;native_owner_data_readonly=1;assert(run()==ENXIO&&!events);
 reset();requested=1;native_owner_data_stage=2;assert(run()==ENXIO&&!events);
 reset();requested=1;bad_type=1;assert(run()==EPERM&&!renames);
 reset();requested=1;bad_device=1;assert(run()==EXDEV&&!renames);
 reset();requested=1;fail_rename=1;assert(run()==EIO&&exists_mask==7&&!backup_mask);
 reset();requested=1;fail_fsync=1;assert(run()==EIO&&renames==1&&closed==1&&venus_gestalt_moved==1);
 reset();requested=1;fail_transport=1;assert(run()==EIO&&renames==3&&backup_mask==7);
 puts("PASS: actual cache transaction: off gate, original files preserved, exclusive names, same-Data/type checks, missing files, one-shot, rename/fsync/UFS errors");
}
