/*
 * Copyright (c) 2024 Apple Inc. All rights reserved.
 */
#ifndef libTrustCache_Image4_h
#define libTrustCache_Image4_h

#include <sys/cdefs.h>
__BEGIN_DECLS

/* Default to __single indexable pointers for Firebloom */
__ptrcheck_abi_assume_single();

#include <stdint.h>

/*
 * Some build environments do not have any access to AppleImage4, which is the
 * de-facto method for parsing and managing image4 signatures by this library.
 *
 * Our goal here is to allow image4 based operations to be opt-outable in those
 * environments where AppleImage4 isn't available or when image4 signatures are
 * not required or supported.
 */

#if libTrustCache_Config_NoImage4
/* Configuration is opting out of supporting image4 */
#define libTrustCache_Include_Image4 0
#elif __has_include(<img4/firmware.h>)
/* Configuration is not opting out of supporting image4 */
#define libTrustCache_Include_Image4 1
#else
/* Configuration doesn't support AppleImage4 */
#define libTrustCache_Include_Image4 0
#endif /* libTrustCache_Config_NoImage4 */

/*
 * The trust cache image4 runtime becomes the abstraction layer for any and all
 * operations against image4 blobs. When AppleImage4 is available and supported,
 * all operations make use of it.
 *
 * When AppleImage4 isn't available or not supported, all operations on image4
 * objects return with an unsupported error.
 */
#if libTrustCache_Include_Image4

#include <img4/firmware.h>

#if XNU_KERNEL_PRIVATE
/*
 * The AppleImage4 API definitions are accessed through the 'img4if' indirection
 * layer within XNU itself. Kernel extensions can access them directly from the
 * AppleImage4 headers.
 */
#include <libkern/img4/interface.h>

#ifndef IMG4_CHIP_CRYPTEX1_ASSET_CODE_LOAD
#define IMG4_CHIP_CRYPTEX1_ASSET_CODE_LOAD (NULL)
#endif /* IMG4_CHIP_CRYPTEX1_ASSET_CODE_LOAD */

#endif /* XNU_KERNEL_PRIVATE */

/* Abstract type for the runtime */
typedef img4_runtime_t Img4Runtime_t;

/* Abstract type for chip environments */
typedef img4_chip_t Img4ChipEnvironment_t;

/* Abstract type for nonce domains */
typedef img4_nonce_domain_t Img4NonceDomain_t;

/* Abstract type for firmware flags */
typedef img4_firmware_flags_t Img4FirmwareFlags_t;

/* Abstract type for the image */
typedef img4_image_t Img4Image_t;

/* Abstract type for 4cc identifiers */
typedef img4_4cc_t Img4FourCC_t;

