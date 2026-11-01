// SPDX-License-Identifier: MIT
// Raw STM FIFO fixtures. IDs are taken from the pinned vendor ftsSoftware.h,
// not generated from the implementation under test. One swipe in one batch.
#include "VenusStProtocol.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned calls;
static const unsigned tips[]={3,3,3,2};
static const unsigned ys[]={3000,2000,1000,1000};
static struct vst_hid_state previous;
static void observe(void *unused,const struct vst_state *state) {
    (void)unused;
    uint8_t report[62];struct vst_hid_state next;
    assert(calls<4 && vst_hid_report(state,&previous,report,&next)==0);
    assert(report[61]==1 && report[1]==tips[calls] && report[2]==0);
    unsigned y=(unsigned)report[5]|((unsigned)report[6]<<8);
    assert(y==ys[calls]*32767u/3199u);
    previous=next;++calls;
}
int main(void) {
    const uint8_t stroke[][8]={
        {0x13,0x01,0x64,0x80,0xbb,0,0,3}, // down (100,3000)
        {0x23,0x01,0x64,0x00,0x7d,0,0,2}, // move (100,2000), still down
        {0x23,0x01,0x64,0x80,0x3e,0,0,1}, // move (100,1000), still down
        {0x33,0x01,0,0,0,0,0,0},          // lift at last known position
    };
    struct vst_state state;vst_state_init(&state,0,0,0);
    assert(vst_process_events(&state,&stroke[0][0],4,observe,0)==0);
    assert(calls==4 && state.active==0 && previous.active==0);
    // A controller-ready/status/empty FIFO must never create a finger.
    const uint8_t idle[][8]={{0x03,0,0,0,0,0,0,1},{0x43,1,0xa0,0,1,0,0,0},{0,0,0,0,0,0,0,0}};
    assert(vst_process_events(&state,&idle[0][0],3,observe,0)==0 && calls==4);
    puts("PASS: raw STM down -> two moves -> lift keeps one continuous contact; no boot-event touches");
    return 0;
}
