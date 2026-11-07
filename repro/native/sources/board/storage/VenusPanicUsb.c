// SPDX-License-Identifier: BSD-2-Clause-Patent
// Report through the existing USB console before entering the panic screen.
#include <stdint.h>
#include <stddef.h>

extern void unixnu_dwc3_put(uint8_t);
extern void unixnu_dwc3_poll(void);
extern unsigned int unixnu_dwc3_backlog(void);
extern volatile uint32_t unixnu_dwc3_phase;

// Filled by the image patcher after the ordinary panic screen is installed.
volatile uintptr_t venus_panic_usb_screen_common = UINT64_C(0x5650555342434f4d);
volatile uint32_t venus_panic_usb_entered;
volatile uint32_t venus_panic_usb_finished;

static int readable(uintptr_t address)
{
    uint64_t par;
    if (address < UINT64_C(0xfffffff000000000)) return 0;
    __asm__ volatile("at s1e1r, %1\n\tisb\n\tmrs %0, par_el1" : "=r"(par) : "r"(address) : "memory");
    return !(par & 1) && (par >> 60) != 0;
}

static void text(const char *value)
{
    while (*value) unixnu_dwc3_put((uint8_t)*value++);
}

static void number(uint64_t value)
{
    static const char digits[] = "0123456789abcdef";
    text("0x");
    for (int shift = 60; shift >= 0; shift -= 4) unixnu_dwc3_put((uint8_t)digits[(value >> shift) & 15]);
}

static void bounded_string(const char *value, unsigned int limit)
{
    for (unsigned int i = 0; i < limit; ++i) {
        if (!readable((uintptr_t)value + i)) { text("<unmapped>"); return; }
        unsigned char c = (unsigned char)value[i];
        if (!c) return;
        unixnu_dwc3_put(c >= 32 && c <= 126 ? c : (c == '\n' || c == '\t' ? c : '?'));
    }
    text("<truncated>");
}

static uint64_t ticks(void)
{
    uint64_t value;
    __asm__ volatile("isb\n\tmrs %0, cntpct_el0" : "=r"(value));
    return value;
}

static void flush(void)
{
    if (unixnu_dwc3_phase < 4) return;
    uint64_t frequency;
    __asm__ volatile("mrs %0, cntfrq_el0" : "=r"(frequency));
    uint64_t start = ticks();
    while (unixnu_dwc3_backlog() && ticks() - start < frequency) unixnu_dwc3_poll();
}

__attribute__((noreturn, noinline, used)) void venus_panic_usb_park(void)
{
    for (;;) __asm__ volatile("wfe");
}

__attribute__((noreturn, used)) void venus_panic_usb_main(const char *format, const uint64_t *arguments)
{
    __asm__ volatile("msr daifset, #15");
    if (!__atomic_exchange_n(&venus_panic_usb_entered, 1, __ATOMIC_RELAXED)) {
        text("\nVENUS PANIC USB: ");
        bounded_string(format, 768);
        text("\nraw argument words:");
        for (unsigned int i = 0; i < 8; ++i) {
            if (!readable((uintptr_t)(arguments + i)) || !readable((uintptr_t)(arguments + i) + 7)) break;
            unixnu_dwc3_put(' ');
            number(arguments[i]);
        }
        if (readable((uintptr_t)arguments) && readable((uintptr_t)arguments + 7) &&
            readable((uintptr_t)format) && readable((uintptr_t)format + 1) && format[0] == '%' && format[1] == 's') {
            text("\nargument0: ");
            bounded_string((const char *)(uintptr_t)arguments[0], 1536);
        }
        const uint64_t *frame = __builtin_frame_address(0);
        text("\nframes:");
        for (unsigned int i = 0; i < 16; ++i) {
            uintptr_t at = (uintptr_t)frame;
            if ((at & 15) || !readable(at) || !readable(at + 15)) break;
            uintptr_t next = (uintptr_t)frame[0];
            unixnu_dwc3_put(' ');
            number(frame[1]);
            if (next <= at) break;
            frame = (const uint64_t *)next;
        }
        text("\nVENUS PANIC USB END\n");
        venus_panic_usb_finished = 1;
        flush();
    }
    uintptr_t target = venus_panic_usb_screen_common;
    if (target != UINT64_C(0x5650555342434f4d) && readable(target)) {
        const uint64_t *list = arguments;
        ((void (*)(const char *, const uint64_t **))target)(format, &list);
    }
    venus_panic_usb_park();
}

__attribute__((naked, noreturn, used)) void venus_panic_usb_direct(void)
{
    __asm__ volatile("mov x1, sp\n\tb _venus_panic_usb_main");
}

__attribute__((naked, noreturn, used)) void venus_panic_usb_common(void)
{
    __asm__ volatile("ldr x1, [x1]\n\tb _venus_panic_usb_main");
}