#pragma mark Chip Environments

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentPersonalized(void)
{
    return __unsafe_forge_single(const img4_chip_t*,
                                 img4_chip_select_personalized_ap());
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentCategorized(void)
{
    return __unsafe_forge_single(const img4_chip_t*,
                                 img4_chip_select_categorized_ap());
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentGlobalFF00(void)
{
    return IMG4_CHIP_AP_SOFTWARE_FF00;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentGlobalFF01(void)
{
    return IMG4_CHIP_AP_SOFTWARE_FF01;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentGlobalFF06(void)
{
    return IMG4_CHIP_AP_SOFTWARE_FF06;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentSupplemental(void)
{
    return IMG4_CHIP_AP_SUPPLEMENTAL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentMobileAsset(void)
{
    return IMG4_CHIP_CRYPTEX1_ASSET;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentCryptex1Boot(void)
{
    return __unsafe_forge_single(const img4_chip_t*,
                                 img4_chip_select_cryptex1_boot());
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentCryptex1BootReduced(void)
{
    return IMG4_CHIP_CRYPTEX1_BOOT_REDUCED;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentCryptex1PreBoot(void)
{
    return __unsafe_forge_single(const img4_chip_t*,
                                 img4_chip_select_cryptex1_preboot());
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentCryptex1Generic(void)
{
    return IMG4_CHIP_CRYPTEX1_GENERIC;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentCryptex1GenericSupplemental(void)
{
    return IMG4_CHIP_CRYPTEX1_GENERIC_SUPPLEMENTAL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentMobileAssetCodeLoad(void)
{
    /*
     * If IMG4_CHIP_CRYPTEX1_ASSET_CODE_LOAD isn't defined for the XNU-SDK, then
     * we define IMG4_CHIP_CRYPTEX1_ASSET_CODE_LOAD to be NULL. This means that this
     * chip-environment function will return NULL.
     *
     * This is acceptable because the chipEnvironment() function pointer is never
     * accessed directly within XNU. In order to get the proper defintion of this
     * chip into the XNU-SDK, we need to update the AppleImage4 headers which are
     * copy-pasted into XNU. While we should do this, we also don't want to entangle
     * submissions for these projects.
     */
    return IMG4_CHIP_CRYPTEX1_ASSET_CODE_LOAD;
}

#pragma mark Nonce Domains

static inline const Img4NonceDomain_t*
img4NonceDomainTrustCache(void)
{
    return IMG4_NONCE_DOMAIN_TRUST_CACHE;
}

static inline const Img4NonceDomain_t*
img4NonceDomainPDI(void)
{
    return IMG4_NONCE_DOMAIN_PDI;
}

static inline const Img4NonceDomain_t*
img4NonceDomainDDI(void)
{
    return IMG4_NONCE_DOMAIN_DDI;
}

static inline const Img4NonceDomain_t*
img4NonceDomainCryptex(void)
{
    return IMG4_NONCE_DOMAIN_CRYPTEX;
}

static inline const Img4NonceDomain_t*
img4NonceDomainEphemeralCryptex(void)
{
    return IMG4_NONCE_DOMAIN_EPHEMERAL_CRYPTEX;
}

#pragma mark Firmware Flags

/*
 * These are kept as defines instead of as an enumeration because AppleImage4
 * declares these using a closed enumeration, and we cannot redeclare that same
 * enumeration without suffering re-definiton errors. By keeping them as macros,
 * we don't lose any semantic type constraints placed on them by the compiler.
 */

#define kImg4FirmwareFlagInit IMG4_FIRMWARE_FLAG_INIT
#define kImg4FirmwareFlagRespectAMNM IMG4_FIRMWARE_FLAG_RESPECT_AMNM
#define kImg4FirmwareFlagRespectSubsequentStage IMG4_FIRMWARE_FLAG_SUBSEQUENT_STAGE

#else

typedef uint8_t Img4Runtime_t;
typedef uint8_t Img4ChipEnvironment_t;
typedef uint8_t Img4NonceDomain_t;
typedef uint8_t Img4FirmwareFlags_t;
typedef uint8_t* Img4Image_t;
typedef uint32_t Img4FourCC_t;

#pragma mark Chip Environments

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentPersonalized(void)
{
    return NULL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentCategorized(void)
{
    return NULL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentGlobalFF00(void)
{
    return NULL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentGlobalFF01(void)
{
    return NULL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentGlobalFF06(void)
{
    return NULL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentSupplemental(void)
{
    return NULL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentMobileAsset(void)
{
    return NULL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentCryptex1Boot(void)
{
    return NULL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentCryptex1BootReduced(void)
{
    return NULL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentCryptex1PreBoot(void)
{
    return NULL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentCryptex1Generic(void)
{
    return NULL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentCryptex1GenericSupplemental(void)
{
    return NULL;
}

static inline const Img4ChipEnvironment_t*
img4ChipEnvironmentMobileAssetCodeLoad(void)
{
    return NULL;
}

#pragma mark Nonce Domains

static inline const Img4NonceDomain_t*
img4NonceDomainTrustCache(void)
{
    return NULL;
}

static inline const Img4NonceDomain_t*
img4NonceDomainPDI(void)
{
    return NULL;
}

static inline const Img4NonceDomain_t*
img4NonceDomainDDI(void)
{
    return NULL;
}

static inline const Img4NonceDomain_t*
img4NonceDomainCryptex(void)
{
    return NULL;
}

static inline const Img4NonceDomain_t*
img4NonceDomainEphemeralCryptex(void)
{
    return NULL;
}

#pragma mark Firmware Flags

#define kImg4FirmwareFlagInit 0
#define kImg4FirmwareFlagRespectAMNM 1
#define kImg4FirmwareFlagRespectSubsequentStage 2

#endif

__END_DECLS
#endif /* libTrustCache_Image4_h */
