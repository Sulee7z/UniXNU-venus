// SPDX-License-Identifier: MIT
// Explicit one-boot refresh of the documented MobileGestalt cache locations.
// Keep each old file under an exclusive backup name; never replace a backup.
#ifndef VENUS_BOOT_GESTALT_CACHE_H
#define VENUS_BOOT_GESTALT_CACHE_H
#include <sys/stdio.h>
#ifndef VENUS_GESTALT_BACKUP_SUFFIX
#define VENUS_GESTALT_BACKUP_SUFFIX ".venus-scale-001.bak"
#endif
#ifndef VENUS_GESTALT_EVENT
#define VENUS_GESTALT_EVENT(phase,index,status) ((void)0)
#endif

volatile unsigned venus_gestalt_requested,venus_gestalt_moved,venus_gestalt_missing;
volatile int venus_gestalt_status=-1;
static const char *const venus_gestalt_paths[]={
 "/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist",
 "/private/var/mobile/Library/Preferences/com.apple.MobileGestalt.plist",
 "/private/var/mobile/Library/Preferences/com.apple.mobilegestalt.plist"
};
static int venus_gestalt_stat(proc_t p,uint64_t scratch,const char *path,struct stat64 *st) {
 int32_t result=0;int error=copyout(path,scratch,strlen(path)+1);
 if(error)return error;
 struct lstat64_args a={.path=scratch,.ub=scratch+0x800};
 if((error=lstat64(p,&a,&result)))return error;
 return copyin(a.ub,st,sizeof(*st));
}
static int venus_gestalt_sync_directory(proc_t p,uint64_t scratch,const char *path) {
 int32_t result=0;int error=copyout(path,scratch,strlen(path)+1);
 if(error)return error;
 struct open_args op={.path=scratch,.flags=O_RDONLY|O_DIRECTORY|O_NOFOLLOW,.mode=0};
 if((error=open(p,&op,&result)))return error;
 int fd=result;struct fsync_args sync_args={.fd=fd};error=fsync(p,&sync_args,&result);
 struct close_args close_args={.fd=fd};int closed=sys_close(p,&close_args,&result);
 return error?error:closed;
}
static int venus_gestalt_refresh(proc_t p,uint64_t scratch) {
 struct stat64 root={0};int error=0;int32_t result=0;
 if(native_owner_data_stage!=4 || native_owner_data_status || native_owner_data_readonly)return ENXIO;
 if((error=venus_gestalt_stat(p,scratch,"/private/var",&root)))return error;
 if(!S_ISDIR(root.st_mode))return ENOTDIR;
 for(unsigned i=0;i<3;++i) {
   const char *path=venus_gestalt_paths[i];struct stat64 st={0};
    error=venus_gestalt_stat(p,scratch,path,&st);
    VENUS_GESTALT_EVENT("source_stat",i,error);
    if(error==ENOENT){venus_gestalt_missing|=1u<<i;continue;}
    if(error)return error;
    VENUS_GESTALT_EVENT("source_uid",i,(int)st.st_uid);
    VENUS_GESTALT_EVENT("source_mode",i,(int)st.st_mode);
    VENUS_GESTALT_EVENT("source_size",i,(int)st.st_size);
   if(st.st_dev!=root.st_dev)return EXDEV;
   // The captured shared cache has the APFS nobody owner (-2) and no
   // permission bits. This is confined to that one exact path on owner Data;
   // preference files still require root/mobile ownership.
   int unowned_shared_cache=i==0 && st.st_uid==(uint32_t)-2 && (st.st_mode&07777)==0;
   if(!S_ISREG(st.st_mode) || (st.st_uid!=0 && st.st_uid!=501 && !unowned_shared_cache) ||
      st.st_size<0 || st.st_size>(16<<20)){VENUS_GESTALT_EVENT("source_validation",i,EPERM);return EPERM;}
   char backup[256],parent[256];
#ifdef VENUS_GESTALT_BACKUP_DIRECTORY
   int n=snprintf(backup,sizeof(backup),"%s/cache-%u.plist",VENUS_GESTALT_BACKUP_DIRECTORY,i);
#else
   int n=snprintf(backup,sizeof(backup),"%s%s",path,VENUS_GESTALT_BACKUP_SUFFIX);
#endif
    if(n<0 || (unsigned)n>=sizeof(backup))return ENAMETOOLONG;
    if((error=copyout(path,scratch,strlen(path)+1)))return error;
   if((error=copyout(backup,scratch+0x200,(unsigned)n+1)))return error;
   struct renameatx_np_args rename_args={.fromfd=AT_FDCWD,.from=scratch,
     .tofd=AT_FDCWD,.to=scratch+0x200,.flags=RENAME_EXCL|RENAME_NOFOLLOW_ANY};
   error=renameatx_np(p,&rename_args,&result);
   VENUS_GESTALT_EVENT("rename",i,error);
   if(error)return error;
   venus_gestalt_moved|=1u<<i;
   strlcpy(parent,path,sizeof(parent));char *slash=strrchr(parent,'/');
   if(!slash)return EINVAL;*slash=0;
   error=venus_gestalt_sync_directory(p,scratch,parent);
   VENUS_GESTALT_EVENT("source_directory_sync",i,error);
   if(error)return error;
#ifdef VENUS_GESTALT_BACKUP_DIRECTORY
   error=venus_gestalt_sync_directory(p,scratch,VENUS_GESTALT_BACKUP_DIRECTORY);
   VENUS_GESTALT_EVENT("backup_directory_sync",i,error);
   if(error)return error;
#endif
  }
  error=!venus_gestalt_moved || native_ufs_store_sync()?0:EIO;
  VENUS_GESTALT_EVENT("cache_medium_sync",3,error);
  return error;
}
static int venus_boot_gestalt_cache(proc_t p,uint64_t scratch) {
 unsigned requested=0;
 if(!PE_parse_boot_argn("venus-gestalt-refresh",&requested,sizeof(requested)) || requested!=1)return 0;
 if(venus_gestalt_requested)return venus_gestalt_status;
 venus_gestalt_requested=1;
 venus_gestalt_status=venus_gestalt_refresh(p,scratch);
  printf("VENUS MG refresh status=%d moved=%x missing=%x backup=%s\n",
    venus_gestalt_status,venus_gestalt_moved,venus_gestalt_missing,
#ifdef VENUS_GESTALT_BACKUP_DIRECTORY
    VENUS_GESTALT_BACKUP_DIRECTORY
#else
    VENUS_GESTALT_BACKUP_SUFFIX
#endif
  );
 return venus_gestalt_status;
}
#endif
