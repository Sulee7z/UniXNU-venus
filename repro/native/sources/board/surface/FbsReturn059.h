/* Diagnostic only: observe original23F84 returns, then replay original code. */
#pragma once
#ifndef FBS059_HOST_TEST
#include <pexpert/pexpert.h>
#include <vm/vm_shared_region_internal.h>
/* Match sys/proc.h's public ABI without importing BSD proc layout into sleh. */
extern int proc_selfpid(void);
extern void proc_selfname(char *buf, int size);
#endif
#include "FbsReturn059Core.h"
#include "FbsProbe059Sites.h"

struct fbs059_context {
    int pid;
    uint64_t proxy_id, proxy_url;
    uint32_t generic[FBS059_COUNT], focused[FBS059_COUNT];
};
static struct fbs059_context fbs059_contexts[8];

static bool
fbs059_take_sample(uint32_t *counter, uint32_t limit, uint32_t *sample)
{
    uint32_t value = __atomic_load_n(counter, __ATOMIC_RELAXED);
    while (value < limit) {
        if (__atomic_compare_exchange_n(counter, &value, value + 1, false,
                __ATOMIC_RELAXED, __ATOMIC_RELAXED)) {
            *sample = value;
            return true;
        }
    }
    return false;
}

static struct fbs059_context *
fbs059_context(int pid)
{
    for (unsigned i = 0; i < 8; ++i) {
        if (__atomic_load_n(&fbs059_contexts[i].pid, __ATOMIC_ACQUIRE) == pid) {
            return &fbs059_contexts[i];
        }
    }
    for (unsigned i = 0; i < 8; ++i) {
        int empty = 0;
        if (__atomic_compare_exchange_n(&fbs059_contexts[i].pid, &empty, pid, false,
                __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE) || empty == pid) {
            return &fbs059_contexts[i];
        }
    }
    return NULL;
}

static bool
venus_fbs059_probe(arm_saved_state_t *state, uint64_t esr)
{
    unsigned enabled = 0;
    if (!state || !is_saved_state64(state) || PSR64_IS_KERNEL(get_saved_state_cpsr(state)) ||
        ((esr >> 26) & 63) != ESR_EC_BRK_AARCH64 ||
        !PE_parse_boot_argn("venus-fbs-trace", &enabled, sizeof(enabled)) || enabled != 1) {
        return false;
    }
    uint32_t immediate = (uint32_t)esr & 0xffff;
    if (immediate < FBS059_BRK_FIRST || immediate >= FBS059_BRK_FIRST + FBS059_COUNT) {
        return false;
    }
    mach_vm_offset_t cache = 0;
    vm_shared_region_t region = vm_shared_region_get(current_task());
    if (!region) {
        return false;
    }
    kern_return_t result = vm_shared_region_start_address(region, &cache);
    vm_shared_region_deallocate(region);
    if (result != KERN_SUCCESS) {
        return false;
    }
    uint64_t pc = get_saved_state_pc(state);
    int index = fbs059_match(fbs059_sites, FBS059_COUNT, immediate, cache, pc);
    uint32_t actual = 0;
    if (index < 0 || copyin((user_addr_t)pc, &actual, sizeof(actual)) ||
        actual != (UINT32_C(0xd4200000) | (immediate << 5))) {
        return false;
    }
    uint64_t registers[29];
    for (unsigned i = 0; i < 29; ++i) {
        registers[i] = get_saved_state_reg(state, i);
    }
    struct fbs059_effect effect;
    if (!fbs059_effect(fbs059_sites[index].word, pc, registers, &effect)) {
        return false;
    }
    char process_name[32] = {0};
    proc_selfname(process_name, sizeof(process_name));
    if (strcmp(process_name, "SpringBoard") == 0) {
        int pid = proc_selfpid();
        struct fbs059_context *context = fbs059_context(pid);
        if (context) {
            if (index == 0) __atomic_store_n(&context->proxy_id, effect.value, __ATOMIC_RELEASE);
            if (index == 4) __atomic_store_n(&context->proxy_url, effect.value, __ATOMIC_RELEASE);
            uint64_t id = __atomic_load_n(&context->proxy_id, __ATOMIC_ACQUIRE);
            uint64_t url = __atomic_load_n(&context->proxy_url, __ATOMIC_ACQUIRE);
            bool focused = false;
            if (index >= 9 && index <= 12) {
                for (unsigned reg = 19; reg < 29; ++reg) {
                    if ((id && registers[reg] == id) || (url && registers[reg] == url)) focused = true;
                }
            }
            uint32_t *counter = focused ? &context->focused[index] : &context->generic[index];
            unsigned limit = focused || index < 9 || index > 12 ? 32 : 8;
            uint32_t sample = 0;
            if (fbs059_take_sample(counter, limit, &sample)) {
                int state_reg = fbs059_sites[index].state_reg;
                uint64_t state_pointer = state_reg >= 0 && state_reg < 29 ? registers[state_reg] : 0;
                uint64_t words[4] = {0};
                int error = state_pointer ? copyin((user_addr_t)state_pointer, words, sizeof(words)) : -1;
                printf("FBS059: pid=%d stage=%s sample=%u focus=%u pc=0x%llx value=0x%llx next=0x%llx state=0x%llx read=%d words=0x%llx/0x%llx/0x%llx/0x%llx\n",
                    pid, fbs059_sites[index].label, sample, focused, pc, effect.value, effect.next_pc,
                    state_pointer, error, words[0], words[1], words[2], words[3]);
                printf("FBS059: pid=%d stage=%s x19-28=0x%llx/0x%llx/0x%llx/0x%llx/0x%llx/0x%llx/0x%llx/0x%llx/0x%llx/0x%llx\n",
                    pid, fbs059_sites[index].label, registers[19], registers[20], registers[21], registers[22],
                    registers[23], registers[24], registers[25], registers[26], registers[27], registers[28]);
            }
        }
    }
    /* Every process maps the shared cache. Non-SpringBoard users must replay
     * these exact instructions as well, without logging or forcing returns. */
    if (effect.destination >= 0) {
        set_user_saved_state_reg(state, (unsigned)effect.destination, effect.value);
    }
    set_user_saved_state_pc(state, effect.next_pc);
    return true;
}
