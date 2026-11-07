// Observe the genuine converter's first NULL result. Never replace a policy decision.
#include <CoreEntitlements/V2/API.h>
#include <kern/thread.h>
#include <vm/vm_page.h>

volatile uintptr_t venus_amfi051_original = UINT64_C(0x414d464930353152);
volatile uint32_t venus_amfi051_failures;

static int venus_amfi051_readable(uintptr_t address)
{
    uint64_t par;
    if (address < UINT64_C(0xfffffff000000000)) return 0;
    __asm__ volatile("at s1e1r, %1\n\tisb\n\tmrs %0, par_el1" : "=r"(par) : "r"(address) : "memory");
    return !(par & 1) && (par >> 60) != 0;
}

#include "AmfiCallback063.h"
#include "AmfiIterator064.h"

__attribute__((noinline, used)) void *
venus_amfi051_convert(const CEValueTypePair_t *value, const void *environment)
{
    void *(*original)(const CEValueTypePair_t *, const void *) = (void *)venus_amfi051_original;
    if ((uintptr_t)original == UINT64_C(0x414d464930353152))
        panic("AMFI051: converter target was not bound");
    void *result = venus_amfi063_call(original, value, environment);
    if (!result && !__atomic_exchange_n(&venus_amfi051_failures, 1, __ATOMIC_RELAXED)) {
        proc_t process = current_proc();
        printf("AMFI051: first NULL pid=%d comm=%s tid=%llu free=%u active=%u inactive=%u wired=%u\n",
            proc_pid(process), process->p_comm, thread_tid(current_thread()),
            vm_page_free_count, vm_page_active_count, vm_page_inactive_count, vm_page_wire_count);
        if (venus_amfi051_readable((uintptr_t)value) &&
            venus_amfi051_readable((uintptr_t)value + sizeof(*value) - 1)) {
            printf("AMFI051: type=%u tag=0x%llx der-bytes=%llu content-bytes=%llu\n",
                value->derType, value->derValue.derDecoded.tag,
                value->derValue.derData.length, value->derValue.derDecoded.content.length);
            const uint8_t *data = value->derValue.derData.data;
            size_t size = value->derValue.derData.length < 512 ? value->derValue.derData.length : 512;
            static const char digits[] = "0123456789abcdef";
            for (size_t at = 0; at < size; at += 32) {
                char line[65];
                size_t count = size - at < 32 ? size - at : 32;
                if ((uintptr_t)data > UINTPTR_MAX - at - count ||
                    !venus_amfi051_readable((uintptr_t)data + at) ||
                    !venus_amfi051_readable((uintptr_t)data + at + count - 1)) break;
                for (size_t index = 0; index < count; ++index) {
                    unsigned char c = data[at + index];
                    line[index * 2] = digits[c >> 4];
                    line[index * 2 + 1] = digits[c & 15];
                }
                line[count * 2] = 0;
                printf("AMFI051: der offset=%lu %s\n", at, line);
            }
        }
    }
    return result;
}

static void venus_amfi051_vnode(vnode_t vnode, off_t offset, const char *phase)
{
    static volatile uint32_t calls;
    if (__atomic_fetch_add(&calls, 1, __ATOMIC_RELAXED) >= 1024) return;
    char path[256];
    int length = sizeof(path);
    int error = vn_getpath(vnode, path, &length);
    printf("AMFI051: vnode %s tid=%llu off=%lld path-error=%d path=%.160s\n",
        phase, thread_tid(current_thread()), offset, error, error ? "<unavailable>" : path);
}
