// SPDX-License-Identifier: MIT
// QEMU-only physical-input substitute. Never link into a phone kernel.
// The original IOHIDFamily, actual VenusHidTouch and actual report codec run.
#include "VenusStProtocol.h"
#include <IOKit/IOLib.h>
#include <IOKit/IOService.h>
#include <kern/thread.h>
extern "C" {
extern volatile uint32_t venus_st_hid_reports,venus_st_hid_ready;
extern volatile int venus_st_hid_status;
volatile uint32_t venus_st_stage,venus_st_frames,venus_st_errors;
volatile int venus_st_status;
volatile uint32_t venus_st_chip_id,venus_st_firmware_version;
volatile uint32_t venus_st_test_passed,venus_st_test_reads,venus_st_test_sink;
__attribute__((noinline)) void venus_st_hid_test_done(void) {__asm__ volatile("":::"memory");}
static void finish(void *,wait_result_t) {
    for(unsigned i=0;i<600 && venus_st_hid_reports<3;++i)IOSleep(50);
    venus_st_test_passed=venus_st_hid_ready==1 && venus_st_hid_reports==3 && venus_st_hid_status==0;
    venus_st_hid_test_done();
}
void venus_st_probe(void) {
    venus_st_stage=7;thread_t thread=nullptr;
    if(kernel_thread_start(finish,nullptr,&thread)==KERN_SUCCESS)thread_deallocate(thread);
}
void venus_st_set_sink(void (*notify)(void *),void *) {venus_st_test_sink=notify?1:0;}
bool venus_st_snapshot(struct vst_state *out) {
    if(!out || venus_st_hid_reports>=3)return false;
    venus_st_test_reads=venus_st_test_reads+1;vst_state_init(out,0,0,0);
    out->sequence=venus_st_hid_reports+1;
    if(venus_st_hid_reports<2) {
        out->active=1;out->contacts[0]={static_cast<uint16_t>(venus_st_hid_reports?1439:0),
            static_cast<uint16_t>(venus_st_hid_reports?3199:0),0,1,1,1};
    }
    return true;
}
}
