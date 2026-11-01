// SPDX-License-Identifier: MIT
// Included from BootWatchdogPolicy.c after the writable Data mount. Uses the
// same init-process syscall context and reserved user scratch page as that hook.
#include <IOKit/IOLib.h>
#include "BootDataCheckCore.h"
extern uint32_t native_ufs_store_mode(void);
extern volatile uint32_t native_data_persist_state,native_data_persist_gpt,native_data_persist_gpt_after;
extern volatile uint64_t native_data_persist_pages,native_data_persist_first_lba,native_data_persist_errors;
extern volatile uint64_t native_data_persist_writes,native_data_persist_syncs,native_data_persist_present;
extern volatile int native_owner_data_status,native_owner_data_stage,native_owner_data_readonly;
extern volatile dev_t native_owner_data_device;
extern int native_ufs_store_sync(void);
volatile unsigned venus_data_check_phase,venus_data_check_stage,venus_data_check_matched;
volatile int venus_data_check_status=-1;
char venus_data_check_row[120];
char venus_data_check_detail[3][120];
static char data_check_token[34];
struct data_check_context {proc_t process;uint64_t scratch;int parent_fd;uint32_t data_dev,parent_dev,file_dev;
  uint64_t before_writes,before_syncs,before_present,after_file_writes,after_full_writes;
  int file_sync_rc,parent_sync_rc,full_sync_rc,transport_sync_rc;};
