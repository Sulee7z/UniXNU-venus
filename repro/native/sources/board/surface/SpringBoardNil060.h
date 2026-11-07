/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include "SpringBoardNil060Core.h"
#ifndef SB060_HOST_TEST
#include <pexpert/pexpert.h>
#include <vm/vm_shared_region_internal.h>
extern int proc_selfpid(void);
extern void proc_selfname(char *buf, int size);
#endif

static unsigned sb060_samples;

static bool
venus_springboard_nil060(arm_saved_state_t *state, uint64_t esr)
{
    if (!state || !is_saved_state64(state) ||
        PSR64_IS_KERNEL(get_saved_state_cpsr(state)) ||
        ((esr >> 26) & 63) != ESR_EC_BRK_AARCH64 ||
        ((uint32_t)esr & 0xffff) != SB060_IMMEDIATE) {
        return false;
    }
    vm_shared_region_t region = vm_shared_region_get(current_task());
    if (!region) return false;
    mach_vm_offset_t cache = 0;
    kern_return_t status = vm_shared_region_start_address(region, &cache);
    vm_shared_region_deallocate(region);
    uint64_t pc = get_saved_state_pc(state);
    if (status != KERN_SUCCESS || cache < SB060_BASE ||
        cache - SB060_BASE > UINT64_C(0x100000000) ||
        pc != cache + (SB060_CALL - SB060_BASE)) {
        return false;
    }
    uint32_t actual = 0;
    if (copyin((user_addr_t)pc, &actual, sizeof(actual))) return false;
    unsigned enabled = 0;
    PE_parse_boot_argn("venus-sb-nil", &enabled, sizeof(enabled));
    char name[32] = {0};
    proc_selfname(name, sizeof(name));
    struct sb060_effect effect;
    if (!sb060_effect(cache, pc, (uint32_t)esr & 0xffff, actual,
            enabled == 1, strcmp(name, "SpringBoard") == 0,
            get_saved_state_reg(state, 2), &effect)) {
        return false;
    }
    unsigned sample = __atomic_load_n(&sb060_samples, __ATOMIC_RELAXED);
    while (effect.skipped_nil && sample < 32) {
        if (__atomic_compare_exchange_n(&sb060_samples, &sample, sample + 1,
                false, __ATOMIC_RELAXED, __ATOMIC_RELAXED)) {
            printf("SB060: pid=%d skipped-system-info-nil=1 pc=0x%llx next=0x%llx sample=%u\n",
                proc_selfpid(), pc, effect.next_pc, sample);
            break;
        }
    }
    /* A normal BL writes only LR and PC. A skipped void call writes neither
     * argument/return registers nor LR; the next original instruction runs. */
    if (effect.writes_lr) set_user_saved_state_lr(state, effect.lr);
    set_user_saved_state_pc(state, effect.next_pc);
    return true;
}
