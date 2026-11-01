#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef void *proc_t;
typedef struct node{int type;}*vnode_t;
struct node node;
#define NULLVP NULL
#define VDIR 2
#define VREG 1
#define MNT_RDONLY 1
#define MNT_UNION 32
struct vnode_attr{int va_mode,va_uid;};
#define VATTR_INIT(a) memset(a,0,sizeof(*(a)))
#define VATTR_WANTED(a,b) ((void)(a))
struct mount_args{uint64_t type,path;int flags;uint64_t data;};
volatile int native_bindfs_boot_mount;
int selector=1,failure=0,calls=0,mounts=0;
unsigned char scratch[4096];
int PE_parse_boot_argn(const char *name,void *value,int size){(void)name;(void)size;*(int*)value=selector;return selector!=0;}
void *vfs_context_current(void){return NULL;}
int vnode_lookup(const char *path,int flags,vnode_t *vp,void *context){
    (void)flags;(void)context;calls++;
    if((failure==1&&strcmp(path,"/private/var/ngpu/boot")==0)||
       (failure==5&&strcmp(path,"/usr/libexec/launchd_cache_loader")==0)||
       (failure==6&&strcmp(path,"/usr/libexec/prng_seedctl")==0))return ENOENT;
    node.type=strcmp(path,"/private/var/ngpu/boot")==0?VDIR:VREG;*vp=&node;return 0;
}
void vnode_put(vnode_t vp){(void)vp;}
int vnode_vtype(vnode_t vp){return vp->type;}
int vnode_getattr(vnode_t vp,struct vnode_attr *attr,void *ctx){(void)vp;(void)ctx;attr->va_mode=failure==2?0644:0755;attr->va_uid=0;return 0;}
int copyout(const void *data,uint64_t destination,size_t size){
    if(failure==3)return EFAULT;
    if(destination<(uint64_t)scratch+0xa00||destination+size>(uint64_t)scratch+0xc00)abort();
    memcpy((void*)destination,data,size);return 0;
}
int mount(proc_t p,struct mount_args *args,int32_t *result){
    (void)p;(void)result;mounts++;
    if(native_bindfs_boot_mount!=1||args->flags!=(MNT_RDONLY|MNT_UNION)||
       strcmp((char*)args->type,"bindfs")||strcmp((char*)args->path,"/usr/libexec")||
       strcmp((char*)args->data,"/private/var/ngpu/boot"))abort();
    return failure==4?EPERM:0;
}
#define MG_TASK_MOUNT_HOST_TEST 1
#include "MGTaskMount.h"
int main(void){
    for(int s=0;s<=2;++s){selector=s;failure=0;calls=mounts=0;venus_mg_task_mount(NULL,(uint64_t)scratch);
        if(s!=1&&(calls||mounts))abort();}
    selector=1;
    for(int f=0;f<=6;++f){
        memset(scratch,0xa5,sizeof(scratch));failure=f;calls=mounts=0;
        venus_mg_task_mount(NULL,(uint64_t)scratch);
        for(int i=0x400;i<0x700;++i)if(scratch[i]!=0xa5)abort();
        if(native_bindfs_boot_mount||(!f&&(venus_mg_task_mount_stage!=5||venus_mg_task_mount_status)))abort();
        if(f&&venus_mg_task_mount_status==0)abort();
    }
    puts("PASS: actual mount helper gates, scratch preservation, readonly union and every failure boundary");return 0;
}
