/*
 * Copyright (c) 2024 Apple Inc. All rights reserved.
 */
#ifndef libTrustCache_TypesConfig_h
#define libTrustCache_TypesConfig_h

#include <sys/cdefs.h>
__BEGIN_DECLS

/* Default to __single indexable pointers for Firebloom */
__ptrcheck_abi_assume_single();

#include <TrustCache/Types.h>

#if XNU_KERNEL_PRIVATE

/* Select macOS platform configuration */
#if XNU_TARGET_OS_OSX
#define libTrustCache_Platform_macOS 1
#else
#define libTrustCache_Platform_macOS 0
#endif

/* Select ARM architecture configuration */
#if defined(__arm__) || defined(__arm64__)
#define libTrustCache_Arch_ARM 1
#else
#define libTrustCache_Arch_ARM 0
#endif

#else /* !XNU_KERNEL_PRIVATE */

/*
 * XNU does not make this header available and uses different availability macros
 * than kernel extensions, base user-space applications, or guarded mode SDKs.
 */
#include <TargetConditionals.h>

/* Select macOS platform configuration */
#if TARGET_OS_OSX
#define libTrustCache_Platform_macOS 1
#else
#define libTrustCache_Platform_macOS 0
#endif

/* Select ARM architecture configuration */
#if TARGET_CPU_ARM || TARGET_CPU_ARM64
#define libTrustCache_Arch_ARM 1
#else
#define libTrustCache_Arch_ARM 0
#endif

#endif /* XNU_KERNEL_PRIVATE */

#pragma mark Firmware Flags

static Img4FirmwareFlags_t
firmwareFlagsDTRS(void) {
    return kImg4FirmwareFlagRespectAMNM;
}

static Img4FirmwareFlags_t
firmwareFlagsSplat(void) {
#if libTrustCache_Platform_macOS && libTrustCache_Arch_ARM
    return kImg4FirmwareFlagRespectSubsequentStage;
#else
    return kImg4FirmwareFlagInit;
#endif
}

#pragma mark Type Configuration

typedef struct _TrustCacheTypeConfig {
    /* Chip environment to use for validation */
    const Img4ChipEnvironment_t* (*chipEnvironment)(void);

    /* Nonce domain for anti-replay */
    const Img4NonceDomain_t* (*nonceDomain)(void);

    /* Four CC identifier for this type */
    Img4FourCC_t fourCC;

    /* Firmware flags to add for this configuration */
    Img4FirmwareFlags_t (*firmwareFlags)(void);

    /*
     * Higher level policy imposes restrictions on which process can load
     * which trust cache. These restrictions are enforced through the use
     * of the entitlement "com.apple.private.pmap.load-trust-cache". The
     * value here is the required value of the above entitlement.
     */
    const char *entitlementValue;
} TrustCacheTypeConfig_t;

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wfour-char-constants"

