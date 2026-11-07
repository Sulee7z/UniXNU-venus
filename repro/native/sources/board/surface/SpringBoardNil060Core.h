/* SPDX-License-Identifier: BSD-2-Clause-Patent */
/* One pinned23F84 call-site guard; never changes NSSet's global nil rules. */
#pragma once
#include <stdbool.h>
#include <stdint.h>

#define SB060_BASE UINT64_C(0x180000000)
#define SB060_CALL UINT64_C(0x223db9cf0)
#define SB060_TARGET UINT64_C(0x224994140)
#define SB060_WORD UINT32_C(0x942f6914)
#define SB060_IMMEDIATE UINT32_C(0x6000)
#define SB060_TRAP UINT32_C(0xd42c0000)
#define SB060_USER_TOP UINT64_C(0x1000000000000)

struct sb060_effect {
    uint64_t next_pc, lr;
    bool writes_lr, skipped_nil;
};

static inline bool
sb060_effect(uint64_t cache, uint64_t pc, uint32_t immediate, uint32_t actual,
    bool enabled, bool springboard, uint64_t argument, struct sb060_effect *out)
{
    if (!out || immediate != SB060_IMMEDIATE || actual != SB060_TRAP ||
        cache < SB060_BASE || cache - SB060_BASE > UINT64_C(0x100000000) ||
        pc & 3 || pc >= SB060_USER_TOP - 4 ||
        cache + (SB060_CALL - SB060_BASE) != pc ||
        cache + (SB060_TARGET - SB060_BASE) >= SB060_USER_TOP) {
        return false;
    }
    bool skip = enabled && springboard && argument == 0;
    *out = (struct sb060_effect){
        .next_pc = skip ? pc + 4 : cache + (SB060_TARGET - SB060_BASE),
        .lr = pc + 4,
        .writes_lr = !skip,
        .skipped_nil = skip,
    };
    return true;
}
