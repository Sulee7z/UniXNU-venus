// SPDX-License-Identifier: MIT
#include <assert.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/types.h>
#include "../package/Metal13/VenusMetalCache.h"

int main(int argc,char **argv) {
    assert(argc==2);
    char path[1024],other[1024],small[8],prefix[2048];
    assert(venus_metal_cache_path(NULL,0,argv[1])==EINVAL);
    assert(venus_metal_cache_path(path,sizeof path,NULL)==EINVAL && !path[0]);
    assert(venus_metal_cache_path(small,sizeof small,argv[1])==ENAMETOOLONG && !small[0]);
    memset(prefix,'x',sizeof prefix-1);prefix[sizeof prefix-1]=0;
    assert(venus_metal_cache_path(path,sizeof path,prefix)==ENAMETOOLONG && !path[0]);
    assert(!venus_metal_cache_path(path,sizeof path,argv[1]));
    assert(!venus_metal_cache_prepare(path));
    assert(!venus_metal_cache_prepare(path));
    struct stat st;assert(!lstat(path,&st) && S_ISDIR(st.st_mode) && (st.st_mode&0777)==0700);
    assert(!chmod(path,0755));assert(venus_metal_cache_prepare(path)==EACCES);
    assert(!chmod(path,0500));assert(venus_metal_cache_prepare(path)==EACCES);
    assert(!chmod(path,0700));assert(!venus_metal_cache_prepare(path));
    assert(snprintf(other,sizeof other,"%s/file",argv[1])>0);
    int fd=open(other,O_CREAT|O_EXCL|O_WRONLY,0600);assert(fd>=0);
    assert(write(fd,"retained",8)==8 && !close(fd));
    assert(venus_metal_cache_prepare(other)==EACCES);
    assert(!lstat(other,&st) && S_ISREG(st.st_mode) && st.st_size==8);
    assert(snprintf(other,sizeof other,"%s/symlink",argv[1])>0);
    assert(!symlink(path,other));assert(venus_metal_cache_prepare(other)==EACCES);
    assert(!lstat(other,&st) && S_ISLNK(st.st_mode));
    assert(snprintf(other,sizeof other,"%s/missing/child",argv[1])>0);
    assert(venus_metal_cache_prepare(other)==ENOENT);
    if(getuid()==0) {
        assert(!chown(path,1,1));assert(venus_metal_cache_prepare(path)==EACCES);
        assert(!chown(path,0,0));
    }
    assert(!venus_metal_cache_prepare(path));
}
