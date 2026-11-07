/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#ifndef AMFI064_HOST_TEST
#include <CoreEntitlements/V2/API.h>
#include <pexpert/pexpert.h>
#endif
#include <stdint.h>

#define AMFI064_MAGIC UINT64_C(0x414d463036340000)
volatile uintptr_t venus_amfi064_iterator = AMFI064_MAGIC;
volatile uintptr_t venus_amfi064_key_callback = AMFI064_MAGIC + 1;
static volatile uint32_t amfi064_key_failures, amfi064_iterator_failures;

static CEReturn_t amfi064_key_probe(const CEKeyValuePair_t *pair, CEIterateArgs_t *args)
{
    CEDictionaryIterate_t callback = (CEDictionaryIterate_t)venus_amfi064_key_callback;
    CEReturn_t result = callback(pair, args);
    if (result && __atomic_fetch_add(&amfi064_key_failures, 1, __ATOMIC_RELAXED) < 64 &&
        amfi063_readable((uintptr_t)pair, sizeof(*pair))) {
        printf("AMFI064: key-callback error=%u tid=%llu key-tag=0x%llx key-data=0x%llx key-content=0x%llx key-bytes=%llu key-content-bytes=%llu value-type=%u value-tag=0x%llx\n",
            result, (unsigned long long)thread_tid(current_thread()),
            (unsigned long long)pair->derKey.derDecoded.tag,
            (unsigned long long)(uintptr_t)pair->derKey.derData.data,
            (unsigned long long)(uintptr_t)pair->derKey.derDecoded.content.data,
            (unsigned long long)pair->derKey.derData.length,
            (unsigned long long)pair->derKey.derDecoded.content.length,
            pair->valueTypePair.derType, (unsigned long long)pair->valueTypePair.derValue.derDecoded.tag);
    }
    return result;
}

__attribute__((noinline, used)) CEReturn_t
venus_amfi064_dictionary_iterate(const CEElement_t *dictionary, CEDictionaryIterate_t callback, void *context)
{
    CEReturn_t (*original)(const CEElement_t *, CEDictionaryIterate_t, void *) =
        (CEReturn_t (*)(const CEElement_t *, CEDictionaryIterate_t, void *))venus_amfi064_iterator;
    unsigned enabled = 0;
    PE_parse_boot_argn("venus-amfi-probe", &enabled, sizeof(enabled));
    bool matched = enabled == 1 && (uintptr_t)callback == venus_amfi064_key_callback;
    CEReturn_t result = original(dictionary, matched ? amfi064_key_probe : callback, context);
    if (result && __atomic_fetch_add(&amfi064_iterator_failures, 1, __ATOMIC_RELAXED) < 64) {
        printf("AMFI064: dictionary-iterate error=%u tid=%llu callback=0x%llx matched=%u context=0x%llx\n",
            result, (unsigned long long)thread_tid(current_thread()),
            (unsigned long long)(uintptr_t)callback, matched, (unsigned long long)(uintptr_t)context);
    }
    return result;
}
