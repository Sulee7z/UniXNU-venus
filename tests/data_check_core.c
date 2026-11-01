// SPDX-License-Identifier: MIT
// Real transaction core over a model separating file flush, directory entry,
// checkpoint submission and the medium fence. This is not an APFS emulator.
#include <assert.h>
#include <stdio.h>
#include "../package/boot-progress/BootDataCheckCore.h"
struct medium {
  char path[VdcPathBytes],data[64],durable[64],queued[64];
  size_t length,durable_length;
  int exists,durable_exists,opened,create_mode;
  unsigned opens,creates,writes,syncs,reads,closes,parent_syncs,full_syncs,transport_syncs;
  int file_synced,parent_synced,checkpoint_queued;
  int fail_write,fail_sync,fail_parent,fail_full,fail_transport,fail_read,fail_close,bad_meta,short_write,short_read;
};
static int open_file(void *ctx,const char *path,int create,int *fd) {
  struct medium *m=ctx;++m->opens;assert(!m->opened);
  if(create) {
    if(m->exists)return EEXIST;
    ++m->creates;m->exists=1;strcpy(m->path,path);m->length=0;
  } else if(!m->exists||strcmp(m->path,path))return ENOENT;
  m->opened=1;m->create_mode=create;*fd=3;return 0;
}
static int write_file(void *ctx,int fd,const void *data,size_t size,size_t *moved) {
  struct medium *m=ctx;assert(fd==3&&m->opened&&m->create_mode);++m->writes;
  if(m->fail_write)return EIO;
  assert(size<=sizeof(m->data));*moved=size-(m->short_write?1:0);
  memcpy(m->data,data,*moved);m->length=*moved;return 0;
}
static int read_file(void *ctx,int fd,void *data,size_t size,size_t *moved) {
  struct medium *m=ctx;assert(fd==3&&m->opened&&!m->create_mode);++m->reads;
  if(m->fail_read)return EIO;
  *moved=m->length<size?m->length:size;if(m->short_read&&*moved)--*moved;
  memcpy(data,m->data,*moved);return 0;
}
static int sync_file(void *ctx,int fd) {
  struct medium *m=ctx;assert(fd==3&&m->opened);++m->syncs;
  if(m->fail_sync)return EIO;
  m->file_synced=1;return 0;
}
static int sync_parent(void *ctx) {
  struct medium *m=ctx;++m->parent_syncs;
  assert(m->opened&&m->file_synced);if(m->fail_parent)return EIO;
  m->parent_synced=1;return 0;
}
static int full_sync(void *ctx,int fd) {
  struct medium *m=ctx;++m->full_syncs;assert(fd==3&&m->opened&&m->file_synced&&m->parent_synced);
  if(m->fail_full)return ENOTSUP;
  memcpy(m->queued,m->data,m->length);m->checkpoint_queued=1;return 0;
}
static int transport_sync(void *ctx) {
  struct medium *m=ctx;++m->transport_syncs;assert(m->checkpoint_queued);
  if(m->fail_transport)return EIO;
  memcpy(m->durable,m->queued,m->length);m->durable_length=m->length;m->durable_exists=m->exists;return 0;
}
static int size_file(void *ctx,int fd,uint64_t *size) {
  struct medium *m=ctx;assert(fd==3&&m->opened);
  if(m->bad_meta)return EPERM;*size=m->length;return 0;
}
static int close_file(void *ctx,int fd) {
  struct medium *m=ctx;assert(fd==3&&m->opened);++m->closes;m->opened=0;
  return m->fail_close?EIO:0;
}
static void reboot(struct medium *m) {
  assert(!m->opened);m->exists=m->durable_exists;m->length=m->durable_length;
  memcpy(m->data,m->durable,m->length);
}
static struct vdc_result run(struct medium *m,unsigned phase,const char *token) {
  struct vdc_ops ops={m,open_file,write_file,read_file,sync_file,size_file,close_file,0,sync_parent,full_sync,transport_sync};
  struct vdc_result r;vdc_run(&ops,phase,token,&r);assert(!m->opened);return r;
}
int main(void) {
  const char *token="0123456789abcdef0123456789abcdef";
  struct medium m={0};struct vdc_result r;
  r=run(&m,0,token);assert(r.error==EINVAL&&!m.opens);
  r=run(&m,3,token);assert(r.error==EINVAL&&!m.opens);
  r=run(&m,1,"../invalid");assert(r.error==EINVAL&&!m.opens);
  r=run(&m,1,"0123456789abcdef0123456789abcdeg");assert(r.error==EINVAL&&!m.opens);
  r=run(&m,1,token);assert(!r.error&&r.stage==VdcDone&&r.matched&&r.bytes==53);
  assert(m.creates==1&&m.writes==1&&m.syncs==1&&m.reads==1&&m.closes==2);
  assert(m.parent_syncs==1&&m.full_syncs==1&&m.transport_syncs==1);
  char expected[53],path[128];assert(!vdc_inputs(token,path,expected));
  assert(!memcmp(m.durable,expected,53));
  reboot(&m);unsigned writes=m.writes,syncs=m.syncs,creates=m.creates;
  r=run(&m,2,token);assert(!r.error&&r.stage==VdcDone&&r.matched);
  assert(m.writes==writes&&m.syncs==syncs&&m.creates==creates);
  assert(m.parent_syncs==1&&m.full_syncs==1&&m.transport_syncs==1);
  r=run(&m,1,token);assert(r.error==EEXIST&&m.writes==writes);
  r=run(&m,2,"1123456789abcdef0123456789abcdef");assert(r.error==ENOENT);
  struct medium bad=m;bad.data[0]^=1;r=run(&bad,2,token);assert(r.error==EINVAL&&!r.matched);
  bad=m;--bad.length;r=run(&bad,2,token);assert(r.error==EINVAL&&!r.matched);
  bad=m;bad.bad_meta=1;r=run(&bad,2,token);assert(r.error==EPERM);
  bad=m;bad.short_read=1;r=run(&bad,2,token);assert(r.error==EIO&&!r.matched);
  bad=m;bad.fail_read=1;r=run(&bad,2,token);assert(r.error==EIO&&!r.matched);
  bad=m;bad.fail_close=1;r=run(&bad,2,token);assert(r.error==EIO);
  for(unsigned i=0;i<7;++i) {
    struct medium fresh={0};
    if(i==0)fresh.fail_write=1;if(i==1)fresh.short_write=1;
    if(i==2)fresh.fail_sync=1;if(i==3)fresh.bad_meta=1;
    if(i==4)fresh.fail_parent=1;if(i==5)fresh.fail_full=1;if(i==6)fresh.fail_transport=1;
    r=run(&fresh,1,token);assert(r.error&&!r.matched);
    if(i==4)assert(r.stage==VdcParentSync&&fresh.full_syncs==0);
    if(i==5)assert(r.stage==VdcFullSync&&r.error==ENOTSUP&&fresh.transport_syncs==0);
    if(i==6)assert(r.stage==VdcTransportSync);
    reboot(&fresh);r=run(&fresh,2,token);assert(r.error==ENOENT);
  }
  assert(vdc_store_ready(1,2,2,2097152,59299519,0,0,0));
  assert(vdc_store_ready(1,2,3,2097152,59299519,0,0,0));
  assert(vdc_store_ready(2,2,2,2097152,59299519,0,0,0));
  assert(!vdc_store_ready(2,2,3,2097152,59299519,0,0,0));
  assert(!vdc_store_ready(1,1,2,2097152,59299519,0,0,0));
  assert(!vdc_store_ready(1,2,2,2097151,59299519,0,0,0));
  assert(!vdc_store_ready(1,2,2,2097152,59299520,0,0,0));
  assert(!vdc_store_ready(1,2,2,2097152,59299519,1,0,0));
  assert(!vdc_store_ready(1,2,2,2097152,59299519,0,1,0));
  assert(!vdc_store_ready(1,2,2,2097152,59299519,0,0,1));
  assert(vdc_same_device(4,0,0,0x1000005,0x1000005));
  assert(!vdc_same_device(4,0,0,0x1000005,0x1000004));
  assert(!vdc_same_device(3,0,0,0x1000005,0x1000005));
  assert(!vdc_same_device(4,1,0,0x1000005,0x1000005));
  assert(!vdc_same_device(4,0,1,0x1000005,0x1000005));
  assert(!vdc_same_device(4,0,0,UINT32_MAX,UINT32_MAX));
  // Show why same-boot reopen alone is insufficient in this model: old
  // file-only synchronization preserves the live file but not its checkpoint.
  struct medium old={0};int fd;char oldpath[128],content[53];size_t moved;
  assert(!vdc_inputs(token,oldpath,content));assert(!open_file(&old,oldpath,1,&fd));
  assert(!write_file(&old,fd,content,53,&moved)&&!sync_file(&old,fd)&&!close_file(&old,fd));
  assert(!open_file(&old,oldpath,0,&fd)&&!close_file(&old,fd));
  reboot(&old);assert(open_file(&old,oldpath,0,&fd)==ENOENT);
  puts("PASS: exclusive create, file/parent/full/medium sync, modeled reboot/readback, no phase2 writes, sync failure stages, device identity, token/metadata/short-I/O controls");
}