static const TrustCacheTypeConfig_t TCTypeConfig[kTCTypeTotal] = {
    /* Static trust caches are loaded as raw modules */
    [kTCTypeStatic] = {
        .chipEnvironment = NULL,
        .nonceDomain = NULL,
        .fourCC = 0,
        .firmwareFlags = NULL,
        .entitlementValue = NULL
    },

    /* Engineering trust caches are loaded as raw modules */
    [kTCTypeEngineering] = {
        .chipEnvironment = NULL,
        .nonceDomain = NULL,
        .fourCC = 0,
        .firmwareFlags = NULL,
        .entitlementValue = NULL
    },

    /* Legacy trust caches are loaded as raw modules */
    [kTCTypeLegacy] = {
        .chipEnvironment = NULL,
        .nonceDomain = NULL,
        .fourCC = 0,
        .firmwareFlags = NULL,
        .entitlementValue = NULL
    },

    [kTCTypeDTRS] = {
        .chipEnvironment = img4ChipEnvironmentPersonalized,
        .nonceDomain = NULL,
        .fourCC = 'dtrs',
        .firmwareFlags = firmwareFlagsDTRS,
        .entitlementValue = "personalized.engineering-root"
    },

    [kTCTypeLTRS] = {
        .chipEnvironment = img4ChipEnvironmentPersonalized,
        .nonceDomain = img4NonceDomainTrustCache,
        .fourCC = 'ltrs',
        .firmwareFlags = NULL,
        .entitlementValue = "personalized.trust-cache"
    },

    [kTCTypePersonalizedDiskImage] = {
        .chipEnvironment = img4ChipEnvironmentPersonalized,
        .nonceDomain = img4NonceDomainPDI,
        .fourCC = 'ltrs',
        .firmwareFlags = NULL,
        .entitlementValue = "personalized.pdi"
    },

    [kTCTypeDeveloperDiskImage] = {
        .chipEnvironment = img4ChipEnvironmentCategorized,
        .nonceDomain = img4NonceDomainDDI,
        .fourCC = 'trdv',
        .firmwareFlags = NULL,
        .entitlementValue = "personalized.ddi"
    },

    [kTCTypeLTRSWithDDINonce] = {
        .chipEnvironment = img4ChipEnvironmentPersonalized,
        .nonceDomain = img4NonceDomainDDI,
        .fourCC = 'ltrs',
        .firmwareFlags = NULL,
        .entitlementValue = "personalized.ddi"
    },

    [kTCTypeCryptex] = {
        .chipEnvironment = img4ChipEnvironmentPersonalized,
        .nonceDomain = img4NonceDomainCryptex,
        .fourCC = 'ltrs',
        .firmwareFlags = NULL,
        .entitlementValue = "personalized.cryptex-research"
    },

    [kTCTypeEphemeralCryptex] = {
        .chipEnvironment = img4ChipEnvironmentSupplemental,
        .nonceDomain = img4NonceDomainEphemeralCryptex,
        .fourCC = 'ltrs',
        .firmwareFlags = NULL,
        .entitlementValue = "personalized.ephemeral-cryptex"
    },

    [kTCTypeUpdateBrain] = {
        .chipEnvironment = img4ChipEnvironmentGlobalFF00,
        .nonceDomain = NULL,
        .fourCC = 'ltrs',
        .firmwareFlags = NULL,
        .entitlementValue = "global.ota-update-brain"
    },

    [kTCTypeInstallAssistant] = {
        .chipEnvironment = img4ChipEnvironmentGlobalFF01,
        .nonceDomain = NULL,
        .fourCC = 'ltrs',
        .firmwareFlags = NULL,
        .entitlementValue = "global.install-assistant"
    },

    [kTCTypeBootabilityBrain] = {
        .chipEnvironment = img4ChipEnvironmentGlobalFF06,
        .nonceDomain = NULL,
        .fourCC = 'trbb',
        .firmwareFlags = NULL,
        .entitlementValue = "global.bootability-brain"
    },

    [kTCTypeCryptex1BootOS] = {
        .chipEnvironment = img4ChipEnvironmentCryptex1Boot,
        .nonceDomain = NULL,
        .fourCC = 'trcs',
        .firmwareFlags = firmwareFlagsSplat,
        .entitlementValue = "cryptex1.boot.os"
    },

    [kTCTypeCryptex1BootApp] = {
        .chipEnvironment = img4ChipEnvironmentCryptex1Boot,
        .nonceDomain = NULL,
        .fourCC = 'trca',
        .firmwareFlags = firmwareFlagsSplat,
        .entitlementValue = "cryptex1.boot.app"
    },

    [kTCTypeCryptex1PreBootApp] = {
        .chipEnvironment = img4ChipEnvironmentCryptex1PreBoot,
        .nonceDomain = NULL,
        .fourCC = 'trca',
        .firmwareFlags = firmwareFlagsSplat,
        .entitlementValue = "cryptex1.preboot.app"
    },

    [kTCTypeGlobalDiskImage] = {
        .chipEnvironment = img4ChipEnvironmentGlobalFF00,
        .nonceDomain = NULL,
        .fourCC = 'ltrs',
        .firmwareFlags = NULL,
        .entitlementValue = "global.pdi"
    },

    [kTCTypeMobileAssetBrain] = {
        .chipEnvironment = img4ChipEnvironmentMobileAsset,
        .nonceDomain = NULL,
        .fourCC = 'trab',
        .firmwareFlags = NULL,
        .entitlementValue = "personalized.mobile-asset-brain"
    },

    [kTCTypeSafariDownlevel] = {
        .chipEnvironment = img4ChipEnvironmentCryptex1BootReduced,
        .nonceDomain = NULL,
        .fourCC = 'trca',
        .firmwareFlags = NULL,
        .entitlementValue = "cryptex1.safari-downlevel"
    },

    [kTCTypeCryptex1PreBootOS] = {
        .chipEnvironment = img4ChipEnvironmentCryptex1PreBoot,
        .nonceDomain = NULL,
        .fourCC = 'trcs',
        .firmwareFlags = firmwareFlagsSplat,
        .entitlementValue = "cryptex1.preboot.os"
    },

    [kTCTypeSupplementalPersistent] = {
        .chipEnvironment = img4ChipEnvironmentSupplemental,
        .nonceDomain = img4NonceDomainDDI,
        .fourCC = 'ltrs',
        .firmwareFlags = NULL,
        .entitlementValue = "personalized.supplemental-persistent"
    },

    [kTCTypeSupplementalEphemeral] = {
        .chipEnvironment = img4ChipEnvironmentSupplemental,
        .nonceDomain = img4NonceDomainPDI,
        .fourCC = 'ltrs',
        .firmwareFlags = NULL,
        .entitlementValue = "personalized.supplemental-ephemeral"
    },

    [kTCTypeCryptex1Generic] = {
        .chipEnvironment = img4ChipEnvironmentCryptex1Generic,
        .nonceDomain = NULL,
        .fourCC = 'gtcd',
        .firmwareFlags = NULL,
        .entitlementValue = "cryptex1.generic"
    },

    [kTCTypeCryptex1GenericSupplemental] = {
        .chipEnvironment = img4ChipEnvironmentCryptex1GenericSupplemental,
        .nonceDomain = NULL,
        .fourCC = 'gtcd',
        .firmwareFlags = NULL,
        .entitlementValue = "cryptex1.generic.supplemental"
    },

    [kTCTypeMobileAssetBrainEphemeral] = {
        .chipEnvironment = img4ChipEnvironmentMobileAsset,
        .nonceDomain = img4NonceDomainPDI,
        .fourCC = 'trab',
        .firmwareFlags = NULL,
        .entitlementValue = "personalized.mobile-asset-brain"
    },

    [kTCTypeCryptex1MobileAssetCode] = {
        .chipEnvironment = img4ChipEnvironmentMobileAssetCodeLoad,
        .nonceDomain = NULL,
        .fourCC = 'gtcd',
        .firmwareFlags = NULL,
        .entitlementValue = "personalized.mobile-asset-code"
    },
};

#pragma GCC diagnostic pop

__END_DECLS
#endif /* libTrustCache_TypesConfig_h */
