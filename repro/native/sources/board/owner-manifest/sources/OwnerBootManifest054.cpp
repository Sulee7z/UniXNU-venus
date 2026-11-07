// SPDX-License-Identifier: BSD-2-Clause-Patent
// UFS-only binding for the official development owner boot-set publisher.
// Immutable signed policies remain the authority; no Apple identity is claimed.
#include <IOKit/IOBSD.h>
#include <IOKit/IOService.h>
#include <IOKit/storage/IOMedia.h>
#include <libkern/c++/OSDictionary.h>
#include <libkern/c++/OSIterator.h>
#include <libkern/c++/OSNumber.h>
#include <libkern/c++/OSString.h>
#include <libkern/libkern.h>
#include <pexpert/pexpert.h>
#include <sys/param.h>
#include <sys/types.h>

#if !DEVELOPMENT && !DEBUG
#error Owner boot-set publication is a development instrument
#endif

extern "C" int native_ufs_block_authenticates(IOService *, const char *, uint8_t *);
extern "C" int native_owner_publish_boot_manifest(dev_t, const char *, dev_t, const char *);
extern "C" volatile int native_owner_boot_manifest_status;
extern "C" uint8_t native_owner_boot_manifest_hash[48];
extern volatile uint32_t native_ufs_integrity_failures;
extern "C" volatile int native_ufs_owner_root_accepted;
extern "C" char native_ufs_owner_root_uuid[37];

static const char rootUUID[] = "B6C635B2-67F6-4034-B5D5-539E4D03D1EC";
static const char systemUUID[] = "B792C617-C87F-4706-9CD3-4C3A034C27CB";

// Matching is consumed only once and all matches must be examined. Retained
// iterator objects keep the selected media alive during the provider walk.
extern "C" int
native_verified_block_manifest_sha384(dev_t device, const char *uuid, uint8_t digest[48])
{
    if (!digest) return 0;
    bzero(digest, 48);
    if (!uuid || strnlen(uuid, 37) != 36 || device == NODEV || native_ufs_integrity_failures) return 0;
    OSDictionary *matching = IOService::serviceMatching("IOMedia");
    OSDictionary *properties = OSDictionary::withCapacity(2);
    OSNumber *mjr = OSNumber::withNumber(static_cast<unsigned>(major(device)), 32);
    OSNumber *mnr = OSNumber::withNumber(static_cast<unsigned>(minor(device)), 32);
    if (!matching || !properties || !mjr || !mnr) {
        OSSafeReleaseNULL(mnr); OSSafeReleaseNULL(mjr);
        OSSafeReleaseNULL(properties); OSSafeReleaseNULL(matching);
        return 0;
    }
    bool ready = properties->setObject(kIOBSDMajorKey, mjr) && properties->setObject(kIOBSDMinorKey, mnr) &&
        matching->setObject("IOPropertyMatch", properties);
    mnr->release(); mjr->release(); properties->release();
    OSIterator *iterator = ready ? IOService::getMatchingServices(matching) : nullptr;
    matching->release();
    if (!iterator) return 0;
    unsigned matches = 0;
    bool authorized = false;
    while (OSObject *object = iterator->getNextObject()) {
        if (++matches != 1) { authorized = false; break; }
        IOMedia *media = OSDynamicCast(IOMedia, object);
        if (!media || media->isWritable()) continue;
        OSString *identity = OSDynamicCast(OSString, media->getProperty("UUID"));
        if (!identity || identity->getLength() != 36 || strcmp(uuid, identity->getCStringNoCopy())) continue;
        unsigned depth = 0;
        for (IOService *provider = media; provider && depth < 64; provider = provider->getProvider()) {
            ++depth;
            int verdict = native_ufs_block_authenticates(provider, uuid, digest);
            if (verdict >= 0) { authorized = verdict == 1; break; }
        }
    }
    iterator->release();
    if (!authorized || matches != 1 || native_ufs_integrity_failures) {
        bzero(digest, 48);
        return 0;
    }
    return 1;
}

static int
venus_owner054_system_device(dev_t *device)
{
    *device = NODEV;
    OSDictionary *matching = IOService::serviceMatching("IOMedia");
    OSDictionary *properties = OSDictionary::withCapacity(1);
    OSString *uuid = OSString::withCString(systemUUID);
    if (!matching || !properties || !uuid) {
        OSSafeReleaseNULL(uuid); OSSafeReleaseNULL(properties); OSSafeReleaseNULL(matching);
        return 0;
    }
    bool ready = properties->setObject("UUID", uuid) && matching->setObject("IOPropertyMatch", properties);
    uuid->release(); properties->release();
    OSIterator *iterator = ready ? IOService::getMatchingServices(matching) : nullptr;
    matching->release();
    if (!iterator) return 0;
    unsigned matches = 0;
    bool valid = false;
    dev_t selected = NODEV;
    while (OSObject *object = iterator->getNextObject()) {
        if (++matches != 1) { valid = false; break; }
        IOMedia *media = OSDynamicCast(IOMedia, object);
        if (!media || media->isWritable()) continue;
        OSNumber *mjr = OSDynamicCast(OSNumber, media->getProperty(kIOBSDMajorKey));
        OSNumber *mnr = OSDynamicCast(OSNumber, media->getProperty(kIOBSDMinorKey));
        if (!mjr || !mnr || mjr->unsigned64BitValue() > 255 || mnr->unsigned64BitValue() > 0xffffff) continue;
        selected = makedev(mjr->unsigned32BitValue(), mnr->unsigned32BitValue());
        valid = selected != NODEV;
    }
    iterator->release();
    if (!valid || matches != 1) return 0;
    *device = selected;
    return 1;
}

extern "C" int
venus_owner054_publish_for_root(dev_t actual, dev_t selected, int readonly)
{
    uint32_t enabled = 0, persist = 0;
    if (!PE_parse_boot_argn("venus-owner-manifest", &enabled, sizeof(enabled)) || enabled != 1) return 1;
    dev_t systemDevice = NODEV;
    if (!PE_parse_boot_argn("sheng-data-persist", &persist, sizeof(persist)) || persist != 1 ||
        !readonly || actual == NODEV || actual != selected || !native_ufs_owner_root_accepted ||
        strcmp(native_ufs_owner_root_uuid, rootUUID) || native_ufs_integrity_failures ||
        !venus_owner054_system_device(&systemDevice)) {
        printf("OwnerBoot054: refused root/data/media prerequisites\n");
        return 0;
    }
    int result = native_owner_publish_boot_manifest(actual, rootUUID, systemDevice, systemUUID);
    printf("OwnerBoot054: published=%d status=%d root=%u:%u systemos=%u:%u readonly=%d\n",
        result, native_owner_boot_manifest_status, major(actual), minor(actual),
        major(systemDevice), minor(systemDevice), readonly);
    if (result) {
        static const char hex[] = "0123456789ABCDEF";
        char text[97];
        for (unsigned i = 0; i < 48; ++i) {
            text[2 * i] = hex[native_owner_boot_manifest_hash[i] >> 4];
            text[2 * i + 1] = hex[native_owner_boot_manifest_hash[i] & 15];
        }
        text[96] = 0;
        printf("OwnerBoot054: IOGetBootManifestHash readback=%s domain=VerifiedRoot.OwnerBootSet.v1\n", text);
    }
    return result;
}
