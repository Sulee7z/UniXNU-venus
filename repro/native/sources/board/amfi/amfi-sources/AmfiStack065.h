/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include <kern/thread.h>
#include <stddef.h>

/* Input x8 is CE's allocated-frame SP. No additional stack is used.
 * Only x8/x9/x10 and flags change. CE retains its 128-byte refusal gate. */
__attribute__((naked, noinline, used)) void venus_amfi065_stack_guard(void)
{
    __asm__ volatile(
        "mrs x9, TPIDR_EL1\n\t"
        "cbz x9, 1f\n\t"
        "ldr x9, [x9, #%c0]\n\t"
        "cbz x9, 1f\n\t"
        "adrp x10, _kernel_stack_size@PAGE\n\t"
        "ldr x10, [x10, _kernel_stack_size@PAGEOFF]\n\t"
        "cbz x10, 1f\n\t"
        "cmp x8, x9\n\t"
        "b.lo 1f\n\t"
        "sub x8, x8, x9\n\t"
        "cmp x8, x10\n\t"
        "b.hi 1f\n\t"
        "ret\n"
        "1: mov x8, #0\n\t"
        "ret"
        : : "i" (offsetof(struct thread, kernel_stack)) : "memory");
}
