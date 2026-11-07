// SPDX-License-Identifier: BSD-2-Clause-Patent
// One boot-lifetime RAM record. Observes an existing exit; changes no exit,
// entitlement, limit, job or recovery policy. Published fields are immutable.
#include "FirstUiFailure055.h"
#ifdef KERNEL
#include <libkern/libkern.h>
#include <sys/reason.h>
#else
#include <stdio.h>
#include <string.h>
#define OS_REASON_JETSAM 1
#define OS_REASON_SPRINGBOARD 20
#endif

static unsigned basic_ready, detail_ready;
static int recorded_pid;
static char basic[224], detail[256];

int
venus_first_ui055_begin(int enabled, int pid, const char *name, int wait_status,
    uint32_t reason_namespace, uint64_t reason_code, const char *description)
{
    if (enabled != 1 || pid <= 0 || !name ||
        (strcmp(name, "SpringBoard") && strcmp(name, "backboardd") && strcmp(name, "lsd"))) return 0;
    unsigned signal = (unsigned)wait_status & 0x7f;
    int fatal = (!signal && wait_status != 0) || signal == 4 || signal == 5 || signal == 6 || signal == 10 || signal == 11 ||
        (signal == 9 && (reason_namespace == OS_REASON_JETSAM || reason_namespace == OS_REASON_SPRINGBOARD));
    if (!fatal) return 0;
    unsigned expected = 0;
    if (!__atomic_compare_exchange_n(&basic_ready, &expected, 1, 0, __ATOMIC_ACQUIRE, __ATOMIC_RELAXED)) return 0;
    recorded_pid = pid;
    snprintf(basic, sizeof(basic), "pid=%d %.16s status=0x%x reason=%u/0x%llx %.96s",
        pid, name, wait_status, reason_namespace, (unsigned long long)reason_code, description ? description : "");
    __atomic_store_n(&basic_ready, 2, __ATOMIC_RELEASE);
    return 1;
}

void
venus_first_ui055_detail(int pid, const char *reason)
{
    if (!reason || !reason[0] || __atomic_load_n(&basic_ready, __ATOMIC_ACQUIRE) != 2 || pid != recorded_pid) return;
    unsigned expected = 0;
    if (!__atomic_compare_exchange_n(&detail_ready, &expected, 1, 0, __ATOMIC_ACQUIRE, __ATOMIC_RELAXED)) return;
    snprintf(detail, sizeof(detail), "%.240s", reason);
    __atomic_store_n(&detail_ready, 2, __ATOMIC_RELEASE);
}

void
venus_first_ui055_snapshot(char *out, size_t capacity)
{
    if (!out || !capacity) return;
    if (__atomic_load_n(&basic_ready, __ATOMIC_ACQUIRE) != 2) {
        snprintf(out, capacity, "none (no recorded fatal UI exit)");
        return;
    }
    int ready = __atomic_load_n(&detail_ready, __ATOMIC_ACQUIRE) == 2;
    snprintf(out, capacity, "%s%s%s", basic, ready ? "\n" : "", ready ? detail : "");
}
