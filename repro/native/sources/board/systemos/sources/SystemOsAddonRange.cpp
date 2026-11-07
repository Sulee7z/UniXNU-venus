// SPDX-License-Identifier: BSD-2-Clause-Patent
// RamBlock d4d22d9819b0162eda49f6402235dddc2279410d accessor, kept separate
// so the already qualified Data provider and persistence lifecycle do not change.
#include <IOKit/IORegistryEntry.h>
#include <IOKit/IODeviceTreeSupport.h>
#include <libkern/c++/OSData.h>
#include <machine/machine_routines.h>
#include <stdint.h>

extern "C" {
extern unsigned long gPhysBase, gPhysSize;
int native_ram_block_gpu_addon(const uint8_t **data, uint64_t *bytes)
{
    if (!data || !bytes) return 0;
    *data = nullptr;
    *bytes = 0;
    IORegistryEntry *map = IORegistryEntry::fromPath("/chosen/memory-map", gIODTPlane);
    if (!map) return 0;
    OSData *range = OSDynamicCast(OSData, map->getProperty("GpuAddon"));
    uint64_t physical = 0, size = 0;
    if (range && range->getLength() == 16) {
        memcpy(&physical, range->getBytesNoCopy(), 8);
        memcpy(&size, static_cast<const uint8_t *>(range->getBytesNoCopy()) + 8, 8);
    }
    map->release();
    if (!size || size > (UINT64_C(64) << 20) || (physical & 4095) || physical < gPhysBase ||
        size > gPhysSize || physical - gPhysBase > gPhysSize - size) return 0;
    *data = reinterpret_cast<const uint8_t *>(ml_static_ptovirt(physical));
    if (!*data) return 0;
    *bytes = size;
    return 1;
}
}