static void data_check_details(struct data_check_context *c) {
  snprintf(venus_data_check_detail[0],120,"DATA DEV mount=%x data=%x parent=%x file=%x stage=%d rc=%d ro=%d",
    (unsigned)native_owner_data_device,c->data_dev,c->parent_dev,c->file_dev,native_owner_data_stage,native_owner_data_status,native_owner_data_readonly);
  snprintf(venus_data_check_detail[1],120,"DATA IO w=%llu>%llu fs=%llu full=%llu runs=%llu>%llu err=%llu",
    c->before_writes,native_data_persist_writes,c->after_file_writes,c->after_full_writes,
    c->before_syncs,native_data_persist_syncs,native_data_persist_errors);
  snprintf(venus_data_check_detail[2],120,"DATA SYNC file=%d dir=%d full=%d ufs=%d present=%llu>%llu v=2",
    c->file_sync_rc,c->parent_sync_rc,c->full_sync_rc,c->transport_sync_rc,c->before_present,native_data_persist_present);
}
static void data_check_note(void *context,const struct vdc_result *r) {
  data_check_details(context);
  venus_data_check_stage=r->stage;venus_data_check_matched=r->matched;
  venus_data_check_status=r->error?r->error:(r->stage==VdcDone?0:EINPROGRESS);
  snprintf(venus_data_check_row,sizeof(venus_data_check_row),
    "DATA CHECK phase=%u step=%u rc=%d match=%u bytes=%u token=%.8s store=%u",
    r->phase,r->stage,venus_data_check_status,r->matched,r->bytes,data_check_token,native_data_persist_state);
}
static int data_check_open(void *context,const char *path,int create,int *fd) {
  struct data_check_context *c=context;int32_t result=0;
  static const char prefix[]="/private/var/db/";
  if(c->parent_fd<0||strncmp(path,prefix,sizeof(prefix)-1))return EINVAL;
  const char *name=path+sizeof(prefix)-1;if(strchr(name,'/')||!*name)return EINVAL;
  int error=copyout(name,c->scratch,strlen(name)+1);if(error)return error;
  struct openat_args a={.fd=c->parent_fd,.path=c->scratch,.flags=(create?O_WRONLY|O_CREAT|O_EXCL:O_RDONLY)|O_NOFOLLOW,.mode=0600};
  error=openat(c->process,&a,&result);if(!error)*fd=result;return error;
}
static int data_check_write(void *context,int fd,const void *src,size_t bytes,size_t *moved) {
  struct data_check_context *c=context;user_ssize_t result=0;
  if(bytes>0x1f0)return EINVAL;
  int error=copyout(src,c->scratch+0x200,bytes);if(error)return error;
  struct write_args a={.fd=fd,.cbuf=c->scratch+0x200,.nbyte=bytes};
  error=write(c->process,&a,&result);
  if(!error){if(result<0||(uint64_t)result>bytes)return EIO;*moved=(size_t)result;}return error;
}
static int data_check_read(void *context,int fd,void *dst,size_t bytes,size_t *moved) {
  struct data_check_context *c=context;user_ssize_t result=0;
  if(bytes>0x1f0)return EINVAL;
  struct read_args a={.fd=fd,.cbuf=c->scratch+0x200,.nbyte=bytes};
  int error=read(c->process,&a,&result);if(error)return error;
  if(result<0||(uint64_t)result>bytes)return EIO;
  *moved=(size_t)result;return copyin(c->scratch+0x200,dst,*moved);
}
static int data_check_sync(void *context,int fd) {
  struct data_check_context *c=context;int32_t result=0;
  struct fsync_args a={.fd=fd};c->file_sync_rc=fsync(c->process,&a,&result);
  c->after_file_writes=native_data_persist_writes;return c->file_sync_rc;
}
static int data_check_parent_sync(void *context) {
  struct data_check_context *c=context;int32_t result=0;
  struct fsync_args a={.fd=c->parent_fd};return c->parent_sync_rc=fsync(c->process,&a,&result);
}
static int data_check_full_sync(void *context,int fd) {
  struct data_check_context *c=context;int32_t result=0;
  struct fcntl_args a={.fd=fd,.cmd=F_FULLFSYNC,.arg=0};
  c->full_sync_rc=sys_fcntl(c->process,&a,&result);c->after_full_writes=native_data_persist_writes;
  return c->full_sync_rc;
}
static int data_check_transport_sync(void *context) {
  struct data_check_context *c=context;
  // Explicit final medium fence, separate from RamBlock's write-through claim.
  return c->transport_sync_rc=native_ufs_store_sync()?0:EIO;
}
static int data_check_size(void *context,int fd,uint64_t *bytes) {
  struct data_check_context *c=context;int32_t result=0;struct stat64 st={0};
  struct fstat64_args a={.fd=fd,.ub=c->scratch+0x800};
  int error=sys_fstat64(c->process,&a,&result);if(error)return error;
  if((error=copyin(a.ub,&st,sizeof(st))))return error;
  c->file_dev=(uint32_t)st.st_dev;
  if(!vdc_same_device(native_owner_data_stage,native_owner_data_status,native_owner_data_readonly,
       c->data_dev,c->file_dev)||c->file_dev!=c->parent_dev)return EXDEV;
  if(st.st_uid!=0||st.st_gid!=0||!S_ISREG(st.st_mode)||(st.st_mode&0777)!=0600||st.st_size<0)return EPERM;
  *bytes=(uint64_t)st.st_size;return 0;
}
static int data_check_close(void *context,int fd) {
  struct data_check_context *c=context;int32_t result=0;
  struct close_args a={.fd=fd};return sys_close(c->process,&a,&result);
}
static int data_check_directory(struct data_check_context *c,const char *path,int *fd,uint32_t *device) {
  int32_t result=0;
  int error=copyout(path,c->scratch,strlen(path)+1);if(error)return error;
  struct open_args a={.path=c->scratch,.flags=O_RDONLY|O_DIRECTORY|O_NOFOLLOW,.mode=0};
  if((error=open(c->process,&a,&result)))return error;
  *fd=result;
  struct stat64 st={0};struct fstat64_args sa={.fd=*fd,.ub=c->scratch+0x800};
  if((error=sys_fstat64(c->process,&sa,&result))||(error=copyin(sa.ub,&st,sizeof(st))))return error;
  *device=(uint32_t)st.st_dev;
  if(!S_ISDIR(st.st_mode)||st.st_uid!=0||st.st_gid!=0)return EPERM;
  return 0;
}
static int data_check_parent(struct data_check_context *c) {
  // st_dev is the filesystem's identity; it need not equal the block rdev.
  // The existing mount hook verified the APFS root's actual backing device.
  if(native_owner_data_device==NODEV || native_owner_data_stage!=4 || native_owner_data_status || native_owner_data_readonly)return ENXIO;
  int root_fd=-1,error=data_check_directory(c,"/private/var",&root_fd,&c->data_dev);
  if(root_fd>=0){int close_error=data_check_close(c,root_fd);if(!error)error=close_error;}
  if(error)return error;
  if((error=data_check_directory(c,"/private/var/db",&c->parent_fd,&c->parent_dev)))return error;
  return vdc_same_device(native_owner_data_stage,native_owner_data_status,native_owner_data_readonly,
         c->data_dev,c->parent_dev)?0:EXDEV;
}
static void venus_boot_data_check(proc_t process,uint64_t scratch) {
  unsigned phase=0;
  if(venus_data_check_phase||!PE_parse_boot_argn("venus-data-check",&phase,sizeof(phase))||!phase)return;
  venus_data_check_phase=phase;
  PE_parse_boot_argn("venus-data-token",data_check_token,sizeof(data_check_token));
  data_check_token[sizeof(data_check_token)-1]=0;
  struct data_check_context context={.process=process,.scratch=scratch,.parent_fd=-1,
    .data_dev=UINT32_MAX,.parent_dev=UINT32_MAX,.file_dev=UINT32_MAX,
    .before_writes=native_data_persist_writes,.before_syncs=native_data_persist_syncs,.before_present=native_data_persist_present,
    .file_sync_rc=-1,.parent_sync_rc=-1,.full_sync_rc=-1,.transport_sync_rc=-1};
  struct vdc_ops ops={&context,data_check_open,data_check_write,data_check_read,
                      data_check_sync,data_check_size,data_check_close,data_check_note,
                      data_check_parent_sync,data_check_full_sync,data_check_transport_sync};
  struct vdc_result result={.phase=phase,.stage=VdcInputs};
  if(!vdc_store_ready(phase,native_ufs_store_mode(),native_data_persist_state,
      native_data_persist_pages,native_data_persist_first_lba,native_data_persist_errors,
      native_data_persist_gpt,native_data_persist_gpt_after)) {
    result.error=ENXIO;data_check_note(&context,&result);
  } else {
    result.stage=VdcParent;data_check_note(&context,&result);
    result.error=data_check_parent(&context);
    if(!result.error)vdc_run(&ops,phase,data_check_token,&result);
    if(!result.error && native_data_persist_errors)result.error=EIO;
    if(!result.error && phase==1 && native_data_persist_writes<=context.before_writes){result.stage=VdcStoreWrites;result.error=EIO;}
  }
  if(context.parent_fd>=0){int error=data_check_close(&context,context.parent_fd);if(!result.error)result.error=error;}
  data_check_note(&context,&result);
  for(unsigned i=0;i<3;++i)printf("%s\n",venus_data_check_detail[i]);
  printf("%s\n",venus_data_check_row);
  // This explicit qualification image stops before launchd. Keep the result
  // visible and avoid unrelated user-space writes until the manual reboot.
  for(;;)IOSleep(1000);
}
