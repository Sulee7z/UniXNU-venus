#!/usr/bin/env python3
"""Exercise the actual Venus fault recorder and ordinary diagnostic-page layout."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

DEVICE = Path(__file__).resolve().parents[1]
SOURCE = DEVICE / 'package/boot-progress'
OUT = DEVICE.parents[1] / 'artifacts/venus-exit-fault-checks'
OUT.mkdir(parents=True, exist_ok=True)
fault = (SOURCE / 'BootFaultProbe.c').read_text()
progress = (SOURCE / 'BootProgress.c').read_text()
fault_body = fault[fault.index('struct boot_fault_record'):fault.index('// REASON-SCAN')]
layout_start = progress.index('  if(!__atomic_exchange_n(&exit_lock')
layout_body = progress[layout_start:progress.index('  if(&boot_process_rows)', layout_start)]

# Match Darwin's printf argument types while compiling the real C bodies on
# Linux. Kernel APIs are explicit stand-ins; these are not hardware tests.
common = r'''
#include <stdio.h>
#include <string.h>
#include <assert.h>
typedef unsigned long long uint64_t;
typedef long long int64_t;
typedef unsigned int uint32_t;
typedef __UINTPTR_TYPE__ uintptr_t;
#include "BootFrontBoardMode.h"
'''
fault_prefix = common + r'''
struct user64_dyld_all_image_infos {unsigned version,infoArrayCount;uint64_t infoArray;};
struct user64_dyld_image_info {uint64_t imageLoadAddress,imageFilePath,imageFileModDate;};
static struct user64_dyld_all_image_infos infos;
#define task_get_all_image_info_addr(t) ((uint64_t)(uintptr_t)&infos)
typedef struct {uint64_t pc,lr,sp,fp,x[29];} arm_saved_state_t;
#define get_saved_state_pc(s) ((s)->pc)
#define get_saved_state_lr(s) ((s)->lr)
#define get_saved_state_sp(s) ((s)->sp)
#define get_saved_state_fp(s) ((s)->fp)
#define get_saved_state_reg(s,i) ((s)->x[i])
static struct {uint64_t task_shared_region_slide;} task;
static arm_saved_state_t *fallback;
#define current_task() (&task)
#define current_thread() ((void *)0)
#define find_user_regs(t) fallback
#define is_saved_state64(s) 1
static int pid=174,copycalls,copyfail;
static int proc_selfpid(void){return pid;}
static void proc_selfname(char *p,int n){snprintf(p,(unsigned)n,"SpringBoard");}
static int copyin(uint64_t p,void *out,unsigned long n){
 ++copycalls;if(copyfail||p<4096)return 14;memcpy(out,(void *)(uintptr_t)p,n);return 0;
}
static int copyinstr(uint64_t p,char *out,unsigned long n,unsigned long *actual){
 ++copycalls;if(copyfail||p<4096)return 14;
 unsigned long z=strlen((char *)(uintptr_t)p)+1;if(z>n)return 63;
 memcpy(out,(void *)(uintptr_t)p,z);*actual=z;return 0;
}
'''
fault_main = r'''
int main(void){
 char out[400]="exit summary";
 boot_progress_exit_fault(pid,5,out,sizeof out);assert(!strcmp(out,"exit summary")&&!copycalls);
 _Alignas(16) uint64_t stack[2]={0,0x100006830};
 arm_saved_state_t saved={.pc=0x100012340,.lr=0x100045670,.fp=(uintptr_t)stack};
 task.task_shared_region_slide=0x1234000;
 boot_progress_user_breakpoint(&saved,0xf2000001);
 assert(!copycalls&&fault_count==1);
 saved.pc=0x100099990; // A later different-class fault must not replace the SIGTRAP context.
 boot_progress_user_abort(&saved,0x92000006,0xdeadbeef);assert(!copycalls);
 boot_progress_exit_fault(pid,5,out,sizeof out);
 assert(strstr(out,"SpringBoard sig5 src=EL0 PC100012340"));
 assert(strstr(out,"LR100045670 Ef2000001 F0 +1234000 bt 100006830"));
 boot_progress_exit_fault(pid,11,out,sizeof out);
 assert(strstr(out,"sig11 src=EL0 PC100099990")&&strstr(out,"Fdeadbeef"));
 int before=copycalls;pid=999;strcpy(out,"prior");
 boot_progress_exit_fault(pid,5,out,sizeof out);assert(!strcmp(out,"prior")&&copycalls==before);
 fallback=&saved;boot_progress_exit_fault(pid,5,out,sizeof out);
 assert(strstr(out,"sig5 src=EXIT")&&!strstr(out,"src=EL0"));fallback=0;
 // An exception in another process is never read through the current map.
 before=copycalls;boot_progress_exit_fault(174,5,out,sizeof out);assert(copycalls==before);
 pid=174;copyfail=1;boot_progress_exit_fault(pid,5,out,sizeof out);
 assert(strstr(out,"src=EL0")&&!strstr(out,"bt 100006830"));copyfail=0;
 struct {char text[24];char guard[16];} bounded;
 memset(&bounded,'Z',sizeof bounded);
 boot_progress_exit_fault(pid,5,bounded.text,sizeof bounded.text);
 assert(bounded.text[23]==0);for(unsigned i=0;i<16;++i)assert(bounded.guard[i]=='Z');
 fault_lock=1;unsigned count=fault_count;boot_progress_user_breakpoint(&saved,0xf2000001);
 strcpy(out,"contended");boot_progress_exit_fault(pid,5,out,sizeof out);
 assert(fault_count==count&&!strcmp(out,"contended"));fault_lock=0;
 for(unsigned i=0;i<8;++i){pid=300+(int)i;boot_progress_user_breakpoint(&saved,0xf2000001);}
 pid=174;strcpy(out,"overwritten");boot_progress_exit_fault(pid,5,out,sizeof out);
 assert(!strcmp(out,"overwritten"));
 // A SIGTRAP with only a data-abort record has no matching exception context.
 boot_progress_user_abort(&saved,0x92000006,0xdeadbeef);
 strcpy(out,"signal summary");boot_progress_exit_fault(pid,5,out,sizeof out);
 assert(!strcmp(out,"signal summary"));
  // Exact FrontBoardServices failure only: preserve invalid values from the
  // original x19 object, even if later saved registers have changed.
  struct bp_fbs_mode mode={.width=1440,.height=3200,.preferred_scale=2,
    .scale_override_bits=0x3ff0000000000000ULL,.refresh_rate_bits=0,
    .gamut=-1,.hdr=2,.rotation=0,.virtual_display=0};
  saved.pc=0x19f3d0744ULL+task.task_shared_region_slide;saved.lr=saved.pc;saved.fp=0;
  saved.x[19]=(uintptr_t)&mode;
  before=copycalls;boot_progress_user_breakpoint(&saved,0xf2000000);assert(copycalls==before);
  saved.x[19]=0;
  boot_progress_exit_fault(pid,5,out,sizeof out);
  assert(strstr(out,"MODE w=1440 h=3200 p=2 so=3ff0000000000000 hz=0 g=-1 hdr=2 r=0 v=0"));
  assert(copycalls==before+1);
  copyfail=1;boot_progress_exit_fault(pid,5,out,sizeof out);copyfail=0;
  assert(strstr(out,"MODE copyerr=14")&&!strstr(out,"w=1440"));
  before=copycalls;boot_progress_exit_fault(pid,5,bounded.text,sizeof bounded.text);
  assert(copycalls==before&&bounded.text[23]==0);
  for(unsigned i=0;i<16;++i)assert(bounded.guard[i]=='Z');
  assert(!bp_fbs_mode_fault(saved.pc+4,task.task_shared_region_slide,0xf2000000,"SpringBoard"));
  assert(!bp_fbs_mode_fault(saved.pc,task.task_shared_region_slide,0xf2000001,"SpringBoard"));
  assert(!bp_fbs_mode_fault(saved.pc,task.task_shared_region_slide,0xf2000000,"watchdogd"));
  puts("PASS: actual recorder, immutable EL0 snapshot, SIGTRAP class match, EXIT fallback, PID/map isolation, contention, copy failure, ring overwrite, exact FBS-mode gate and output bounds");
}
'''
layout_prefix = common + r'''
#include "BootProgressCore.h"
#include "BootProgressLifecycle.h"
#define BP_BAR_SECTION 1
static struct bp_exits exit_records,exit_snapshot;
static unsigned exit_lock,exit_dropped,boot_ui_trace_ready;
static uint32_t native_legacy_frame_count,native_legacy_frame_colors[8][4];
static uint64_t native_legacy_frame_color_counts[8][4],native_legacy_frame_color_other[8];
static char boot_ui_trace_rows[14][120],boot_ui_trace_label[120];
struct pc_sample {unsigned second;int pid;char name[16];uint64_t pc,psr;};
static struct pc_sample samples[8];static unsigned sample_count;
static unsigned writes[48];static char final[48][120];
static void line(unsigned row,const char *text,uint32_t color){
 (void)color;assert(row<48);++writes[row];snprintf(final[row],120,"%s",text);
}
static void bar(unsigned row,const char *text,uint32_t color,uint32_t background){
 (void)background;line(row,text,color);
}
static void layout(struct bp_core *visible){char b[120];
'''
layout_main = r'''
}
int main(void){
 struct bp_core core={0};layout(&core);assert(strstr(final[12],"PC "));
 bp_exit_add(&exit_records,174,"SpringBoard",5,2,5);
 char expected[400];memset(expected,'A',sizeof expected);expected[399]=0;
 const char *head="p174 SpringBoard sig5 src=EL0 PC100012340 ";
 const char *tail="TAIL-BACKTRACE-100045670";
 memcpy(expected,head,strlen(head));memcpy(expected+360,tail,strlen(tail));
 memcpy(exit_records.crash[0],expected,sizeof expected);
 // Ordinary successes and SIGKILL failures must not displace the crash record.
 for(unsigned i=0;i<1000;++i){
  bp_exit_add(&exit_records,200+(int)i,"helper",0,0,0);
  bp_exit_add(&exit_records,2200+(int)i,"helper",9,2,9);
 }
 memset(writes,0,sizeof writes);layout(&core);
 char joined[401]={0};
 for(unsigned i=0;i<4;++i){
  assert(writes[12+i]==1&&strlen(final[12+i])<120);
  assert(!strncmp(final[12+i],"CRASH ",6));strcat(joined,final[12+i]+10);
 }
 assert(!strcmp(joined,expected)&&strstr(joined,"TAIL-BACKTRACE-100045670"));
 // A short new record clears the three obsolete continuation rows.
 for(unsigned i=0;i<4;++i)bp_exit_add(&exit_records,4000+(int)i,"latest",5,2,5);
 layout(&core);assert(strstr(final[12],"p4003 latest"));
 for(unsigned i=13;i<16;++i)assert(!final[i][0]);
 // Bounded wrapping also handles a completely full, unterminated source slot.
 memset(exit_records.crash[(exit_records.crashes-1)%3],'Z',400);
 struct {char text[120];char guard[16];} bounded;memset(&bounded,'G',sizeof bounded);
 bp_exit_crash_row(&exit_records,3,bounded.text);assert(strlen(bounded.text)==110);
 for(unsigned i=0;i<16;++i)assert(bounded.guard[i]=='G');
 bp_exit_crash_row(&exit_records,4,bounded.text);assert(!bounded.text[0]);
 exit_records.crash[(exit_records.crashes-1)%3][399]=0;
 // Existing UI-trace mode must retain its own middle-page rows.
 boot_ui_trace_ready=1;
 for(unsigned i=0;i<14;++i)snprintf(boot_ui_trace_rows[i],120,"TRACE %u",i);
 strcpy(boot_ui_trace_label,"STACK64 1/2");memset(writes,0,sizeof writes);
 layout(&core);
 for(unsigned i=6;i<20;++i)assert(writes[i]==1&&!strcmp(final[i],boot_ui_trace_rows[i-6]));
 assert(!strcmp(final[20],boot_ui_trace_label));
 // Snapshot contention retains the last coherent page without reading live data.
 exit_lock=1;boot_ui_trace_ready=0;struct bp_exits snapshot=exit_snapshot;
 layout(&core);assert(!memcmp(&snapshot,&exit_snapshot,sizeof snapshot));
 puts("PASS: actual ordinary-page layout exposes full crash/backtrace without UI driver, survives 2000 normal/kill exits, clears stale rows, bounds wrapping and preserves UI-trace/snapshot behavior");
}
'''

results = {}
for name, code in [('fault', fault_prefix + fault_body + fault_main),
                   ('layout', layout_prefix + layout_body + layout_main)]:
    source, binary = OUT / f'{name}.c', OUT / name
    source.write_text(code)
    # Existing upstream code uses compact multi-statement lines and copies
    # between distinct arrays within bp_exits; GCC diagnoses their common base
    # as possible restrict overlap. ASan/UBSan still check the executed copies.
    subprocess.run([os.environ.get('CC', 'gcc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-function', '-Wno-address',
                    '-Wno-misleading-indentation', '-Wno-restrict',
                    '-O1', '-g', '-fno-pie', '-no-pie', '-fsanitize=address,undefined',
                    '-I', str(SOURCE), str(source), '-o', str(binary)], check=True, timeout=60)
    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=20)
    print(result.stdout, end='')
    print(result.stderr, end='', file=sys.stderr)
    result.check_returncode()
    results[name] = result.stdout.strip()
(OUT / 'report.json').write_text(json.dumps({
    'passed': True,
    'checks': results,
    'sources': {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest()
                for name in ['BootProgress.c', 'BootFaultProbe.c', 'BootProgressLifecycle.h', 'BootFrontBoardMode.h']},
    'kernel_api_and_pixel_stores_substituted': True,
    'hardware_observed': False,
}, indent=2) + '\n')
