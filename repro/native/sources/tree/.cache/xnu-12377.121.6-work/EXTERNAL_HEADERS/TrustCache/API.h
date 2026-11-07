/*
 * Copyright (c) 2024 Apple Inc. All rights reserved.
 */
#ifndef libTrustCache_API_h
#define libTrustCache_API_h

#include <sys/cdefs.h>
__BEGIN_DECLS

/* Default to __single indexable pointers for Firebloom */
__ptrcheck_abi_assume_single();

#if __has_ptrcheck
#define libTrustCache_Firebloom_Unavailable(m) __attribute__((unavailable(m)))
#else
#define libTrustCache_Firebloom_Unavailable(m)
#endif /* __has_ptrcheck */

#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <TrustCache/Return.h>
#include <TrustCache/RawTypes.h>
#include <TrustCache/Types.h>
#include <TrustCache/TypesConfig.h>

#pragma mark Types

typedef struct _TrustCacheRuntimeOptions {
    const Img4Runtime_t *image4Runtime;
    bool allowSecondStaticTC;
    bool allowEngineeringTC;
    bool allowLegacyTC;

    /*
     * The environment may provide a call-back for auxiliary validation of the trust
     * cache before it is added to the trust cache runtime. This call-back is called
     * after the image4 validation of the trust cache is successful.
     *
     * If the environment does not wish to perform auxiliary validation, then leave
     * this pointer as NULL.
     */
    bool (*auxiliaryValidate)(Img4Image_t img4Obj);
} TrustCacheRuntimeOptions_t;

#pragma mark API

/**
 * Initialize a runtime to the default values based on the options provided.
 *
 * If the system supports read-only segments, and the runtime is allocated within the read-only
 * segment, then this function needs to be called before the segment is enforced to be read-only.
 * For more information, please look at <TrustCache/Types.h>.
 *
 * `Img4Runtime_t` is an alias of `img4_runtime_t`.
 */
static inline void
trustCacheInitializeRuntimeWithOptions(TrustCacheRuntime_t *runtime,
                                       TrustCacheMutableRuntime_t *mutableRT,
                                       TrustCacheRuntimeOptions_t *options)
{
    /* Zero out everything */
    memset(runtime, 0, sizeof(*runtime));
    memset(mutableRT, 0, sizeof(*mutableRT));

    /* Set the mutable runtime pointer */
    runtime->mutableRT = mutableRT;

    /* Setup trust cache type permissions */
    runtime->allowSecondStaticTC = options->allowSecondStaticTC;
    runtime->allowEngineeringTC = options->allowEngineeringTC;
    runtime->allowLegacyTC = options->allowLegacyTC;

    /* Set the image4 runtime */
    runtime->image4RT = options->image4Runtime;

    /* Setup environment based call-backs */
    runtime->auxiliaryValidate = options->auxiliaryValidate;
}

/**
 * Initialize a runtime to the default values. This is a thin wrapper over the API
 * for `trustCacheInitializeRuntimeWithOptions`.
 *
 * If the system supports read-only segments, and the runtime is allocated within the read-only
 * segment, then this function needs to be called before the segment is enforced to be read-only.
 * For more information, please look at <TrustCache/Types.h>.
 *
 * `Img4Runtime_t` is an alias of `img4_runtime_t`.
 */
static inline void
trustCacheInitializeRuntime(TrustCacheRuntime_t *runtime,
                            TrustCacheMutableRuntime_t *mutableRT,
                            bool allowSecondStaticTC,
                            bool allowEngineeringTC,
                            bool allowLegacyTC,
                            const Img4Runtime_t *image4RT)
{
    TrustCacheRuntimeOptions_t options = {
        .allowSecondStaticTC = allowSecondStaticTC,
        .allowEngineeringTC = allowEngineeringTC,
        .allowLegacyTC = allowLegacyTC,
        .image4Runtime = image4RT
    };

    return trustCacheInitializeRuntimeWithOptions(runtime, mutableRT, &options);
}

