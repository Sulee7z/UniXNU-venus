// SPDX-License-Identifier: MIT
// Own ST FTS5 SPI protocol/state core for Venus; no Linux driver code included.
#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
enum {VST_CONTACTS=10,VST_EVENT_BYTES=8,VST_FIFO_DEPTH=32,VST_X_MAX=1439,VST_Y_MAX=3199};
enum {VST_OK=0,VST_E_ARGUMENT=-22,VST_E_PROTOCOL=-71,VST_E_IO=-5,VST_E_ID=-19,VST_E_TIMEOUT=-110};
// STMicroelectronics fts_spi/fts_lib/ftsSoftware.h. FocalTech also uses the
// abbreviation FTS, but its register framing and report format are unrelated.
enum {VST_EVENT_READY=0x03,VST_EVENT_ENTER=0x13,VST_EVENT_MOTION=0x23,
      VST_EVENT_LEAVE=0x33,VST_EVENT_STATUS=0x43,VST_EVENT_ERROR=0xf3};
struct vst_bus {
    void *context;
    // One message: command then read clocks under one CS assertion. rx includes
    // the protocol dummy byte; wait10us before CS deassertion. No autonomous retry.
    int (*message)(void *,const uint8_t *,size_t,uint8_t *,size_t,unsigned);
};
struct vst_firmware {
    uint16_t target_id,firmware_version,config_version;
    uint32_t sections[4];
    const uint8_t *payload;
    size_t payload_bytes;
};
struct vst_contact {uint16_t x,y;uint8_t id,type,tip,confidence;};
struct vst_state {
    struct vst_contact contacts[VST_CONTACTS];
    uint16_t active;
    uint8_t super_resolution,invert_x,invert_y;
    uint32_t events,invalid,resets,sequence;
};
struct vst_hid_state {uint16_t active;struct vst_contact contacts[VST_CONTACTS];};
typedef void (*vst_publish_fn)(void *,const struct vst_state *);
int vst_firmware_parse(const uint8_t *,size_t,struct vst_firmware *);
int vst_identify(const struct vst_bus *,uint16_t expected_id,uint16_t *,uint16_t *);
int vst_start_scan(const struct vst_bus *);
typedef void (*vst_delay_ms_fn)(void *,unsigned);
int vst_wait_ready(const struct vst_bus *,vst_delay_ms_fn,void *,unsigned polls);
int vst_wait_scan_echo(const struct vst_bus *,vst_delay_ms_fn,void *,unsigned polls);
int vst_read_fifo(const struct vst_bus *,uint8_t out[VST_FIFO_DEPTH*VST_EVENT_BYTES],size_t *events);
void vst_state_init(struct vst_state *,int super_resolution,int invert_x,int invert_y);
int vst_process_events(struct vst_state *,const uint8_t *,size_t,vst_publish_fn,void *);
void vst_release_all(struct vst_state *,vst_publish_fn,void *);
// Actual10-contact HID report: explicit tip-up at previous coordinates, without
// rescaling by the UI point scale. On send failure the caller retains prior state.
int vst_hid_report(const struct vst_state *,const struct vst_hid_state *,uint8_t out[62],struct vst_hid_state *next);
// Bridge into the retained ShengHidInput consumer's exclusive axis maxima.
// That consumer emits confident finger contacts only; exclude palms/hover here.
unsigned vst_native_contacts(const struct vst_state *,int xs[12],int ys[12],int ids[12]);
#ifdef __cplusplus
}
#endif
