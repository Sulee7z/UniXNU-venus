// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include "VenusStProtocol.h"
#include <stdbool.h>

static inline bool vst061_at_edge(int32_t x,int32_t y) {
    const int32_t ex=48*65536/1440,ey=48*65536/3200;
    return x<ex||x>65536-ex||y<ey||y>65536-ey;
}

static inline int vst061_report(const struct vst_state *input,const struct vst_hid_state *previous,
    uint8_t out[62],struct vst_hid_state *next) {
    if(!input)return VST_E_ARGUMENT;
    struct vst_state filtered=*input;
    for(unsigned i=0;i<VST_CONTACTS;++i)
        if(!filtered.contacts[i].tip||!filtered.contacts[i].confidence)
            filtered.active=(uint16_t)(filtered.active&~(1u<<i));
    return vst_hid_report(&filtered,previous,out,next);
}
