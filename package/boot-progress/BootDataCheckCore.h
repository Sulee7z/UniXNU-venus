// SPDX-License-Identifier: MIT
// Bounded, opt-in file test: exclusive create/file+directory sync/fullsync/reopen, followed
// by a separate boot's read-only verification. Caller supplies the filesystem.
#ifndef VENUS_BOOT_DATA_CHECK_CORE_H
#define VENUS_BOOT_DATA_CHECK_CORE_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <sys/errno.h>

enum { VdcTokenBytes=32, VdcPathBytes=128, VdcContentBytes=53 };
enum { VdcInputs=1,VdcCreate,VdcWrite,VdcSync,VdcCloseWrite,VdcOpenRead,VdcStat,VdcRead,VdcCompare,VdcCloseRead,VdcDone };
// Keep the old stage numbers stable for retained photographs.
enum { VdcParent=12,VdcParentSync,VdcFullSync,VdcTransportSync,VdcStoreWrites };
#define VDC_SYNC_CONTRACT 2
struct vdc_result { unsigned phase,stage,matched,bytes; int error; };
struct vdc_ops {
  void *context;
  int (*open)(void *,const char *,int,int *); // create!=0: exclusive new file
  int (*write)(void *,int,const void *,size_t,size_t *);
  int (*read)(void *,int,void *,size_t,size_t *);
  int (*sync)(void *,int);
  int (*size)(void *,int,uint64_t *); // also verifies regular/root-owned/0600
  int (*close)(void *,int);
  void (*note)(void *,const struct vdc_result *);
  int (*sync_parent)(void *);
  int (*full_sync)(void *,int);
  int (*transport_sync)(void *);
};
static int vdc_inputs(const char *token,char path[VdcPathBytes],char content[VdcContentBytes]) {
  if(!token || strnlen(token,VdcTokenBytes+1)!=VdcTokenBytes)return EINVAL;
  for(unsigned i=0;i<VdcTokenBytes;++i)
    if(!((token[i]>='0'&&token[i]<='9')||(token[i]>='a'&&token[i]<='f')))return EINVAL;
  static const char prefix[]="/private/var/db/venus-data-check-",suffix[]=".bin";
  static const char head[]="VENUS-DATA-CHECK-v1\n";
  _Static_assert(sizeof(head)-1+VdcTokenBytes+1==VdcContentBytes,"Marker format");
  _Static_assert(sizeof(prefix)-1+VdcTokenBytes+sizeof(suffix)<=VdcPathBytes,"Path bound");
  memcpy(path,prefix,sizeof(prefix)-1);
  memcpy(path+sizeof(prefix)-1,token,VdcTokenBytes);
  memcpy(path+sizeof(prefix)-1+VdcTokenBytes,suffix,sizeof(suffix));
  memcpy(content,head,sizeof(head)-1);
  memcpy(content+sizeof(head)-1,token,VdcTokenBytes);
  content[VdcContentBytes-1]='\n';
  return 0;
}
static int vdc_store_ready(unsigned phase,unsigned mode,unsigned state,uint64_t pages,
                           uint64_t first,uint64_t errors,unsigned gpt,unsigned after) {
  // Same 8 GiB seed/window already verified by the Android metadata reader.
  return (phase==1||phase==2) && mode==2 && (state==2||(phase==1&&state==3)) &&
    pages==2097152ULL && first==59299519ULL && !errors && !gpt && !after;
}
static int vdc_same_device(unsigned stage,int status,int readonly,uint32_t expected,uint32_t actual) {
  return stage==4 && !status && !readonly && expected!=UINT32_MAX && actual==expected;
}
static void vdc_step(const struct vdc_ops *ops,struct vdc_result *r,unsigned stage) {
  r->stage=stage;if(ops->note)ops->note(ops->context,r);
}
static void vdc_run(const struct vdc_ops *ops,unsigned phase,const char *token,struct vdc_result *r) {
  char path[VdcPathBytes]={0},expected[VdcContentBytes],actual[VdcContentBytes];
  int fd=-1;size_t moved=0;uint64_t size=0;
  memset(r,0,sizeof(*r));r->phase=phase;
  vdc_step(ops,r,VdcInputs);
  if((phase!=1&&phase!=2)||(r->error=vdc_inputs(token,path,expected))) {r->error=EINVAL;goto done;}
  if(phase==1 && (!ops->sync_parent||!ops->full_sync||!ops->transport_sync)){r->error=EINVAL;goto done;}
  if(phase==1) {
    vdc_step(ops,r,VdcCreate);
    if((r->error=ops->open(ops->context,path,1,&fd)))goto done;
    // Newly created file must still have the expected kind, owner and size.
    if((r->error=ops->size(ops->context,fd,&size)))goto done;
    if(size){r->error=EINVAL;goto done;}
    vdc_step(ops,r,VdcWrite);
    if((r->error=ops->write(ops->context,fd,expected,sizeof(expected),&moved)))goto done;
    if(moved!=sizeof(expected)){r->error=EIO;goto done;}
    vdc_step(ops,r,VdcSync);
    if((r->error=ops->sync(ops->context,fd)))goto done;
    vdc_step(ops,r,VdcParentSync);
    if((r->error=ops->sync_parent(ops->context)))goto done;
    vdc_step(ops,r,VdcFullSync);
    if((r->error=ops->full_sync(ops->context,fd)))goto done;
    vdc_step(ops,r,VdcTransportSync);
    if((r->error=ops->transport_sync(ops->context)))goto done;
    vdc_step(ops,r,VdcCloseWrite);
    r->error=ops->close(ops->context,fd);fd=-1;
    if(r->error)goto done;
  }
  vdc_step(ops,r,VdcOpenRead);
  if((r->error=ops->open(ops->context,path,0,&fd)))goto done;
  vdc_step(ops,r,VdcStat);
  if((r->error=ops->size(ops->context,fd,&size)))goto done;
  if(size!=sizeof(expected)){r->error=EINVAL;goto done;}
  vdc_step(ops,r,VdcRead);
  if((r->error=ops->read(ops->context,fd,actual,sizeof(actual),&moved)))goto done;
  if(moved!=sizeof(actual)){r->error=EIO;goto done;}
  r->bytes=(unsigned)moved;
  vdc_step(ops,r,VdcCompare);
  if(memcmp(actual,expected,sizeof(actual))){r->error=EINVAL;goto done;}
  r->matched=1;
  vdc_step(ops,r,VdcCloseRead);
  r->error=ops->close(ops->context,fd);fd=-1;
  if(!r->error)vdc_step(ops,r,VdcDone);
done:
  if(fd>=0){int error=ops->close(ops->context,fd);if(!r->error)r->error=error;}
  if(ops->note)ops->note(ops->context,r);
}
#endif
