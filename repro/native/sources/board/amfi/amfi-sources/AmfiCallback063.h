/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <string.h>
#ifndef AMFI063_HOST_TEST
#include <CoreEntitlements/V2/API.h>
#include <pexpert/pexpert.h>
#endif

#define AMFI063_MAGIC UINT64_C(0x414d463036330000)
volatile uintptr_t venus_amfi063_originals[10] = {
    AMFI063_MAGIC, AMFI063_MAGIC+1, AMFI063_MAGIC+2, AMFI063_MAGIC+3, AMFI063_MAGIC+4,
    AMFI063_MAGIC+5, AMFI063_MAGIC+6, AMFI063_MAGIC+7, AMFI063_MAGIC+8, AMFI063_MAGIC+9
};
static volatile uint32_t amfi063_failures[8], amfi063_value_samples;

struct amfi063_environment {
    void (*free_object)(const void *);
    void *(*boolean)(bool);
    void *(*number)(int64_t);
    void *(*string)(const CEString_t *);
    void *(*symbol)(const CEString_t *);
    void *(*array)(void);
    void *(*dictionary)(void);
    void *(*data)(const CEData_t *);
    void (*array_set)(void *, const void *);
    void (*dictionary_set)(void *, const void *, const void *);
};
_Static_assert(sizeof(struct amfi063_environment) == 80, "Original CE environment must be80 bytes");

static bool amfi063_readable(uintptr_t address, size_t size)
{
    if (!size || address > UINTPTR_MAX - size) return false;
#ifdef AMFI063_HOST_TEST
    return address >= 4096;
#else
    uint64_t first, last;
    if (address < UINT64_C(0xfffffff000000000)) return false;
    uintptr_t end = address + size - 1;
    __asm__ volatile("at s1e1r, %1\n\tisb\n\tmrs %0, par_el1" : "=r"(first) : "r"(address) : "memory");
    __asm__ volatile("at s1e1r, %1\n\tisb\n\tmrs %0, par_el1" : "=r"(last) : "r"(end) : "memory");
    return !(first & 1) && !(last & 1) && (first >> 60) && (last >> 60);
#endif
}

static void amfi063_failure(unsigned index, const void *input, size_t length)
{
    static const char *names[8] = {"free", "boolean", "number", "string", "symbol", "array", "dictionary", "data"};
    if (index >= 8 || __atomic_fetch_add(&amfi063_failures[index], 1, __ATOMIC_RELAXED) >= 32) return;
    char hex[49] = {0}; unsigned count = length > 24 ? 24 : (unsigned)length;
    bool readable = count && amfi063_readable((uintptr_t)input, count);
    if (readable) {
        static const char digits[] = "0123456789abcdef";
        for (unsigned i = 0; i < count; ++i) {
            unsigned char byte = ((const unsigned char *)input)[i];
            hex[i * 2] = digits[byte >> 4]; hex[i * 2 + 1] = digits[byte & 15];
        }
    }
    printf("AMFI063: callback=%s NULL tid=%llu free=%u input=0x%llx bytes=%llu read=%u prefix=%s\n",
        names[index], (unsigned long long)thread_tid(current_thread()), vm_page_free_count,
        (unsigned long long)(uintptr_t)input, (unsigned long long)length, readable, hex);
}
static void amfi063_free(const void *object) {((void (*)(const void *))venus_amfi063_originals[0])(object);}
static void *amfi063_bool(bool value) {
    void *result = ((void *(*)(bool))venus_amfi063_originals[1])(value);
    if (!result) amfi063_failure(1, NULL, 0);
    return result;
}
static void *amfi063_number(int64_t value) {
    void *result = ((void *(*)(int64_t))venus_amfi063_originals[2])(value);
    if (!result) amfi063_failure(2, NULL, 0);
    return result;
}
static void *amfi063_string(const CEString_t *value) {
    void *result = ((void *(*)(const CEString_t *))venus_amfi063_originals[3])(value);
    if (!result) {
        bool valid = amfi063_readable((uintptr_t)value, sizeof(*value));
        amfi063_failure(3, valid ? value->data : NULL, valid ? value->length : 0);
    }
    return result;
}
static void *amfi063_symbol(const CEString_t *value) {
    void *result = ((void *(*)(const CEString_t *))venus_amfi063_originals[4])(value);
    if (!result) {
        bool valid = amfi063_readable((uintptr_t)value, sizeof(*value));
        amfi063_failure(4, valid ? value->data : NULL, valid ? value->length : 0);
    }
    return result;
}
static void *amfi063_array(void) {
    void *result = ((void *(*)(void))venus_amfi063_originals[5])();
    if (!result) amfi063_failure(5, NULL, 0);
    return result;
}
static void *amfi063_dictionary(void) {
    void *result = ((void *(*)(void))venus_amfi063_originals[6])();
    if (!result) amfi063_failure(6, NULL, 0);
    return result;
}
static void *amfi063_data(const CEData_t *value) {
    void *result = ((void *(*)(const CEData_t *))venus_amfi063_originals[7])(value);
    if (!result) {
        bool valid = amfi063_readable((uintptr_t)value, sizeof(*value));
        amfi063_failure(7, valid ? value->data : NULL, valid ? value->length : 0);
    }
    return result;
}
static void amfi063_array_set(void *array, const void *value) {
    ((void (*)(void *, const void *))venus_amfi063_originals[8])(array, value);
}
static void amfi063_dictionary_set(void *dictionary, const void *key, const void *value) {
    ((void (*)(void *, const void *, const void *))venus_amfi063_originals[9])(dictionary, key, value);
}

static void *venus_amfi063_call(void *(*original)(const CEValueTypePair_t *, const void *),
    const CEValueTypePair_t *value, const void *environment)
{
    unsigned enabled = 0;
    PE_parse_boot_argn("venus-amfi-probe", &enabled, sizeof(enabled));
    if (enabled != 1 || !amfi063_readable((uintptr_t)environment, 80)) return original(value, environment);
    uintptr_t actual[10]; memcpy(actual, environment, sizeof(actual));
    for (unsigned i = 0; i < 10; ++i) {
        if (venus_amfi063_originals[i] == AMFI063_MAGIC + i || actual[i] != venus_amfi063_originals[i])
            return original(value, environment);
    }
    /* Original iteration is synchronous; this80-byte callback table never escapes the call. */
    const struct amfi063_environment observed = {amfi063_free, amfi063_bool, amfi063_number,
        amfi063_string, amfi063_symbol, amfi063_array, amfi063_dictionary, amfi063_data,
        amfi063_array_set, amfi063_dictionary_set};
    void *result = original(value, &observed);
    if (!result && __atomic_fetch_add(&amfi063_value_samples, 1, __ATOMIC_RELAXED) < 64 &&
        amfi063_readable((uintptr_t)value, sizeof(*value))) {
        printf("AMFI063: original-result=NULL type=%u tag=0x%llx data=0x%llx content=0x%llx der-bytes=%llu content-bytes=%llu tid=%llu\n",
            value->derType, (unsigned long long)value->derValue.derDecoded.tag,
            (unsigned long long)(uintptr_t)value->derValue.derData.data,
            (unsigned long long)(uintptr_t)value->derValue.derDecoded.content.data,
            (unsigned long long)value->derValue.derData.length,
            (unsigned long long)value->derValue.derDecoded.content.length,
            (unsigned long long)thread_tid(current_thread()));
    }
    return result;
}