/**
 * Construct a trust cache object from some module bytes. The module is validated for
 * correctness before being returned.
 */
TCReturn_t
trustCacheConstructInvalid(TrustCache_t *trustCache,
                           const uint8_t *__counted_by(moduleSize) moduleAddr,
                           size_t moduleSize);

/**
 * Check the runtime for a trust cache which matches a particular UUID. Since we do
 * not allow trust caches with duplicate UUIDs, there can only ever be a single trust
 * cache with a particular UUID within the runtime.
 */
TCReturn_t
trustCacheCheckRuntimeForUUID(const TrustCacheRuntime_t *runtime,
                              const uint8_t checkUUID[kUUIDSize],
                              const TrustCache_t **trustCacheRet);

/**
 * Add a trust cache module directly to the runtime. This function is used to add modules which
 * don't need to be separately authenticated. Currently, the only trust cache types which can be
 * used with this function are static and engineering trust caches.
 *
 * If the system supports read-only segments, and the runtime is allocated within the read-only
 * segment, then this function needs to be called before the segment is enforced to be read-only.
 * For more information, please look at <TrustCache/Types.h>.
 */
TCReturn_t
trustCacheLoadModuleRange(TrustCacheRuntime_t *runtime,
                          TCType_t type,
                          TrustCache_t *trustCache,
                          const uint8_t *__counted_by(dataSize) dataAddr,
                          size_t dataSize);

libTrustCache_Firebloom_Unavailable("replaced with: trustCacheLoadModuleRange")
TCReturn_t
trustCacheLoadModule(TrustCacheRuntime_t *runtime,
                     const TCType_t type,
                     TrustCache_t *trustCache,
                     const uintptr_t dataAddr,
                     const size_t dataSize);

/**
 * Load a trust cache onto the system. This function validates the trust cache for a proper
 * signature and adds it to the runtime.
 *
 * Both the payload and the manifest must be provided and they will be validated as image4
 * objects.
 */
TCReturn_t
trustCacheLoadRange(TrustCacheRuntime_t *runtime,
                    TCType_t type,
                    TrustCache_t *trustCache,
                    const uint8_t *__counted_by(payloadSize) payloadAddr,
                    size_t payloadSize,
                    const uint8_t *__counted_by(manifestSize) manifestAddr,
                    size_t manifestSize);

libTrustCache_Firebloom_Unavailable("replaced with: trustCacheLoadRange")
TCReturn_t
trustCacheLoad(TrustCacheRuntime_t *runtime,
               TCType_t type,
               TrustCache_t *trustCache,
               const uintptr_t payloadAddr,
               const size_t payloadSize,
               const uintptr_t manifestAddr,
               const size_t manifestSize);

/**
 * Unload a trust cache from the given runtime. For now, this function does not truly unload
 * the trust cache, but rather tombstones it such that the trust cache does not partipcipate
 * in any queries in the future.
 *
 * Any look ups which race with the unloading operation may succeed. Once this function
 * returns, look ups performed afterwards will not match any digests within the tombstoned
 * trust cache.
 */
TCReturn_t
trustCacheUnload(TrustCacheRuntime_t *runtime,
                 const uint8_t unloadUuid[kUUIDSize],
                 const TrustCache_t **trustCacheRet);

/**
 * Extract an image4 artifact from an image4 file or an image4 payload and extract the
 * trust cache module embedded within it. The module is validated for correctness
 * before being returned, however the image4 signature is not verified.
 *
 * The returned trust cache object is marked with an invalid type.
 */
TCReturn_t
trustCacheExtractModule(TrustCache_t *trustCache,
                        const uint8_t *__counted_by(dataSize) dataAddr,
                        size_t dataSize);

/**
 * Query a  trust cache for a particular CDHash. The returned token can then be used to
 * query further attributes from the matched entry.
 *
 * This method is deprecated in favor of `trustCacheQueryWithLength`.
 */
