/* Exact observation replay only. No application/policy decision is changed. */
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#define FBS059_ORIGINAL_BASE UINT64_C(0x180000000)
#define FBS059_USER_TOP UINT64_C(0x1000000000000)
#define FBS059_BRK_FIRST UINT32_C(0x5900)

struct fbs059_site {
    uint64_t pc;
    uint32_t word;
    int state_reg;
    const char *label;
};

struct fbs059_effect {
    int destination; /* -1: branch only */
    uint64_t value;
    uint64_t next_pc;
};

static inline int
fbs059_match(const struct fbs059_site *sites, size_t count, uint32_t immediate,
    uint64_t cache, uint64_t pc)
{
    if (!sites || immediate < FBS059_BRK_FIRST ||
        (uint64_t)(immediate - FBS059_BRK_FIRST) >= count ||
        cache < FBS059_ORIGINAL_BASE || cache - FBS059_ORIGINAL_BASE > UINT64_C(0x100000000) ||
        pc >= FBS059_USER_TOP || (pc & 3)) {
        return -1;
    }
    unsigned index = immediate - FBS059_BRK_FIRST;
    uint64_t original = sites[index].pc;
    if (original < FBS059_ORIGINAL_BASE || original - FBS059_ORIGINAL_BASE >= FBS059_USER_TOP - cache ||
        original - FBS059_ORIGINAL_BASE + cache != pc) {
        return -1;
    }
    return (int)index;
}

static inline bool
fbs059_effect(uint32_t word, uint64_t pc, const uint64_t registers[29],
    struct fbs059_effect *effect)
{
    if (!registers || !effect || (pc & 3) || pc >= FBS059_USER_TOP - 4) {
        return false;
    }
    struct fbs059_effect result = { .destination = -1, .value = 0, .next_pc = pc + 4 };
    if ((word & UINT32_C(0xffe0ffe0)) == UINT32_C(0xaa0003e0)) {
        unsigned source = (word >> 16) & 31, destination = word & 31;
        /* Do not replace Objective-C MOV x29,x29 return handshake markers. */
        if (source >= 29 || destination >= 29) {
            return false;
        }
        result.destination = (int)destination;
        result.value = registers[source];
    } else if ((word & UINT32_C(0xff000000)) == UINT32_C(0xb4000000)) {
        unsigned reg = word & 31;
        if (reg >= 29) {
            return false;
        }
        result.value = registers[reg];
        if (result.value == 0) {
            unsigned encoded = (word >> 5) & 0x7ffff;
            int64_t delta = ((int64_t)encoded - ((encoded & 0x40000) ? 0x80000 : 0)) * 4;
            if (delta < 0) {
                if (pc < (uint64_t)-delta) {
                    return false;
                }
                result.next_pc = pc - (uint64_t)-delta;
            } else {
                if ((uint64_t)delta >= FBS059_USER_TOP - pc) {
                    return false;
                }
                result.next_pc = pc + (uint64_t)delta;
            }
        }
    } else {
        return false;
    }
    *effect = result;
    return true;
}
