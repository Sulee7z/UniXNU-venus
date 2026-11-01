// SPDX-License-Identifier: MIT
// Explicit pre-launchd readonly union view for one existing early boot task.
// Scratch +0x400/+0x500/+0x600 hold SystemOS environment: never overwrite them.
#ifndef MG_TASK_MOUNT_HOST_TEST
#include <sys/mount.h>
#include <sys/vnode.h>
#endif

extern volatile int native_bindfs_boot_mount;
volatile int venus_mg_task_mount_stage=0,venus_mg_task_mount_status=-1;

static void venus_mg_task_mount(proc_t p,uint64_t scratch) {
    int enabled=0,error;int32_t result=0;vnode_t vp=NULLVP;
    if(!PE_parse_boot_argn("venus-mg-task",&enabled,sizeof(enabled))||enabled!=1)return;
    static const char source[]="/private/var/ngpu/boot";
    static const char point[]="/usr/libexec";
    venus_mg_task_mount_stage=1;
    error=vnode_lookup(source,0,&vp,vfs_context_current());
    if(error)goto done;
    if(vnode_vtype(vp)!=VDIR){vnode_put(vp);error=ENOTDIR;goto done;}
    vnode_put(vp);vp=NULLVP;
    // Own shim and preserved original must exist before covering the task path.
    const char *paths[]={"/private/var/ngpu/boot/prng_seedctl","/private/var/ngpu/original/prng_seedctl"};
    for(unsigned i=0;i<2;++i){
        error=vnode_lookup(paths[i],0,&vp,vfs_context_current());
        if(error)goto done;
        struct vnode_attr attr;VATTR_INIT(&attr);VATTR_WANTED(&attr,va_mode);VATTR_WANTED(&attr,va_uid);
        error=vnode_getattr(vp,&attr,vfs_context_current());
        if(!error&&(vnode_vtype(vp)!=VREG||attr.va_uid!=0||(attr.va_mode&07777)!=0755))error=EINVAL;
        vnode_put(vp);vp=NULLVP;if(error)goto done;
    }
    venus_mg_task_mount_stage=2;
    struct mount_args request={.type=scratch+0xa00,.path=scratch+0xa20,
        .flags=MNT_RDONLY|MNT_UNION,.data=scratch+0xb00};
    if((error=copyout("bindfs",request.type,7))||(error=copyout(point,request.path,sizeof(point)))||
       (error=copyout(source,request.data,sizeof(source))))goto done;
    native_bindfs_boot_mount=1;error=mount(p,&request,&result);native_bindfs_boot_mount=0;
    if(error)goto done;
    venus_mg_task_mount_stage=3;
    error=vnode_lookup("/usr/libexec/launchd_cache_loader",0,&vp,vfs_context_current());
    if(error)goto done;
    vnode_put(vp);vp=NULLVP;venus_mg_task_mount_stage=4;
    error=vnode_lookup("/usr/libexec/prng_seedctl",0,&vp,vfs_context_current());
    if(!error){vnode_put(vp);vp=NULLVP;venus_mg_task_mount_stage=5;}
done:
    venus_mg_task_mount_status=error;
    printf("venus MG boot-task union stage=%d status=%d\n",venus_mg_task_mount_stage,error);
}
