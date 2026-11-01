// SPDX-License-Identifier: MIT
#include <assert.h>
#include <string.h>
const char *getprogname(void);
#include "../package/Metal13/VenusMetalDiagnostics.h"

const char *getprogname(void) {return "backboardd";}

int main(void) {
    venus_metal_diag("entry","quote \" slash \\ control \001");
    venus_metal_diag("device","Metal device created");
    return 0;
}
