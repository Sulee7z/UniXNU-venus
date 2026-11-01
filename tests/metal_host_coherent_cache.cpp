// SPDX-License-Identifier: MIT
// Host software Vulkan uses coherent x86 CPU memory. This supplies the host's
// visibility barrier; the iOS target still imports real libSystem cache flush.
#include <atomic>
#include <stddef.h>
extern "C" void sys_dcache_flush(void *address,size_t bytes) {
    (void)address;(void)bytes;std::atomic_thread_fence(std::memory_order_seq_cst);
}
