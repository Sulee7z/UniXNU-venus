/*
 * Copyright (c) 2024 Apple Inc. All rights reserved.
 */
#ifndef libTrustCache_RawTypes_h
#define libTrustCache_RawTypes_h

#include <sys/cdefs.h>
__BEGIN_DECLS

/* Default to __single indexable pointers for Firebloom */
__ptrcheck_abi_assume_single();

#if __has_ptrcheck
#define libTrustCache_variable_counted(x) __counted_by(x)
#else
#define libTrustCache_variable_counted(x) 0
#endif

#if __has_include(<corecrypto/ccsha1.h>)
#define libTrustCache_Include_SHA1 1
#else
#define libTrustCache_Include_SHA1 0
#endif

#include <stddef.h>
#include <stdint.h>

#if libTrustCache_Include_SHA1
#include <corecrypto/ccsha1.h>
#define kTCEntryHashSize CCSHA1_OUTPUT_SIZE
#else
#define kTCEntryHashSize 20
#endif

#include <corecrypto/ccsha2.h>

/* UUIDs are always 16 bytes */
#define kTCUuidSize 16
#define kUUIDSize kTCUuidSize

/* Versions supported by the library */
enum {
    kTCVersion0 = 0x0,
    kTCVersion1 = 0x1,
    kTCVersion2 = 0x2,
    kTCVersion3 = 0x3,
    kTCVersionTotal
};

/* Flags for the trust cache look ups */
enum {
    kTCFlagAMFID = (1 << 0),
    kTCFlagANEModel = (1 << 1),

    /*
     * Restricted Execution Mode permissions is an enumeration built from a
     * combination of trust cache flags attached to the trust cache entry.
     */
    kTCFlagRestrictedModePermsBit0 = (1 << 6),
    kTCFlagRestrictedModePermsBit1 = (1 << 7)
};

typedef enum __attribute__((enum_extensibility(closed))) : uint8_t {
    kTCHashTypeInvalid = 0,
    kTCHashTypeSHA1 = 1,
    kTCHashTypeSHA256 = 2,
    kTCHashTypeSHA256Truncated = 3,
    kTCHashTypeSHA384 = 4,
    kTCHashTypeTotal
} TrustCacheHashType_t;

typedef struct _TrustCacheModuleBase {
    uint32_t version;
} __attribute__((packed)) TrustCacheModuleBase_t;

typedef struct _TrustCacheModuleBase3 {
    uint32_t version;
    uint8_t uuid[kUUIDSize];
    TrustCacheHashType_t hashType;
    uint32_t numEntries;
} __attribute__((packed)) TrustCacheModuleBase3_t;

#pragma mark Trust Cache Version 0

typedef uint8_t TrustCacheEntry0_t[kTCEntryHashSize];

typedef struct _TrustCacheModule0 {
    /* Must be 0 */
    uint32_t version;

    /* ID which uniquely identifies the trust cache */
    uint8_t uuid[kUUIDSize];

    /* The number of entries present in the trust cache */
    uint32_t numEntries;

    /* Dynamic data containing all the entries */
    TrustCacheEntry0_t entries[libTrustCache_variable_counted(numEntries)];
} __attribute__((packed)) TrustCacheModule0_t;

#pragma mark Trust Cache Version 1

typedef struct _TrustCacheEntry1 {
    uint8_t CDHash[kTCEntryHashSize];
    uint8_t hashType;
    uint8_t flags;
} __attribute__((packed)) TrustCacheEntry1_t;

typedef struct _TrustCacheModule1 {
    /* Must be 1 */
    uint32_t version;

    /* ID which uniquely identifies the trust cache */
    uint8_t uuid[kUUIDSize];

    /* The number of entries present in the trust cache */
    uint32_t numEntries;

    /* Dynamic data containing all the entries */
    TrustCacheEntry1_t entries[libTrustCache_variable_counted(numEntries)];
} __attribute__((packed)) TrustCacheModule1_t;

#pragma mark Trust Cache Version 2

typedef struct _TrustCacheEntry2 {
    uint8_t CDHash[kTCEntryHashSize];
    uint8_t hashType;
    uint8_t flags;
    uint8_t constraintCategory;
    uint8_t reserved0;
} __attribute__((packed)) TrustCacheEntry2_t;

typedef struct _TrustCacheModule2 {
    /* Must be 2 */
    uint32_t version;

    /* ID which uniquely identifies the trust cache */
    uint8_t uuid[kUUIDSize];

    /* The number of entries present in the trust cache */
    uint32_t numEntries;

    /* Dynamic data containing all the entries */
    TrustCacheEntry2_t entries[libTrustCache_variable_counted(numEntries)];
} __attribute__((packed)) TrustCacheModule2_t;

#pragma mark Trust Cache Version 3

typedef struct _TrustCacheEntry3Sha256 {
    uint8_t digest[CCSHA256_OUTPUT_SIZE];
    uint8_t flags;
    uint8_t constraintCategory;
} __attribute__((packed)) TrustCacheEntry3Sha256_t;

typedef struct _TrustCacheModule3Sha256 {
    /* Must be 3 */
    uint32_t version;

    /* ID which uniquely identifies the trust cache */
    uint8_t uuid[kUUIDSize];

    /* Hash type used for the module (must be sha-256) */
    TrustCacheHashType_t hashType;

    /* The number of entries present in the trust cache */
    uint32_t numEntries;

    /* Dynamic data containing all the entries */
    TrustCacheEntry3Sha256_t entries[libTrustCache_variable_counted(numEntries)];
} __attribute__((packed)) TrustCacheModule3Sha256_t;

typedef struct _TrustCacheEntry3Sha384 {
    uint8_t digest[CCSHA384_OUTPUT_SIZE];
    uint8_t flags;
    uint8_t constraintCategory;
} __attribute__((packed)) TrustCacheEntry3Sha384_t;

typedef struct _TrustCacheModule3Sha384 {
    /* Must be 3 */
    uint32_t version;

    /* ID which uniquely identifies the trust cache */
    uint8_t uuid[kUUIDSize];

    /* Hash type used for the module (must be sha-384) */
    TrustCacheHashType_t hashType;

    /* The number of entries present in the trust cache */
    uint32_t numEntries;

    /* Dynamic data containing all the entries */
    TrustCacheEntry3Sha384_t entries[libTrustCache_variable_counted(numEntries)];
} __attribute__((packed)) TrustCacheModule3Sha384_t;

__END_DECLS
#endif /* libTrustCache_RawTypes_h */
