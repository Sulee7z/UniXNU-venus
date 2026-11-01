// SPDX-License-Identifier: MIT
// Caller supplies serialization. Keep failures separate from ordinary exits so
// successful short-lived helpers cannot erase the last useful crash records.
#ifndef SHENG_BOOT_PROGRESS_LIFECYCLE_H
#define SHENG_BOOT_PROGRESS_LIFECYCLE_H
#include <string.h>
struct bp_exits {
 unsigned total,failed,crashes;
 char recent[4][120],failures[3][120],crash[3][400];
 unsigned first_mode_set;
 char first_mode[400];
 char reason[330];
 char thrown[330];
};
static void bp_exit_add(struct bp_exits *e,int pid,const char *name,int status,
                        unsigned ns,uint64_t code) {
 char *row=e->recent[e->total++%4];
 unsigned signal=(unsigned)status&127,exit_code=((unsigned)status>>8)&255;
 snprintf(row,120,"p%d %.24s status=%x sig=%u exit=%u ns=%u sub=%llx",
          pid,name,(unsigned)status,signal,exit_code,ns,(unsigned long long)code);
 if(signal>=3 && signal<=12 && signal!=9)snprintf(e->crash[e->crashes++%3],400,"%s",row);
 if(status || ns) {
  char *bad=e->failures[e->failed++%3];
  snprintf(bad,120,"%s",row);
 }
}
// The ordinary diagnostic page has no UI trace or post-scanout crash banner.
// Show the newest retained crash there, including its tail (cache slide/BT),
// without reading beyond a short record or leaving stale sample rows behind.
static void bp_exit_crash_row(const struct bp_exits *e,unsigned part,char out[120]) {
 out[0]=0;
 if(!e->crashes || part>=4)return;
 const char *text=e->crash[(e->crashes-1)%3];
 unsigned length=0;
 while(length<sizeof(e->crash[0]) && text[length])++length;
 unsigned start=part*100;
 if(start>=length)return;
 unsigned count=length-start;if(count>100)count=100;
 snprintf(out,120,"CRASH %u/4 %.*s",part+1,(int)count,text+start);
}
// Keep the first SpringBoard FBSDisplayMode rejection for the whole boot so a
// later watchdogd/daemon crash cannot push it off the page.
static int bp_exit_keep_first_mode(struct bp_exits *e,const char *row) {
 if(e->first_mode_set || !row)return 0;
 unsigned long rowlen=strnlen(row,sizeof(e->first_mode));
 if(!strnstr(row,"SpringBoard sig5",rowlen) || !strnstr(row," MODE ",rowlen))return 0;
 snprintf(e->first_mode,sizeof(e->first_mode),"%s",row);
 e->first_mode_set=1;
 return 1;
}
static void bp_exit_mode_row(const struct bp_exits *e,unsigned part,char out[120]) {
 out[0]=0;
 if(!e->first_mode_set || part>=4)return;
 unsigned length=0;
 while(length<sizeof(e->first_mode) && e->first_mode[length])++length;
 unsigned start=part*100;
 if(start>=length)return;
 unsigned count=length-start;if(count>100)count=100;
 snprintf(out,120,"MODE %u/4 %.*s",part+1,(int)count,e->first_mode+start);
}
#endif