TCReturn_t
trustCacheQuery(const TrustCacheRuntime_t *runtime,
                TCQueryType_t queryType,
                const uint8_t CDHash[kTCEntryHashSize],
                TrustCacheQueryToken_t *queryToken);

TCReturn_t
trustCacheQueryWithLength(const TrustCacheRuntime_t *runtime,
                          TCQueryType_t queryType,
                          const uint8_t *__counted_by(digestLength) digest,
                          size_t digestLength,
                          TrustCacheQueryToken_t *queryToken);

/**
 * Get the module bytes backng a trust cache object. The environment may have chosen
 * to allocate the module bytes within read-only memory, so the bytes returned may
 * not be mutable.
 */
TCReturn_t
trustCacheGetModule(const TrustCache_t *trustCache,
                    const uint8_t *__counted_by(*moduleSizeRet) *moduleAddrRet,
                    size_t *moduleSizeRet);

/**
 * Get the UUID of the trust cache module represented by the wrapped trust cache object.
 */
TCReturn_t
trustCacheGetUUID(const TrustCache_t *trustCache,
                  uint8_t returnUUID[kUUIDSize]);

/**
 * Get the capabilities of a trust cache. This function can be used to query which fields a given
 * trust cache supports.
 *
 * The fields which are supported are based on the version of the trust cache module.
 */
TCReturn_t
trustCacheGetCapabilities(const TrustCache_t *trustCache,
                          TCCapabilities_t *capabilities);

/**
 * Acquire the trust cache type for a query token.
 */
TCReturn_t
trustCacheQueryGetTCType(const TrustCacheQueryToken_t *queryToken,
                         TCType_t *typeRet);

/**
 * Acquire the UUID of a trust cache for a query token.
 */
TCReturn_t
trustCacheQueryGetUUID(const TrustCacheQueryToken_t *queryToken,
                       uint8_t returnUUID[kUUIDSize]);

/**
 * Acquire the capabilities of the trust cache through a query token.
 */
TCReturn_t
trustCacheQueryGetCapabilities(const TrustCacheQueryToken_t *queryToken,
                               TCCapabilities_t *capabilities);

/**
 * Acquire the hash type for the CDHash through a query token.
 */
TCReturn_t
trustCacheQueryGetHashType(const TrustCacheQueryToken_t *queryToken,
                           uint8_t *hashTypeRet);

/**
 * Acquire the flags for a trust cache entry through a query token.
 */
TCReturn_t
trustCacheQueryGetFlags(const TrustCacheQueryToken_t *queryToken,
                        uint64_t *flagsRet);

/**
 * Acquire the constraint category for a trust cache entry through a query token.
 */
TCReturn_t
trustCacheQueryGetConstraintCategory(const TrustCacheQueryToken_t *queryToken,
                                     uint8_t *constraintCategoryRet);

/**
 * Acquire the restricted execution mode permissions for a trust cache entry through
 * a query token.
 */
TCReturn_t
trustCacheQueryGetRestrictedModePerms(const TrustCacheQueryToken_t *queryToken,
                                      uint8_t *remPermsRet);

#pragma mark Special APIs

#define kLibTrustCacheHasQueryForREM 1

/**
 * Query the set of loaded trust caches in a very particular order in order to guage the
 * most appropriate REM permissions for the CDHash.
 *
 * First, the set of loadable trust caches are queried. If a match is found, the permissions
 * are returned. Next, the set of static/engineering trust caches are queried. If a match is
 * found, the permissions are returned.
 *
 * NOTE: The ordering of the loadable trust caches is undefined. If multiple loadable trust
 * caches contain the CDHash, the permissions from the first match are returned, even if
 * the matched trust cache is not the newest loaded one.
 */
TCReturn_t
trustCacheQueryForREM(const TrustCacheRuntime_t *runtime,
                      const uint8_t *__counted_by(digestLength) digest,
                      size_t digestLength,
                      uint8_t *remPermsRet);

__END_DECLS
#endif /* libTrustCache_API_h */
