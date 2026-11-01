#!/usr/bin/env python3
"""Exercise Venus's actual row gate, GPU layout and framebuffer painter on Linux."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import subprocess

DEVICE = Path(__file__).resolve().parents[1]
SOURCE = DEVICE / 'package/boot-progress'
FONT = DEVICE.parent / 'uefi-venus/Silicon/Silicium/SiliciumPkg/Library/FrameBufferSerialPortLib'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=DEVICE.parents[1]/'artifacts/venus-a660-live-checks')
OUT=parser.parse_args().output
OUT.mkdir(parents=True, exist_ok=True)
progress = (SOURCE / 'BootProgress.c').read_text()
start = progress.index('static void capture(unsigned row,')
end = progress.index('// Title bar and section headings:', start)
body = progress[start:end]
data_line = 'if(venus_data_check_phase)line(38,venus_data_check_row,0xff66e0ff);'
assert progress.count(data_line)==1
body += '\nstatic void draw_data(void) { '+data_line+' }\n'
detail_line='if(venus_data_check_phase)for(unsigned i=0;i<3;++i)line(24+i,venus_data_check_detail[i],0xff66e0ff);'
assert progress.count(detail_line)==1
body+='\nstatic void draw_data_details(void) { '+detail_line+' }\n'
assert 'draw_gpu(now);' in progress[progress.index('static void draw(unsigned now)'):progress.index('static void refresh(unsigned now)')]
prefix = r'''
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include "BootProgressCore.h"
#include "BootProgressDisplay.h"
static struct bp_display display;
static struct {unsigned ready;} pulse;
static char boot_progress_page_text[48][BP_COLS];
extern char boot_process_rows[10][120] __attribute__((weak));
static volatile uint32_t native_gpu_power_stage, native_legacy_gpu_probe_calls;
static volatile uint32_t native_keyevents_stage, native_aks_opens, native_aks_calls;
static volatile int native_keyevents_status;
static volatile uint32_t native_hid_stage, native_hid_resource_found, native_cpufreq_stage;
static volatile int native_hid_load_status, native_hid_matching_load_status, native_hid_input_meta_status;
static volatile uint32_t native_hid_input_events[8];
static volatile int native_hid_input_results[8];
static volatile unsigned venus_data_check_phase;
static char venus_data_check_row[120];
static char venus_data_check_detail[3][120];
static volatile unsigned venus_gestalt_requested,venus_gestalt_moved,venus_gestalt_missing;
static volatile int venus_gestalt_status=-1;
static unsigned format_calls;
static void native_gpu_diagnostic_row(unsigned row,char *out,size_t n) {
  ++format_calls;snprintf(out,n,"A660 retained row=%u stage=%x",row,native_gpu_power_stage);
}
static int PE_parse_boot_argn(const char *name,void *out,unsigned n) {
  assert(!strcmp(name,"sheng-gpu-power")&&n==sizeof(unsigned));*(unsigned *)out=9;return 1;
}
'''
main = r'''
enum { Width=1440, Height=720, Stride=Width+16 };
static uint32_t pixels[Height][Stride], saved[Height][Stride];
static void setup(void) {
  for(unsigned y=0;y<Height;++y)for(unsigned x=0;x<Stride;++x)pixels[y][x]=0x12345678;
  display=(struct bp_display){.frame=(uintptr_t)pixels,.bound=1,.width=Width,.height=Height,.stride=Stride*4,.scale=1};
}
int main(void) {
  setup();
#ifdef PROCESS_LINKED
  strcpy(boot_process_rows[0],"existing process");
  line(24,boot_process_rows[0],1);memcpy(saved,pixels,sizeof pixels);draw_gpu(5);
  assert(!format_calls&&!memcmp(saved,pixels,sizeof pixels));
  puts("PASS: linked process rows retain ownership; GPU layout does not overwrite them");
#else
  assert(!&boot_process_rows);
  // Reproduce the original defect using the real row gate and pixel writer.
  line(47,"GPU stage=0",1);memcpy(saved,pixels,sizeof pixels);pulse.ready=1;
  line(47,"GPU stage=77",1);
  assert(!strcmp(boot_progress_page_text[47],"GPU stage=77"));
  assert(!memcmp(saved,pixels,sizeof pixels)); // Capture changed; pixels did not.
  draw_gpu(0);memcpy(saved,pixels,sizeof pixels);
  native_gpu_power_stage=0x77;native_legacy_gpu_probe_calls=1;draw_gpu(12);
  for(unsigned row=24;row<30;++row) {
    assert(strstr(boot_progress_page_text[row],"stage=77"));
    assert(memcmp(saved+row*14,pixels+row*14,14*sizeof pixels[0]));
  }
  assert(strstr(boot_progress_page_text[41],"t=12s stage=77 calls=1 requested-mode=9"));
  assert(strstr(boot_progress_page_text[39],"OS t=12s AKS="));
  assert(memcmp(saved+39*14,pixels+39*14,14*sizeof pixels[0]));
  assert(memcmp(saved+41*14,pixels+41*14,14*sizeof pixels[0]));
  assert(!memcmp(saved+47*14,pixels+47*14,14*sizeof pixels[0]));
  // Data qualification has a fixed, pulse-safe row and survives other text.
  memcpy(saved,pixels,sizeof pixels);draw_data();assert(!memcmp(saved,pixels,sizeof pixels));
  venus_data_check_phase=1;
  strcpy(venus_data_check_row,"DATA CHECK phase=1 step=11 rc=0 match=1 bytes=53");
  line(38,"SMP req=0",1);draw_data();
  assert(!strcmp(boot_progress_page_text[38],venus_data_check_row));
  line(12,"watchdogd sig5",1);draw_data();
  assert(!strcmp(boot_progress_page_text[38],venus_data_check_row));
  strcpy(venus_data_check_detail[0],"DATA DEV mount=1 parent=1 file=1");
  strcpy(venus_data_check_detail[1],"DATA IO w=1>20 fs=3 full=20");
  strcpy(venus_data_check_detail[2],"DATA SYNC file=0 dir=0 full=0 ufs=0");
  draw_data_details();
  for(unsigned i=0;i<3;++i)assert(!strcmp(boot_progress_page_text[24+i],venus_data_check_detail[i]));
  venus_gestalt_requested=1;venus_gestalt_status=0;venus_gestalt_moved=3;venus_gestalt_missing=4;
  memcpy(saved,pixels,sizeof pixels);draw_gpu(13);
  assert(strstr(boot_progress_page_text[29],"MG CACHE rc=0 moved=3 missing=4"));
  assert(memcmp(saved+29*14,pixels+29*14,14*sizeof pixels[0]));
  venus_gestalt_status=17;draw_gpu(14);assert(strstr(boot_progress_page_text[29],"MG CACHE rc=17"));
  venus_gestalt_requested=0;
  // Future cpufreq telemetry owns row 39 when enabled.
  native_cpufreq_stage=2;memcpy(saved,pixels,sizeof pixels);draw_gpu(13);
  assert(!memcmp(saved+39*14,pixels+39*14,14*sizeof pixels[0]));native_cpufreq_stage=0;
  for(unsigned y=0;y<Height;++y)for(unsigned x=Width;x<Stride;++x)assert(pixels[y][x]==0x12345678);
  // Once scanout requests the display, diagnostic rendering must stop storing.
  memcpy(saved,pixels,sizeof pixels);display.yield_requested=1;
  native_gpu_power_stage=0x9a;draw_gpu(13);draw_data();draw_data_details();assert(!memcmp(saved,pixels,sizeof pixels));
  display.yield_requested=0;display.bound=0;draw_gpu(14);draw_data();assert(!memcmp(saved,pixels,sizeof pixels));
  puts("PASS: old stale-pixel defect reproduced; six GPU rows and timestamp repaint after pulse anchoring; reserved row, padding and display yield preserved");
#endif
}
'''
results = {}
for name, extra in [('absent', ''), ('linked', 'char boot_process_rows[10][120];\n#define PROCESS_LINKED 1\n')]:
    source, binary = OUT / f'gpu-screen-{name}.c', OUT / f'gpu-screen-{name}'
    source.write_text(prefix + extra + body + main)
    subprocess.run([os.environ.get('CC', 'gcc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-function', '-Wno-address', '-O1', '-g', '-fno-pie', '-no-pie',
                    '-fsanitize=address,undefined', '-I', str(SOURCE), '-I', str(FONT), str(source), '-o', str(binary)], check=True)
    result = subprocess.check_output([str(binary)], text=True, timeout=20)
    print(result, end='')
    results[name] = result.strip()
(OUT / 'screen-report.json').write_text(json.dumps({
    'passed': True, 'checks': results,
    'source_sha256': {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest()
                      for name in ['BootProgress.c', 'BootProgressDisplay.h', 'BootProgressCore.h']},
    'font_sha256': hashlib.sha256((FONT / 'Font.h').read_bytes()).hexdigest(),
    'real_line_gate_and_pixel_writer': True, 'gpu_state_provider_substituted': True,
    'sanitizers': ['address', 'undefined'], 'hardware_observed': False,
}, indent=2) + '\n')
