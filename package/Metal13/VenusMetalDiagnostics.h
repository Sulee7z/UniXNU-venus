// SPDX-License-Identifier: MIT
// Bounded post-launch diagnostic written from the Metal plugin's own process.
// A missing file is meaningful: launchd never reached the plugin.
#ifndef VENUS_METAL_DIAGNOSTICS_H
#define VENUS_METAL_DIAGNOSTICS_H
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <unistd.h>

static char venus_metal_diag_path[256]={0};
static int venus_metal_diag_tried=0;

static int venus_metal_diag_parent(const char *path) {
    char copy[256];
    if(!path || strlen(path)>=sizeof copy)return ENAMETOOLONG;
    strcpy(copy,path);
    for(char *p=copy+1;*p;++p)if(*p=='/') {
        *p=0;
        if(mkdir(copy,0700) && errno!=EEXIST)return errno;
        struct stat st;
        if(lstat(copy,&st))return errno;
        if(S_ISLNK(st.st_mode) || !S_ISDIR(st.st_mode))return EACCES;
        *p='/';
    }
    return 0;
}

#ifndef VENUS_METAL_DIAG_TEST
static const char *venus_metal_diag_target(void) {
    static const char *const candidates[]={
        "/private/var/db/venus-metal-040/native.jsonl",
        "/private/var/root/Library/Caches/com.apple.backboardd/venus-metal13/native.jsonl",
        "/private/var/mobile/Library/Caches/com.apple.backboardd/venus-metal13/native.jsonl",
        "/private/var/tmp/venus-metal13-native.jsonl",
        "/tmp/venus-metal13-native.jsonl",
    };
    if(venus_metal_diag_path[0])return venus_metal_diag_path;
    if(venus_metal_diag_tried)return NULL;
    venus_metal_diag_tried=1;
    for(unsigned i=0;i<sizeof candidates/sizeof candidates[0];++i) {
        if(venus_metal_diag_parent(candidates[i]))continue;
        int fd=open(candidates[i],O_WRONLY|O_APPEND|O_CREAT|O_NOFOLLOW,0600);
        if(fd<0)continue;
        struct stat st;
        int accepted=!fstat(fd,&st) && S_ISREG(st.st_mode) && st.st_uid==getuid();
        close(fd);
        if(accepted) {
            strncpy(venus_metal_diag_path,candidates[i],sizeof venus_metal_diag_path-1);
            return venus_metal_diag_path;
        }
    }
    return NULL;
}
#else
static const char *venus_metal_diag_target(void) {
    if(venus_metal_diag_path[0])return venus_metal_diag_path;
    if(venus_metal_diag_tried)return NULL;
    venus_metal_diag_tried=1;
    if(venus_metal_diag_parent(VENUS_METAL_DIAG_TEST))return NULL;
    strncpy(venus_metal_diag_path,VENUS_METAL_DIAG_TEST,sizeof venus_metal_diag_path-1);
    return venus_metal_diag_path;
}
#endif

static size_t venus_metal_diag_escape(char *out,size_t bytes,const char *text) {
    size_t used=0;
    if(!text)text="";
    for(const unsigned char *p=(const unsigned char *)text;*p && used+7<bytes;++p) {
        if(*p=='"' || *p=='\\') {
            out[used++]='\\';out[used++]=(char)*p;
        } else if(*p<0x20) {
            int n=snprintf(out+used,bytes-used,"\\u%04x",*p);
            if(n<0)break;
            used+=(size_t)n;
        } else out[used++]=(char)*p;
    }
    out[used]=0;
    return used;
}

static void venus_metal_diag(const char *stage,const char *detail) {
    const char *path=venus_metal_diag_target();
    if(!path)return;
    char phase[160],extra[384],line[640];
    venus_metal_diag_escape(phase,sizeof phase,stage);
    venus_metal_diag_escape(extra,sizeof extra,detail);
    struct timeval now={0,0};gettimeofday(&now,NULL);
    int length=snprintf(line,sizeof line,
        "{\"schema\":1,\"process\":\"%s\",\"pid\":%d,\"seconds\":%lld,\"stage\":\"%s\",\"detail\":\"%s\",\"errno\":%d}\n",
        getprogname(),getpid(),(long long)now.tv_sec,phase,extra,errno);
    if(length<=0 || (size_t)length>=sizeof line)return;
    int fd=open(path,O_WRONLY|O_APPEND|O_CREAT|O_NOFOLLOW,0600);
    if(fd<0)return;
    ssize_t written=write(fd,line,(size_t)length);
    if(written==length)fsync(fd);
    close(fd);
}
#endif
