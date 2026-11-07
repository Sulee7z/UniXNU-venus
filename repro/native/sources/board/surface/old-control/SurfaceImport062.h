/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include "SurfaceImport062Core.h"
#ifndef SURFACE062_HOST_TEST
#include <pexpert/pexpert.h>
#include <vm/vm_shared_region_internal.h>
extern int proc_selfpid(void);
extern void proc_selfname(char *buf, int size);
#endif

static unsigned surface062_samples;
static volatile uint32_t surface062_repaired, surface062_rejected;

static int surface062_user_read(void *opaque, uint64_t address, void *buffer, size_t bytes)
{
    (void)opaque;
    return copyin((user_addr_t)address, buffer, bytes);
}
static int surface062_user_write(void *opaque, uint64_t address, const void *buffer, size_t bytes)
{
    (void)opaque;
    return copyout(buffer, (user_addr_t)address, bytes);
}

static bool venus_surface_import062(arm_saved_state_t *state, uint64_t esr)
{
    if (!state || !is_saved_state64(state) || PSR64_IS_KERNEL(get_saved_state_cpsr(state)) ||
        ((esr >> 26) & 63) != ESR_EC_BRK_AARCH64 || ((uint32_t)esr & 0xffff) != SURFACE062_IMMEDIATE)
        return false;
    vm_shared_region_t region = vm_shared_region_get(current_task());
    if (!region) return false;
    mach_vm_offset_t cache = 0;
    kern_return_t status = vm_shared_region_start_address(region, &cache);
    vm_shared_region_deallocate(region);
    uint64_t pc = get_saved_state_pc(state);
    uint32_t word = 0;
    if (status != KERN_SUCCESS || copyin((user_addr_t)pc, &word, sizeof(word)) ||
        !surface062_match(cache, pc, (uint32_t)esr & 0xffff, word)) return false;
    unsigned enabled = 0;
    PE_parse_boot_argn("venus-surface-import", &enabled, sizeof(enabled));
    char name[32] = {0};
    proc_selfname(name, sizeof(name));
    struct surface062_io io = {.opaque = NULL, .read = surface062_user_read, .write = surface062_user_write};
    struct surface062_result result = surface062_repair(&io, enabled == 1, strcmp(name, "backboardd") == 0,
        cache, get_saved_state_reg(state, 20), get_saved_state_reg(state, 0));
    if (result.verified) __atomic_fetch_add(&surface062_repaired, 1, __ATOMIC_RELAXED);
    if (result.reason >= SURFACE062_INVALID) __atomic_fetch_add(&surface062_rejected, 1, __ATOMIC_RELAXED);
    unsigned sample = __atomic_load_n(&surface062_samples, __ATOMIC_RELAXED);
    while (result.reason != SURFACE062_PASS && sample < 128) {
        if (__atomic_compare_exchange_n(&surface062_samples, &sample, sample + 1, false,
                __ATOMIC_RELAXED, __ATOMIC_RELAXED)) {
            printf("SURF062: pid=%d reason=%u committed=%u verified=%u ctx=0x%llx vptr=0x%llx import=0x%llx surface=0x%llx ref=%u flags=0x%x state=0x%x next=0x%llx head=0x%llx owner=0x%llx nodes=%u pc=0x%llx\n",
                proc_selfpid(), result.reason, result.committed, result.verified,
                (unsigned long long)result.context, (unsigned long long)result.vptr,
                (unsigned long long)result.import, (unsigned long long)result.surface,
                result.references, result.flags, result.state_flags,
                (unsigned long long)result.next, (unsigned long long)result.head,
                (unsigned long long)result.owner, result.nodes, (unsigned long long)pc);
            break;
        }
    }
    set_user_saved_state_reg(state, 23, get_saved_state_reg(state, 0));
    set_user_saved_state_pc(state, pc + 4);
    return true;
}
