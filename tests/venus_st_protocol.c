// SPDX-License-Identifier: MIT
#include "VenusStProtocol.h"
#include "VenusStGpio.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned reports;static struct vst_hid_state prior;
static void notify(void *context,const struct vst_state *state) {
    (void)context;uint8_t report[62];struct vst_hid_state next;
    assert(vst_hid_report(state,&prior,report,&next)==0);assert(report[61]<=10);
    for(unsigned i=0;i<report[61];++i)assert(report[2+i*6]<10);
    prior=next;reports++;
}
static void event(uint8_t out[8],unsigned kind,unsigned id,unsigned x,unsigned y) {
    memset(out,0,8);out[0]=(uint8_t)((kind<<4)|3);out[1]=(uint8_t)((id<<4)|1);
    out[2]=(uint8_t)x;out[3]=(uint8_t)(((y&15)<<4)|(x>>8));out[4]=(uint8_t)(y>>4);
}
struct fake {unsigned calls;int fail;};
static int message(void *context,const uint8_t *cmd,size_t n,uint8_t *out,size_t bytes,unsigned delay) {
    struct fake *fake=context;fake->calls++;assert(delay==10);
    if(fake->fail==(int)fake->calls)return VST_E_IO;
    if(cmd[0]==0xfb){assert(n==5&&bytes==3&&cmd[1]==0x20);out[0]=0xee;out[1]=cmd[4]==0?0x36:0x84;out[2]=cmd[4]==0?0x39:0;}
    else if(cmd[0]==0x87){assert(n==1);memset(out,0,bytes);if(bytes==9){event(out+1,1,2,1439,3199);out[8]=31;}else for(unsigned i=0;i<31;++i)event(out+1+i*8,2,2,600,1200);}
    else if(cmd[0]==0xfa){assert(n==6&&bytes==0&&cmd[4]==0x29&&cmd[5]==0x41);}
    else {assert(n==3&&cmd[0]==0xa0&&cmd[1]==0&&cmd[2]==1&&bytes==0);}
    return 0;
}
struct startup {unsigned calls,delays;int fail,reply;};
static int startup_message(void *context,const uint8_t *cmd,size_t n,uint8_t *out,size_t bytes,unsigned delay) {
    struct startup *s=context;s->calls++;
    assert(cmd[0]==0x87 && n==1 && bytes==9 && delay==10);
    if(s->fail)return VST_E_IO;
    memset(out,0,bytes);out[0]=0xe7; // dummy is not an event
    if(s->calls==1){memset(out+1,0xff,8);return 0;}
    if(s->reply==1)out[1]=0x03;
    if(s->reply==2){const uint8_t echo[]={0x43,0x01,0xa0,0x00,0x01};memcpy(out+1,echo,sizeof echo);}
    if(s->reply==3)out[1]=0xf3;
    return 0;
}
static void startup_delay(void *context,unsigned ms){struct startup *s=context;assert(ms==2);s->delays++;}
static void startup_tests(void) {
    struct startup s={0,0,0,1};struct vst_bus bus={&s,startup_message};
    assert(vst_wait_ready(&bus,startup_delay,&s,5)==0 && s.calls==2 && s.delays==1);
    s=(struct startup){0,0,0,2};assert(vst_wait_scan_echo(&bus,startup_delay,&s,5)==0);
    s=(struct startup){0,0,0,0};assert(vst_wait_ready(&bus,startup_delay,&s,4)==VST_E_TIMEOUT && s.calls==4);
    s=(struct startup){0,0,1,1};assert(vst_wait_ready(&bus,startup_delay,&s,4)==VST_E_IO && s.calls==1);
    s=(struct startup){0,0,0,3};assert(vst_wait_ready(&bus,startup_delay,&s,4)==VST_E_PROTOCOL);
}
int main(int argc,char **argv) {
    assert(VST_EVENT_ENTER==0x13 && VST_EVENT_MOTION==0x23 && VST_EVENT_LEAVE==0x33);
    startup_tests();
    // A high -> low reset must clear OUT bit1, even when the input level is 1.
    assert(vst_gpio_output(3,0)==1 && vst_gpio_output(1,1)==3);
    assert(vst_gpio_output(0xfeed0002u,0)==0xfeed0000u);
    assert(!(vst_gpio_control(0xffffffffu,1,3,0,0)&(1u<<9)));
    assert((vst_gpio_control(0xfeed0000u,0,3,0,1)&~0x3ffu)==0xfeed0000u);
    assert(argc==2);FILE *file=fopen(argv[1],"rb");assert(file);assert(fseek(file,0,SEEK_END)==0);long length=ftell(file);assert(length>68);rewind(file);
    uint8_t *firmware=malloc((size_t)length);assert(firmware&&fread(firmware,1,(size_t)length,file)==(size_t)length);fclose(file);
    struct vst_firmware info;assert(vst_firmware_parse(firmware,(size_t)length,&info)==0);assert(info.target_id==0x3936&&info.firmware_version==0x84&&info.config_version==0x48);
    assert(vst_firmware_parse(firmware,(size_t)length-1,&info)!=0);firmware[8]^=1;assert(vst_firmware_parse(firmware,(size_t)length,&info)!=0);firmware[8]^=1;
    firmware[44]=0xff;assert(vst_firmware_parse(firmware,(size_t)length,&info)!=0);free(firmware);
    struct vst_state state;vst_state_init(&state,0,0,0);uint8_t bytes[256];event(bytes,1,2,1439,3199);
    assert(vst_process_events(&state,bytes,1,notify,NULL)==0&&state.active==4&&reports==1);
    uint8_t report[62];struct vst_hid_state next;assert(vst_hid_report(&state,&prior,report,&next)==0);assert(report[3]==0xff&&report[4]==0x7f&&report[5]==0xff&&report[6]==0x7f);
    event(bytes,1,9,0,0);assert(vst_process_events(&state,bytes,1,notify,NULL)==0&&state.active==0x204);
    event(bytes,3,2,0,0);assert(vst_hid_report(&state,&prior,report,&next)==0);assert(vst_process_events(&state,bytes,1,notify,NULL)==0&&state.active==0x200);
    unsigned before=reports;event(bytes,1,9,4000,4000);assert(vst_process_events(&state,bytes,1,notify,NULL)==0&&reports==before+1);assert(state.contacts[9].x==1439&&state.contacts[9].y==3199);
    int xs[12],ys[12],ids[12];assert(vst_native_contacts(&state,xs,ys,ids)==1 && ids[0]==9 && xs[0]==30479 && ys[0]==20319);
    state.contacts[9].confidence=0;assert(vst_native_contacts(&state,xs,ys,ids)==0);state.contacts[9].confidence=1;
    state.contacts[9].tip=0;assert(vst_native_contacts(&state,xs,ys,ids)==0);state.contacts[9].tip=1;
    event(bytes,1,15,0,0);before=reports;assert(vst_process_events(&state,bytes,1,notify,NULL)==VST_E_PROTOCOL&&reports==before&&state.active==0x200);
    vst_release_all(&state,notify,NULL);assert(!state.active&&!prior.active);
    vst_state_init(&state,1,1,1);memset(bytes,0,8);bytes[0]=0x13;bytes[1]=0x11;bytes[2]=0x9f;bytes[3]=5;bytes[4]=0x7f;bytes[5]=12;
    assert(vst_process_events(&state,bytes,1,notify,NULL)==0&&state.contacts[1].x==0&&state.contacts[1].y==0);
    assert(vst_process_events(&state,bytes,33,notify,NULL)==VST_E_ARGUMENT);
    struct fake fake={0};struct vst_bus bus={&fake,message};uint16_t id=0,version=0;assert(vst_identify(&bus,0x3936,&id,&version)==0&&id==0x3936&&version==0x84);
    fake.calls=0;assert(vst_identify(&bus,0x4036,&id,&version)==VST_E_ID && fake.calls==1 && version==0);
    fake.calls=0;fake.fail=2;assert(vst_identify(&bus,0x3936,&id,&version)==VST_E_IO&&fake.calls==2);
    fake.calls=0;fake.fail=0;size_t count=0;assert(vst_read_fifo(&bus,bytes,&count)==0&&count==32&&fake.calls==2);
    fake.calls=0;fake.fail=2;count=99;assert(vst_read_fifo(&bus,bytes,&count)==VST_E_IO&&count==0);
    fake.calls=0;fake.fail=0;assert(vst_start_scan(&bus)==0&&fake.calls==2);
    puts("PASS: STM FTB bounds, strict ID, ready/echo timeout, GPIO reset, contact codec and native HID coordinate bridge");
    return 0;
}
