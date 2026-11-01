// SPDX-License-Identifier: MIT
#ifndef VENUS_METAL_CACHE_H
#define VENUS_METAL_CACHE_H
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static inline int venus_metal_cache_path(char *out,size_t bytes,const char *prefix) {
    if(!out || !bytes)return EINVAL;
    out[0]=0;
    if(!prefix || !prefix[0])return EINVAL;
    int n=snprintf(out,bytes,"%s%svenus-metal13",prefix,prefix[strlen(prefix)-1]=='/'?"":"/");
    if(n<0 || (size_t)n>=bytes){out[0]=0;return ENAMETOOLONG;}
    return 0;
}

static inline int venus_metal_cache_prepare(const char *path) {
    if(!path || !path[0])return EINVAL;
    if(mkdir(path,0700) && errno!=EEXIST)return errno;
    struct stat st;
    if(lstat(path,&st))return errno;
    if(!S_ISDIR(st.st_mode) || st.st_uid!=getuid() || (st.st_mode&077) ||
       (st.st_mode&(S_IWUSR|S_IXUSR))!=(S_IWUSR|S_IXUSR))return EACCES;
    if(access(path,W_OK|X_OK))return errno;
    return 0;
}
#endif
