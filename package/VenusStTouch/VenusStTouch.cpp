// SPDX-License-Identifier: MIT
// Own Venus ST FTS5 backend. GPIO/clock addresses are Lahaina/Venus inputs;
// protocol is separate from the shared GENI controller and original HID ABI.
#include "VenusStProtocol.h"
#include "VenusStGpio.h"
#include "VenusStGeniTransport.h"
extern "C" {
#include "GeniSpi.h"
}
#include <IOKit/IOLib.h>
#include <IOKit/IODeviceMemory.h>
#include <IOKit/IOMemoryDescriptor.h>
#include <pexpert/pexpert.h>
#include <kern/thread.h>
#include <string.h>
extern "C" {
volatile uint32_t native_touch_seq,native_touch_count,native_touch_hid_reports;
volatile int native_touch_xs[12],native_touch_ys[12],native_touch_ids[12];
volatile uint32_t venus_st_stage,venus_st_frames,venus_st_errors;
volatile int venus_st_status=-1;
volatile uint32_t venus_st_chip_id,venus_st_firmware_version;
volatile uint32_t venus_st_clock_cmd,venus_st_clock_cfg,venus_st_geni_protocol=~0u,venus_st_geni_fifo_disabled=~0u;
volatile uint32_t venus_st_messages,venus_st_opcode,venus_st_irq_polls,venus_st_irq_low;
volatile int venus_st_transfer_status=-1,venus_st_cs_status=-1;
volatile uint32_t venus_st_id_attempts;
volatile int venus_st_loop_status=-1;
volatile uint32_t venus_st_loop_match,venus_st_pin_io[4];
volatile int venus_st_power_status=-1;
volatile uint32_t venus_st_power_base;
volatile uint32_t venus_st_last_count,venus_st_last_event[8],venus_st_publish_sequence;
extern volatile uint32_t venus_st_hid_phase,venus_st_hid_ready,venus_st_hid_reports;
extern volatile uint32_t venus_st_hid_ticks;
extern volatile uint32_t native_hid_stage,native_hid_resource_found;
extern volatile int native_hid_load_status,native_hid_matching_load_status,native_hid_input_meta_status;
extern volatile uint32_t native_hid_input_events[8];
extern volatile int native_hid_input_results[8];
extern volatile uint32_t native_touch_edge_stats[4];
#ifndef VENUS_ST_REPORT_BUILD
#define VENUS_ST_REPORT_BUILD "unversioned"
#endif
extern volatile int venus_st_hid_meta_status,venus_st_hid_start_status,venus_st_hid_report_status,venus_st_hid_match_status;
int venus_st_diagnostic_json(char *out,size_t bytes) {
    return snprintf(out,bytes,"{\"schema\":1,\"build\":\"%s\",\"sample\":\"prelaunchd\",\"protocol\":\"stm-fts-spi\",\"stage\":%u,\"status\":%d,"
        "\"clock_cmd\":%u,\"clock_cfg\":%u,\"geni_protocol\":%u,\"fifo_disabled\":%u,\"chip_id\":%u,\"fw\":%u,"
        "\"messages\":%u,\"id_attempts\":%u,\"opcode\":%u,\"transfer\":%d,\"cs\":%d,\"cs_manual\":0,\"loop_status\":%d,"
        "\"loop_match\":%u,\"pin_io\":[%u,%u,%u,%u],\"power_status\":%d,\"power_base\":%u,\"tp_enable\":154,"
        "\"irq_polls\":%u,\"irq_low\":%u,"
        "\"frames\":%u,\"errors\":%u,\"hid_phase\":%u,\"hid_match\":%d,\"hid_meta\":%d,\"hid_start\":%d,\"hid_ready\":%u,"
        "\"hid_report\":%d,\"hid_reports\":%u,\"hid_ticks\":%u,\"publish_seq\":%u,\"last_count\":%u,"
        "\"last_event\":[%u,%u,%u,%u,%u,%u,%u,%u],\"native_stage\":%u,\"native_res\":%u,"
        "\"native_load\":%d,\"native_match\":%d,\"native_meta\":%d,"
        "\"native_events\":[%u,%u,%u,%u,%u,%u,%u,%u],\"native_results\":[%d,%d,%d,%d,%d,%d,%d,%d],"
        "\"native_reports\":%u,\"edge\":[%u,%u,%u,%u]}\n",
        VENUS_ST_REPORT_BUILD,venus_st_stage,venus_st_status,venus_st_clock_cmd,venus_st_clock_cfg,venus_st_geni_protocol,
        venus_st_geni_fifo_disabled,venus_st_chip_id,venus_st_firmware_version,venus_st_messages,venus_st_id_attempts,
        venus_st_opcode,venus_st_transfer_status,venus_st_cs_status,venus_st_loop_status,venus_st_loop_match,
        venus_st_pin_io[0],venus_st_pin_io[1],venus_st_pin_io[2],venus_st_pin_io[3],venus_st_power_status,
        venus_st_power_base,venus_st_irq_polls,venus_st_irq_low,
        venus_st_frames,venus_st_errors,venus_st_hid_phase,venus_st_hid_match_status,venus_st_hid_meta_status,
        venus_st_hid_start_status,venus_st_hid_ready,venus_st_hid_report_status,venus_st_hid_reports,
        venus_st_hid_ticks,venus_st_publish_sequence,venus_st_last_count,
        venus_st_last_event[0],venus_st_last_event[1],venus_st_last_event[2],venus_st_last_event[3],
        venus_st_last_event[4],venus_st_last_event[5],venus_st_last_event[6],venus_st_last_event[7],
        native_hid_stage,native_hid_resource_found,native_hid_load_status,native_hid_matching_load_status,native_hid_input_meta_status,
        native_hid_input_events[0],native_hid_input_events[1],native_hid_input_events[2],native_hid_input_events[3],
        native_hid_input_events[4],native_hid_input_events[5],native_hid_input_events[6],native_hid_input_events[7],
        native_hid_input_results[0],native_hid_input_results[1],native_hid_input_results[2],native_hid_input_results[3],
        native_hid_input_results[4],native_hid_input_results[5],native_hid_input_results[6],native_hid_input_results[7],
        native_touch_hid_reports,native_touch_edge_stats[0],native_touch_edge_stats[1],native_touch_edge_stats[2],native_touch_edge_stats[3]);
}
}
static IOLock *snapshotLock;
static void (*nativeTouchSink)(void *);
static void *nativeTouchContext;
extern "C" void native_touch_set_sink(void (*sink)(void *),void *context) {
    if(!snapshotLock)return;
    OSObject *next=static_cast<OSObject *>(context);if(next)next->retain();
    IOLockLock(snapshotLock);
    OSObject *old=static_cast<OSObject *>(nativeTouchContext);
    nativeTouchContext=context;nativeTouchSink=sink;
    IOLockUnlock(snapshotLock);
    if(old)old->release();
}
static void publishNative(const struct vst_state *updated) {
    int xs[12]={},ys[12]={},ids[12]={};
    const unsigned count=vst_native_contacts(updated,xs,ys,ids);
    native_touch_seq=native_touch_seq+1;
    __asm__ volatile("dmb ish":::"memory");
    native_touch_count=count;
    for(unsigned i=0;i<count;++i){native_touch_xs[i]=xs[i];native_touch_ys[i]=ys[i];native_touch_ids[i]=ids[i];}
    __asm__ volatile("dmb ish":::"memory");
    native_touch_seq=native_touch_seq+1;
    IOLockLock(snapshotLock);
    void (*notify)(void *)=nativeTouchSink;
    OSObject *context=static_cast<OSObject *>(nativeTouchContext);
    if(context)context->retain();
    IOLockUnlock(snapshotLock);
    if(notify)notify(context);
    if(context)context->release();
}
namespace {
static struct vst_state snapshot;
static struct geni_spi spi;
static IOMemoryMap *maps[6];
static volatile uint8_t *se,*wrapper,*gcc,*tlmm,*rsc,*cmd_db;
static void (*sink)(void *);static void *sinkContext;
static unsigned mode;
static uint32_t rd32(volatile uint8_t *base,uint32_t reg) {uint32_t v=*reinterpret_cast<volatile uint32_t *>(base+reg);__asm__ volatile("dmb oshld":::"memory");return v;}
static void wr32(volatile uint8_t *base,uint32_t reg,uint32_t v) {__asm__ volatile("dmb oshst":::"memory");*reinterpret_cast<volatile uint32_t *>(base+reg)=v;__asm__ volatile("dsb oshst":::"memory");}
struct cmd_db_slave {uint16_t id,header_offset,data_offset,count,version,reserved[3];};
struct cmd_db_header {uint32_t version;uint8_t magic[4];struct cmd_db_slave slave[8];uint32_t checksum,reserved;uint8_t data[];};
struct cmd_db_entry {char id[8];uint32_t priority[2],address;uint16_t length,offset;};
static uint32_t rpmh_address(const char *name) {
    if(!cmd_db)return 0;
    const struct cmd_db_header *db=reinterpret_cast<const struct cmd_db_header *>(const_cast<uint8_t *>(cmd_db));
    if(db->magic[0]!=0xdb || db->magic[1]!=0x30 || db->magic[2]!=0x03 || db->magic[3]!=0x0c)return 0;
    char id[8]={0};for(unsigned i=0;i<7 && name[i];++i)id[i]=name[i];
    for(unsigned s=0;s<8;++s) {
        const struct cmd_db_slave *slave=&db->slave[s];
        if(!slave->id || !slave->count || slave->count>512)continue;
        const struct cmd_db_entry *entry=reinterpret_cast<const struct cmd_db_entry *>(db->data+slave->header_offset);
        for(unsigned i=0;i<slave->count;++i)if(!memcmp(entry[i].id,id,sizeof id))return entry[i].address;
    }
    return 0;
}
static bool rpmh_wait(uint32_t reg,uint32_t mask,uint32_t value) {
    for(unsigned i=0;i<2000;++i){if((rd32(rsc,0xd00+reg)&mask)==value)return true;IODelay(100);}
    return false;
}
static bool rpmh_write(const uint32_t *address,const uint32_t *data,unsigned count) {
    const uint32_t irq=rd32(rsc,0xd00);
    for(unsigned i=0;rd32(rsc,0xd00+0x18)==0;++i){if(i>2000)return false;IODelay(100);}
    wr32(rsc,0xd00+0x14,rd32(rsc,0xd00+0x14)&~(1u<<24));
    wr32(rsc,0xd00+0x14,rd32(rsc,0xd00+0x14)&~(1u<<16));
    wr32(rsc,0xd00+0x08,1);
    for(unsigned i=0;i<count;++i){wr32(rsc,0xd00+0x30+20*i,0x10008|0x100);wr32(rsc,0xd00+0x34+20*i,address[i]);wr32(rsc,0xd00+0x38+20*i,data[i]);}
    wr32(rsc,0xd00+0x10,(1u<<count)-1);wr32(rsc,0xd00+0x1c,(1u<<count)-1);
    wr32(rsc,0xd00,irq|1);wr32(rsc,0xd00+0x14,1u<<16);wr32(rsc,0xd00+0x14,(1u<<16)|(1u<<24));
    const bool done=rpmh_wait(0x04,1,1);
    wr32(rsc,0xd00+0x14,rd32(rsc,0xd00+0x14)&~(1u<<24));
    wr32(rsc,0xd00+0x14,rd32(rsc,0xd00+0x14)&~(1u<<16));
    wr32(rsc,0xd00+0x1c,0);wr32(rsc,0xd00+0x10,0);wr32(rsc,0xd00+0x08,1);wr32(rsc,0xd00,irq);
    return done;
}
static int io_supply_on() {
    uint32_t base=rpmh_address("ldoc2");
    venus_st_power_base=base;
    if(!base || (base>>16&0xfu)!=4u)return VST_E_IO;
    const uint32_t address[3]={base,base+4u,base+8u};
    const uint32_t data[3]={1800u,1u,7u};
    return rpmh_write(address,data,3)?0:VST_E_IO;
}
static uint32_t readSe(void *,uint32_t reg) {return rd32(se,reg);}
static void writeSe(void *,uint32_t reg,uint32_t value) {wr32(se,reg,value);}
static uint32_t readWrapper(void *,uint32_t reg) {return rd32(wrapper,reg);}
static void delay(void *,unsigned us) {
    // Sheng TouchProbe uses the architectural counter for short SPI waits;
    // IODelay in this kernel may block/schedule even for a one-us poll.
    if(us>50){IODelay(us);return;}
    uint64_t frequency=0,start=0,now=0;
    __asm__ volatile("mrs %0, cntfrq_el0":"=r"(frequency));
    __asm__ volatile("mrs %0, cntvct_el0":"=r"(start));
    const uint64_t ticks=(frequency*us+999999)/1000000;
    do {__asm__ volatile("mrs %0, cntvct_el0":"=r"(now));} while(now-start<ticks);
}
static void delayMs(void *,unsigned ms){IOSleep(ms);}
static volatile uint8_t *map(unsigned index,uint64_t physical,size_t bytes) {
    IODeviceMemory *memory=IODeviceMemory::withRange(physical,bytes);if(!memory)return nullptr;
    maps[index]=memory->map(kIOMapInhibitCache);memory->release();
    return maps[index]?reinterpret_cast<volatile uint8_t *>(maps[index]->getVirtualAddress()):nullptr;
}
static void gpio(unsigned pin,unsigned mux,bool output,bool high,unsigned pull) {
    const uint32_t reg=0x100000+pin*0x1000;
    const uint32_t control=vst_gpio_control(rd32(tlmm,reg),mux,3,pull,output);
    // Set the output latch before OE. Input direction is OE=0; IO bit0 is
    // read-only pin level, and must not be treated as an enable switch.
    if(output)wr32(tlmm,reg+4,vst_gpio_output(rd32(tlmm,reg+4),high));
    wr32(tlmm,reg,control);
}
static int clock() {
    // AHB wrapper clocks are firmware-critical Lahaina clocks. Take a vote for
    // SE11/S3 only and select CX-safe XO19.2MHz; no PLL or shared AHB reprogram.
    wr32(gcc,0x52008,rd32(gcc,0x52008)|(1u<<25));
    venus_st_clock_cfg=(rd32(gcc,0x183a4)&~(0x700u|0x1fu|0x3000u))|1u;
    wr32(gcc,0x183a4,venus_st_clock_cfg);
    wr32(gcc,0x183a0,rd32(gcc,0x183a0)|1u);
    for(unsigned n=0;n<2000;++n){venus_st_clock_cmd=rd32(gcc,0x183a0);if(!(venus_st_clock_cmd&1))return 0;IODelay(1);}
    return VST_E_IO;
}
static int message(void *,const uint8_t *command,size_t commandBytes,uint8_t *out,size_t readBytes,unsigned hold) {
    if(!command || !commandBytes)return VST_E_ARGUMENT;
    venus_st_messages=venus_st_messages+1;venus_st_opcode=command[0];
    int ended=-1;
    const int status=vst_geni_message(&spi,command,commandBytes,out,readBytes,hold,&ended);
    venus_st_transfer_status=status;
    venus_st_cs_status=ended;
    return status;
}
static void publish(void *,const struct vst_state *updated) {
    IOLockLock(snapshotLock);snapshot=*updated;venus_st_publish_sequence=updated->sequence;void (*notify)(void *)=sink;OSObject *context=static_cast<OSObject *>(sinkContext);
    if(context)context->retain();IOLockUnlock(snapshotLock);
    publishNative(updated);
    if(notify)notify(context);if(context)context->release();
}
static void run(void *,wait_result_t) {
    venus_st_stage=1;
    se=map(0,0xa8c000,0x4000);wrapper=map(1,0xac0000,0x2000);gcc=map(2,0x100000,0x80000);tlmm=map(3,0xf000000,0x200000);
    rsc=map(4,0x18220000,0x10000);cmd_db=map(5,0x80860000,0x20000);
    if(!se || !wrapper || !gcc || !tlmm){venus_st_status=VST_E_IO;return;}
    if(mode==1){venus_st_stage=2;venus_st_status=0;IOLog("venus-st: mapped SE/wrapper/GCC/TLMM resources without hardware access\n");return;}
    venus_st_stage=3;
    // The reference power_on order is reset low, interrupt as input, LDO2,
    // then AVDD/TP enable. Keep that order; the rail must precede the switch.
    gpio(22,0,true,false,0);gpio(23,0,false,false,3);
    venus_st_power_status=rsc?io_supply_on():VST_E_IO;
    if(venus_st_power_status){venus_st_status=venus_st_power_status;return;}
    IOSleep(3);gpio(132,0,true,true,0);gpio(154,0,true,true,0);IOSleep(15);
    venus_st_status=clock();if(venus_st_status)return;
    for(unsigned pin=48;pin<=51;++pin)gpio(pin,1,false,false,0);
    for(unsigned pin=0;pin<4;++pin)venus_st_pin_io[pin]=rd32(tlmm,0x100000+(48+pin)*0x1000+4);
    // The existing flash firmware stays intact. Reset only the controller MCU;
    // no downloaded firmware or NVM/lockdown/calibration operation is present.
    // Reset remains low through rail/clock/GENI setup, at least the vendor's
    // 10 ms. Release below and consume CONTROLLER_READY before sending scan.
    spi.se={nullptr,readSe,writeSe,delay};spi.wrapper={nullptr,readWrapper,nullptr,delay};spi.poll_only=1;spi.poll_limit=20000;
    venus_st_stage=4;venus_st_status=geni_spi_init(&spi);
    if(!venus_st_status){wr32(se,0x278,0);wr32(se,0x80c,0);}
    venus_st_geni_protocol=spi.info.protocol;venus_st_geni_fifo_disabled=spi.info.fifo_disabled;
    if(venus_st_status){IOLog("venus-st: GENI init %d protocol%u fifo-disabled%d\n",venus_st_status,spi.info.protocol,spi.info.fifo_disabled);return;}
    venus_st_status=geni_spi_setup(&spi,0,0);if(venus_st_status)return;
    venus_st_status=geni_spi_set_clock(&spi,6400000,19200000,0);if(venus_st_status)return;
    // Internal MOSI->MISO loopback separates the GENI/clock/packing path from
    // the external chip, the same diagnostic the official sheng probe uses.
    uint8_t loop_tx[8]={0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88},loop_rx[8]={0};
    venus_st_status=geni_spi_setup(&spi,GENI_SPI_LOOP,0);if(venus_st_status)return;
    venus_st_loop_status=geni_spi_transfer(&spi,loop_tx,loop_rx,sizeof loop_tx,0);
    venus_st_loop_match=!venus_st_loop_status && !memcmp(loop_rx,loop_tx,sizeof loop_tx);
    venus_st_status=geni_spi_setup(&spi,0,0);if(venus_st_status)return;
    if(!venus_st_loop_match){venus_st_status=VST_E_IO;return;}
    const struct vst_bus bus={nullptr,message};
    gpio(22,0,true,true,0);
    venus_st_stage=5;
    venus_st_status=vst_wait_ready(&bus,delayMs,nullptr,250);if(venus_st_status)return;
    uint16_t id=0,version=0;venus_st_id_attempts=1;
    venus_st_status=vst_identify(&bus,0x3936,&id,&version);
    venus_st_chip_id=id;venus_st_firmware_version=version;
    if(venus_st_status || mode==2)return;
    venus_st_stage=6;
    venus_st_status=vst_start_scan(&bus);if(venus_st_status)return;
    venus_st_status=vst_wait_scan_echo(&bus,delayMs,nullptr,250);if(venus_st_status)return;
    venus_st_stage=7;venus_st_status=0;
    struct vst_state current;vst_state_init(&current,0,0,0);
    unsigned failed=0;
    for(;;) {
        venus_st_irq_polls=venus_st_irq_polls+1;
        if(!(rd32(tlmm,0x117004)&1)) {
            venus_st_irq_low=venus_st_irq_low+1;
            uint8_t events[256]={};size_t count=0;
            int status=vst_read_fifo(&bus,events,&count);
            if(!status && count) {
                venus_st_last_count=(uint32_t)count;
                for(unsigned i=0;i<8;++i)venus_st_last_event[i]=events[i];
                const uint32_t resets=current.resets;
                status=vst_process_events(&current,events,count,publish,nullptr);
                if(!status && current.resets!=resets) {
                    status=vst_start_scan(&bus);
                    if(!status)status=vst_wait_scan_echo(&bus,delayMs,nullptr,250);
                }
                if(!status)venus_st_frames=venus_st_frames+1;
            }
            if(status) {
                venus_st_errors=venus_st_errors+1;venus_st_status=status;
                vst_release_all(&current,publish,nullptr);
                if(++failed>=3){venus_st_stage=8;return;}
            } else {failed=0;venus_st_status=0;}
        }
        IOSleep(8);
    }
}
}
extern "C" bool venus_st_snapshot(struct vst_state *out) {
    if(!snapshotLock || !out)return false;
    IOLockLock(snapshotLock);*out=snapshot;IOLockUnlock(snapshotLock);return true;
}
extern "C" void venus_st_set_sink(void (*notify)(void *),void *context) {
    if(!snapshotLock)return;
    OSObject *next=static_cast<OSObject *>(context);if(next)next->retain();
    IOLockLock(snapshotLock);OSObject *old=static_cast<OSObject *>(sinkContext);sink=notify;sinkContext=next;IOLockUnlock(snapshotLock);
    if(old)old->release();
}
extern "C" void venus_st_probe(void) {
    if(snapshotLock)return;
    mode=0;PE_parse_boot_argn("venus-st-touch",&mode,sizeof mode);if(!mode || mode>3)return;
    snapshotLock=IOLockAlloc();if(!snapshotLock){venus_st_status=VST_E_IO;return;}
    vst_state_init(&snapshot,0,0,0);thread_t thread=nullptr;
    if(kernel_thread_start(run,nullptr,&thread)==KERN_SUCCESS)thread_deallocate(thread);
    else venus_st_status=VST_E_IO;
}
