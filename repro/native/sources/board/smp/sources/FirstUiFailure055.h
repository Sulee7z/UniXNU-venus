// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef VENUS_FIRST_UI_FAILURE_055_H
#define VENUS_FIRST_UI_FAILURE_055_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
int venus_first_ui055_begin(int enabled, int pid, const char *name, int wait_status,
    uint32_t reason_namespace, uint64_t reason_code, const char *description);
void venus_first_ui055_detail(int pid, const char *reason);
void venus_first_ui055_snapshot(char *out, size_t capacity);
#ifdef __cplusplus
}
#endif
#endif
