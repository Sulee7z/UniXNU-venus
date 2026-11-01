// SPDX-License-Identifier: MIT
#include "VenusStProtocol.h"
#include <string.h>
static uint32_t le32(const uint8_t *p) {return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
int vst_firmware_parse(const uint8_t *data,size_t bytes,struct vst_firmware *out) {
    if(!data || !out || bytes<68)return VST_E_ARGUMENT;
    if(le32(data)!=0xaa55aa55u || le32(data+4)!=1 || le32(data+8)!=0x3936)return VST_E_PROTOCOL;
    struct vst_firmware result={0};size_t total=0;
    for(unsigned i=0;i<4;++i) {
        const uint32_t n=le32(data+44+i*4);
        if(n%4 || n>bytes-68-total)return VST_E_PROTOCOL;
        result.sections[i]=n;total+=n;
    }
    if(total!=bytes-68 || !result.sections[0] || !result.sections[1])return VST_E_PROTOCOL;
    result.target_id=(uint16_t)le32(data+8);result.firmware_version=(uint16_t)le32(data+16);
    result.config_version=(uint16_t)le32(data+24);result.payload=data+68;result.payload_bytes=total;
    *out=result;return VST_OK;
}
static int read_register(const struct vst_bus *bus,uint32_t address,uint8_t out[2]) {
    if(!bus || !bus->message || !out)return VST_E_ARGUMENT;
    const uint8_t command[5]={0xfb,(uint8_t)(address>>24),(uint8_t)(address>>16),(uint8_t)(address>>8),(uint8_t)address};
    uint8_t result[3]={0};const int status=bus->message(bus->context,command,sizeof command,result,sizeof result,10);
    if(status)return status;
    out[0]=result[1];out[1]=result[2];return VST_OK;
}
int vst_identify(const struct vst_bus *bus,uint16_t expected,uint16_t *id,uint16_t *version) {
    if(!id || !version)return VST_E_ARGUMENT;
    *id=0;*version=0;
    uint8_t data[2];int status=read_register(bus,0x20000000,data);if(status)return status;
    *id=(uint16_t)((unsigned)data[0]|((unsigned)data[1]<<8));
    // The two hardware bytes are little-endian (DCHIP_ID_0 is the LSB).
    // Do not silently accept a different chip when the caller pins one.
    if(!*id || *id==0xffff || (expected && *id!=expected))return VST_E_ID;
    status=read_register(bus,0x20000004,data);if(status)return status;
    *version=(uint16_t)((unsigned)data[0]|((unsigned)data[1]<<8));return VST_OK;
}
int vst_start_scan(const struct vst_bus *bus) {
    if(!bus || !bus->message)return VST_E_ARGUMENT;
    // Volatile interrupt-enable register and active scan command. No flash,
    // firmware update, calibration or lockdown/NVM command belongs to this path.
    const uint8_t interrupt[6]={0xfa,0x20,0,0,0x29,0x41};
    int status=bus->message(bus->context,interrupt,sizeof interrupt,NULL,0,10);if(status)return status;
    const uint8_t scan[3]={0xa0,0,1};return bus->message(bus->context,scan,sizeof scan,NULL,0,10);
}
int vst_read_fifo(const struct vst_bus *bus,uint8_t out[256],size_t *events) {
    if(!events)return VST_E_ARGUMENT;
    *events=0;
    if(!bus || !bus->message || !out)return VST_E_ARGUMENT;
    const uint8_t command=0x87;uint8_t first[9]={0};
    int status=bus->message(bus->context,&command,1,first,sizeof first,10);if(status)return status;
    if(first[1]==0xff)return VST_E_PROTOCOL;
    if(!first[1])return VST_OK;
    const size_t remaining=first[8]&31u;memcpy(out,first+1,8);*events=1;
    if(remaining) {
        uint8_t rest[249]={0};status=bus->message(bus->context,&command,1,rest,remaining*8+1,10);
        if(status){*events=0;return status;}
        memcpy(out+8,rest+1,remaining*8);*events+=remaining;
    }
    return VST_OK;
}
static int wait_event(const struct vst_bus *bus,const uint8_t *wanted,size_t size,
                      vst_delay_ms_fn delay,void *context,unsigned polls) {
    if(!bus || !bus->message || !delay || !polls)return VST_E_ARGUMENT;
    const uint8_t command=0x87;
    for(unsigned i=0;i<polls;++i) {
        uint8_t raw[9]={0};
        int status=bus->message(bus->context,&command,1,raw,sizeof raw,10);
        if(status)return status;
        if(!memcmp(raw+1,wanted,size))return VST_OK;
        if(raw[1]==VST_EVENT_ERROR)return VST_E_PROTOCOL;
        // 0xff is observed during reset; it is not an input frame. Await the
        // explicit ready/echo instead of treating a delay as firmware readiness.
        delay(context,2);
    }
    return VST_E_TIMEOUT;
}
int vst_wait_ready(const struct vst_bus *bus,vst_delay_ms_fn delay,void *context,unsigned polls) {
    const uint8_t ready=VST_EVENT_READY;
    return wait_event(bus,&ready,1,delay,context,polls);
}
int vst_wait_scan_echo(const struct vst_bus *bus,vst_delay_ms_fn delay,void *context,unsigned polls) {
    const uint8_t echo[]={VST_EVENT_STATUS,0x01,0xa0,0x00,0x01};
    return wait_event(bus,echo,sizeof echo,delay,context,polls);
}
void vst_state_init(struct vst_state *state,int super_resolution,int invert_x,int invert_y) {
    if(!state)return;
    memset(state,0,sizeof *state);state->super_resolution=(uint8_t)!!super_resolution;
    state->invert_x=(uint8_t)!!invert_x;state->invert_y=(uint8_t)!!invert_y;
    for(unsigned i=0;i<VST_CONTACTS;++i)state->contacts[i].id=(uint8_t)i;
}
static void publish(struct vst_state *state,vst_publish_fn notify,void *context) {state->sequence++;if(notify)notify(context,state);}
void vst_release_all(struct vst_state *state,vst_publish_fn notify,void *context) {
    if(!state)return;
    const uint16_t previous=state->active;state->active=0;
    for(unsigned i=0;i<VST_CONTACTS;++i)state->contacts[i].tip=0;
    if(previous)publish(state,notify,context);
}
int vst_process_events(struct vst_state *state,const uint8_t *bytes,size_t count,vst_publish_fn notify,void *context) {
    if(!state || (!bytes && count) || count>VST_FIFO_DEPTH)return VST_E_ARGUMENT;
    int result=VST_OK;
    for(size_t e=0;e<count;++e) {
        const uint8_t *event=bytes+e*8;const unsigned kind=event[0]>>4;
        if(!event[0])break;
        state->events++;
        if(event[0]==VST_EVENT_READY || kind==15) {
            state->resets++;vst_release_all(state,notify,context);continue;
        }
        if(kind!=1 && kind!=2 && kind!=3)continue;
        const unsigned id=event[1]>>4,type=event[1]&15;
        if(id>=VST_CONTACTS || type<1 || type>5 || type==3) {state->invalid++;result=VST_E_PROTOCOL;continue;}
        const uint16_t bit=(uint16_t)(1u<<id);struct vst_contact *contact=&state->contacts[id];
        if(kind==(VST_EVENT_LEAVE>>4)) {
            if(state->active&bit) {state->active=(uint16_t)(state->active&~bit);contact->tip=0;publish(state,notify,context);}
            continue;
        }
        unsigned x,y;
        if(state->super_resolution){x=event[2]|((unsigned)event[3]<<8);y=event[4]|((unsigned)event[5]<<8);}
        else{x=event[2]|((unsigned)(event[3]&15)<<8);y=((unsigned)event[4]<<4)|(event[3]>>4);}
        if(x>VST_X_MAX)x=VST_X_MAX;
        if(y>VST_Y_MAX)y=VST_Y_MAX;
        if(state->invert_x)x=VST_X_MAX-x;
        if(state->invert_y)y=VST_Y_MAX-y;
        contact->x=(uint16_t)x;contact->y=(uint16_t)y;
        contact->type=(uint8_t)type;contact->tip=(uint8_t)(type!=5);contact->confidence=(uint8_t)(type!=4);
        // Preserve each queued movement, including the final position before
        // a lift in the same FIFO batch (vendor handler calls input_sync).
        state->active=(uint16_t)(state->active|bit);
        publish(state,notify,context);
    }
    return result;
}
unsigned vst_native_contacts(const struct vst_state *state,int xs[12],int ys[12],int ids[12]) {
    if(!state || !xs || !ys || !ids)return 0;
    unsigned count=0;
    for(unsigned i=0;i<VST_CONTACTS;++i)if(state->active&(1u<<i)) {
        const struct vst_contact *c=&state->contacts[i];
        if(!c->tip || !c->confidence)continue;
        unsigned x=c->x>VST_X_MAX?VST_X_MAX:c->x,y=c->y>VST_Y_MAX?VST_Y_MAX:c->y;
        xs[count]=(int)(x*30479u/VST_X_MAX);
        ys[count]=(int)(y*20319u/VST_Y_MAX);
        ids[count++]=c->id;
    }
    return count;
}
static void coordinate(uint8_t *out,unsigned value,unsigned maximum) {
    const uint16_t normalized=(uint16_t)((uint32_t)value*32767u/maximum);out[0]=(uint8_t)normalized;out[1]=(uint8_t)(normalized>>8);
}
int vst_hid_report(const struct vst_state *state,const struct vst_hid_state *previous,uint8_t out[62],struct vst_hid_state *next) {
    if(!state || !previous || !out || !next || ((state->active|previous->active)&~0x3ffu))return VST_E_ARGUMENT;
    memset(out,0,62);out[0]=3;unsigned slot=0;
    const uint16_t include=(uint16_t)(state->active|previous->active);
    for(unsigned id=0;id<VST_CONTACTS;++id)if(include&(1u<<id)) {
        const int active=!!(state->active&(1u<<id));
        const struct vst_contact *contact=active?&state->contacts[id]:&previous->contacts[id];
        uint8_t *finger=out+1+slot++*6;finger[0]=(uint8_t)((active&&contact->tip?1:0)|(contact->confidence?2:0));
        finger[1]=(uint8_t)id;coordinate(finger+2,contact->x,VST_X_MAX);coordinate(finger+4,contact->y,VST_Y_MAX);
    }
    out[61]=(uint8_t)slot;next->active=state->active;memcpy(next->contacts,state->contacts,sizeof next->contacts);
    return VST_OK;
}
