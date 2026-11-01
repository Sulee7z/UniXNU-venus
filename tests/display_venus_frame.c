// SPDX-License-Identifier: MIT
// Real CPU copy core at Venus panel dimensions; all buffers are host memory.
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "NativeLegacyRequest.h"
int main(void) {
    const unsigned width=1440,height=3200;
    const size_t src_stride=width*4+64,dst_stride=width*4;
    const size_t src_bytes=src_stride*height,dst_bytes=dst_stride*height;
    unsigned char *src=malloc(src_bytes),*dst=malloc(dst_bytes+64);
    assert(src&&dst);memset(src,0xa5,src_bytes);memset(dst,0xcc,dst_bytes+64);
    for(unsigned y=0;y<height;y++)for(unsigned x=0;x<width;x++) {
        unsigned char *p=src+y*src_stride+x*4;
        p[0]=(unsigned char)x;p[1]=(unsigned char)y;p[2]=(unsigned char)(x^y);p[3]=0xff;
    }
    assert(native_legacy_copy_pixels(dst,dst_bytes,dst_stride,src,src_bytes,src_stride,width,height));
    for(unsigned y=0;y<height;y++)for(unsigned x=0;x<width;x++) {
        const unsigned char *p=dst+y*dst_stride+x*4;
        assert(p[0]==(unsigned char)x&&p[1]==(unsigned char)y&&p[2]==(unsigned char)(x^y)&&p[3]==0xff);
    }
    for(unsigned i=0;i<64;i++)assert(dst[dst_bytes+i]==0xcc);
    assert(!native_legacy_copy_pixels(dst,dst_bytes-1,dst_stride,src,src_bytes,src_stride,width,height));
    assert(!native_legacy_copy_pixels(dst,dst_bytes,dst_stride-1,src,src_bytes,src_stride,width,height));
    assert(!native_legacy_copy_pixels(dst,dst_bytes,dst_stride,src,src_bytes-1,src_stride,width,height));
    free(dst);free(src);
    puts("PASS: 1440x3200 BGRA CPU copy, padded source, all pixel values, destination guard and undersized/stride refusals");
}
