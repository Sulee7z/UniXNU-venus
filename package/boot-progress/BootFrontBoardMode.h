// SPDX-License-Identifier: MIT
// Read-only layout from the exact 21H461 FrontBoardServices class metadata,
// independently matched against the stores in the initializer at 19f3d0500.
// This is user-space object storage, not a kernel display-driver layout.
#ifndef VENUS_BOOT_FRONTBOARD_MODE_H
#define VENUS_BOOT_FRONTBOARD_MODE_H
#include <stddef.h>

struct bp_fbs_mode {
  uint64_t isa, width, height, preferred_scale;
  uint64_t scale_override_bits, refresh_rate_bits;
  int64_t gamut, hdr, rotation;
  unsigned char virtual_display, padding[7];
};
_Static_assert(sizeof(struct bp_fbs_mode)==80,"21H461 FBSDisplayMode extent");
_Static_assert(offsetof(struct bp_fbs_mode,width)==8,"FBS width");
_Static_assert(offsetof(struct bp_fbs_mode,height)==16,"FBS height");
_Static_assert(offsetof(struct bp_fbs_mode,preferred_scale)==24,"FBS preferredScale");
_Static_assert(offsetof(struct bp_fbs_mode,scale_override_bits)==32,"FBS scaleOverride");
_Static_assert(offsetof(struct bp_fbs_mode,refresh_rate_bits)==40,"FBS refreshRate");
_Static_assert(offsetof(struct bp_fbs_mode,gamut)==48,"FBS gamut");
_Static_assert(offsetof(struct bp_fbs_mode,hdr)==56,"FBS HDR");
_Static_assert(offsetof(struct bp_fbs_mode,rotation)==64,"FBS rotation");
_Static_assert(offsetof(struct bp_fbs_mode,virtual_display)==72,"FBS virtual");

static int bp_fbs_mode_fault(uint64_t pc,uint64_t slide,uint64_t esr,const char *name) {
  return pc>=slide && pc-slide==0x19f3d0744ULL && esr==0xf2000000ULL && !strcmp(name,"SpringBoard");
}
static int bp_fbs_mode_text(char *out,size_t cap,const struct bp_fbs_mode *m) {
  // Avoid floating-point instructions in the kernel. so/hz are IEEE-754 bits,
  // decoded on the host; keep error values rather than normalizing them.
  return snprintf(out,cap," MODE w=%llu h=%llu p=%llu so=%llx hz=%llx g=%lld hdr=%lld r=%lld v=%u",
    m->width,m->height,m->preferred_scale,m->scale_override_bits,m->refresh_rate_bits,
    m->gamut,m->hdr,m->rotation,(unsigned)m->virtual_display);
}
#endif
