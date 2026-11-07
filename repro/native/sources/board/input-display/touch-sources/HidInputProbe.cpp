// SPDX-License-Identifier: BSD-2-Clause-Patent
// Venus virtual keyboard/Home interface over the original KDK25F84 IOHIDFamily.
// Based on zeta; only explicit USB Home requests feed reports.
#include <IOKit/IOService.h>
#include <IOKit/IOCatalogue.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <IOKit/IOTimerEventSource.h>
#include <IOKit/IOWorkLoop.h>
#include <libkern/c++/OSArray.h>
#include <libkern/c++/OSDictionary.h>
#include <libkern/c++/OSNumber.h>
#include <libkern/c++/OSString.h>
#include <libkern/OSKextLib.h>
#include <pexpert/pexpert.h>
#include <string.h>

extern "C" uintptr_t native_kext_symbol(const char *bundleID, const char *symbol);
extern "C" void venus_hid_input_probe(void);
extern "C" void venus_touch061_probe(void);
// Home requests the USB log console counted ("\0ZETA:HOME\n").
extern "C" volatile uint32_t unixnu_dwc3_home_requests;
// [0] stage (1 loaded, 2 bound, 3 started, negative: the step that failed), [1] presses, [2] last down result, [3] last up result,
// [4] event driver attached
extern "C" {volatile int32_t venus_hid_stats[5];}
namespace {
const char kFamily[] = "com.apple.iokit.IOHIDFamily";
// IOHIDDevice vtable, KDK 25F84: slot N is the word at vptr + 8 * N; 334 slots, then a zero word.
constexpr unsigned kSlots = 334;
enum : unsigned {
    kGetWorkLoop = 215, kNewTransportString = 275, kNewProductString = 277, kNewReportDescriptor = 284, kHandleReport = 285,
};
struct SlotName {unsigned slot; const char *symbol;};
const SlotName kChecked[] = {
    {kNewTransportString, "__ZNK11IOHIDDevice18newTransportStringEv"},
    {kNewProductString, "__ZNK11IOHIDDevice16newProductStringEv"},
    {kHandleReport, "__ZN11IOHIDDevice12handleReportEP18IOMemoryDescriptor15IOHIDReportTypej"},
    {22, "__ZN11IOHIDDevice4freeEv"},
    {190, "__ZN11IOHIDDevice5startEP9IOService"},
};
// NativeHidInput's descriptor: a boot keyboard (report 1), so the generic keyboard personality matches, and Consumer Menu (report 2).
const uint8_t kDescriptor[] = {
    0x05,0x01,0x09,0x06,0xa1,0x01,0x85,0x01,
    0x05,0x07,0x19,0xe0,0x29,0xe7,0x15,0x00,0x25,0x01,
    0x75,0x01,0x95,0x08,0x81,0x02,
    0x75,0x08,0x95,0x01,0x81,0x03,
    0x19,0x00,0x29,0x65,0x15,0x00,0x25,0x65,
    0x75,0x08,0x95,0x06,0x81,0x00,
    0x85,0x02,0x05,0x0c,0x09,0x40,0x15,0x00,0x25,0x01,
    0x75,0x01,0x95,0x01,0x81,0x02,
    0x75,0x07,0x95,0x01,0x81,0x03,
    0xc0
};
uintptr_t gTable[2 + kSlots + 1];
uintptr_t gOriginal[kSlots];
IOWorkLoop *gLoop;
IOTimerEventSource *gTimer;
IOService *gDevice;
bool gDown;
unsigned gHomeSeen;

unsigned bootArg(const char *name, unsigned fallback = 0) {
    unsigned value = fallback;
    PE_parse_boot_argn(name, &value, sizeof(value));
    return value;
}
IOWorkLoop *dGetWorkLoop(const IOService *) {return gLoop;}
OSString *dNewTransportString(const IOService *) {return OSString::withCString("Virtual");}
OSString *dNewProductString(const IOService *) {return OSString::withCString("Venus virtual Home input");}
IOReturn dNewReportDescriptor(const IOService *, IOMemoryDescriptor **out) {
    if (!out) return kIOReturnBadArgument;
    *out = IOBufferMemoryDescriptor::withBytes(kDescriptor, sizeof(kDescriptor), kIODirectionNone);
    return *out ? kIOReturnSuccess : kIOReturnNoMemory;
}

IOReturn sendReport(IOService *device, const uint8_t *report, size_t length) {
    IOBufferMemoryDescriptor *buffer = IOBufferMemoryDescriptor::withBytes(report, length, kIODirectionNone);
    using HandleReport = IOReturn (*)(IOService *, IOMemoryDescriptor *, uint32_t, IOOptionBits);
    IOReturn result = buffer ? reinterpret_cast<HandleReport>(gOriginal[kHandleReport])(device, buffer, 0, 0) : kIOReturnNoMemory;
    OSSafeReleaseNULL(buffer);
    return result;
}
IOReturn sendMenu(bool down) {
    const uint8_t report[] = {2, static_cast<uint8_t>(down ? 1 : 0)};
    return sendReport(gDevice, report, sizeof(report));
}
// The IOHIDEventDriver below this device, if one has attached.
IORegistryEntry *eventDriverBelow(IORegistryEntry *parent, unsigned depth) {
    if (!depth) return nullptr;
    OSIterator *it = parent->getChildIterator(gIOServicePlane);
    if (!it) return nullptr;
    IORegistryEntry *found = nullptr;
    while (OSObject *child = found ? nullptr : it->getNextObject()) {
        IORegistryEntry *entry = OSDynamicCast(IORegistryEntry, child);
        if (entry) found = entry->metaCast("IOHIDEventDriver") ? entry : eventDriverBelow(entry, depth - 1);
    }
    it->release();
    return found;
}

bool homeRequested() {
    const uint32_t requests = unixnu_dwc3_home_requests;
    if (requests == gHomeSeen) return false;
    gHomeSeen = requests;
    return true;
}

// The work-loop timer owns each explicit press and its release, even after a failed down.
void tick(OSObject *, IOTimerEventSource *source) {
    if (gDown) {
        venus_hid_stats[3] = sendMenu(false);
        gDown = false;
        source->setTimeoutMS(250);
        return;
    }
    const bool driver = eventDriverBelow(gDevice, 4) != nullptr;
    if (driver != (venus_hid_stats[4] != 0)) {
        venus_hid_stats[4] = driver;
        IOLog("venus-hid: event driver %s\n", driver ? "attached" : "gone");
    }
    if (driver && homeRequested()) {
        venus_hid_stats[2] = sendMenu(true);
        venus_hid_stats[1] = venus_hid_stats[1] + 1;
        gDown = true;
        source->setTimeoutMS(100);
    } else source->setTimeoutMS(250);
}

bool bind() {
    uintptr_t table = native_kext_symbol(kFamily, "__ZTV11IOHIDDevice");
    if (!table) return false;
    const uintptr_t *vtable = reinterpret_cast<const uintptr_t *>(table) + 2;
    if (vtable[kSlots] != 0 || vtable[kSlots - 1] == 0) {
        IOLog("venus-hid: IOHIDDevice vtable is not %u slots\n", kSlots);
        return false;
    }
    for (const auto &entry : kChecked) {
        if (vtable[entry.slot] != native_kext_symbol(kFamily, entry.symbol)) {
            IOLog("venus-hid: slot %u is not %s\n", entry.slot, entry.symbol);
            return false;
        }
    }
    memcpy(gTable, vtable - 2, sizeof(gTable));
    memcpy(gOriginal, vtable, sizeof(gOriginal));
    gTable[2 + kGetWorkLoop] = reinterpret_cast<uintptr_t>(&dGetWorkLoop);
    gTable[2 + kNewTransportString] = reinterpret_cast<uintptr_t>(&dNewTransportString);
    gTable[2 + kNewProductString] = reinterpret_cast<uintptr_t>(&dNewProductString);
    gTable[2 + kNewReportDescriptor] = reinterpret_cast<uintptr_t>(&dNewReportDescriptor);
    return true;
}

// The plug-in's "HID Keyboard Driver" personality, without its pointer acceleration curves (a keyboard has no pointer).
bool addKeyboardPersonality() {
    OSDictionary *personality = OSDictionary::withCapacity(5);
    OSArray *pairs = OSArray::withCapacity(2);
    OSArray *personalities = OSArray::withCapacity(1);
    bool ok = personality && pairs && personalities;
    // The original keyboard/keypad IOHIDEventDriver matching rules.
    static const unsigned kUsages[][2] = {{1, 6}, {1, 7}};
    for (const auto &usage : kUsages) {
        OSDictionary *pair = OSDictionary::withCapacity(2);
        OSNumber *page = OSNumber::withNumber(usage[0], 32), *number = OSNumber::withNumber(usage[1], 32);
        ok = ok && pair && page && number && pair->setObject("DeviceUsagePage", page) && pair->setObject("DeviceUsage", number) &&
            pairs->setObject(pair);
        OSSafeReleaseNULL(page);
        OSSafeReleaseNULL(number);
        OSSafeReleaseNULL(pair);
    }
    if (ok) {
        OSString *bundle = OSString::withCString(kFamily), *ioClass = OSString::withCString("IOHIDEventDriver");
        OSString *provider = OSString::withCString("IOHIDInterface"), *behavior = OSString::withCString("");
        ok = bundle && ioClass && provider && behavior && personality->setObject("CFBundleIdentifier", bundle) &&
            personality->setObject("IOClass", ioClass) && personality->setObject("IOProviderClass", provider) &&
            personality->setObject("HIDDefaultBehavior", behavior) && personality->setObject("DeviceUsagePairs", pairs) &&
            personalities->setObject(personality);
        OSSafeReleaseNULL(bundle);
        OSSafeReleaseNULL(ioClass);
        OSSafeReleaseNULL(provider);
        OSSafeReleaseNULL(behavior);
    }
    ok = ok && gIOCatalogue->addDrivers(personalities, true);
    OSSafeReleaseNULL(personalities);
    OSSafeReleaseNULL(pairs);
    OSSafeReleaseNULL(personality);
    return ok;
}
}  // namespace

// bsd_autoconf, from the display's late probe (before launchd: backboardd matches HID services when it starts).
void venus_hid_input_probe(void) {
    if (bootArg("offline-hid-input") != 1 || bootArg("offline-hid-home") != 1 || venus_hid_stats[0]) return;
    kern_return_t load = OSKextLoadKextWithIdentifier(kFamily);
    venus_hid_stats[0] = load ? -1 : 1;
    if (load) {IOLog("venus-hid: IOHIDFamily load %#x\n", load); return;}
    auto allocate = reinterpret_cast<void *(*)(size_t)>(native_kext_symbol(kFamily, "__ZN11IOHIDDevicenwEm"));
    auto construct = reinterpret_cast<void (*)(void *, const OSMetaClass *)>(
        native_kext_symbol(kFamily, "__ZN11IOHIDDeviceC2EPK11OSMetaClass"));
    auto meta = reinterpret_cast<const OSMetaClass *>(native_kext_symbol(kFamily, "__ZN11IOHIDDevice10gMetaClassE"));
    if (!allocate || !construct || !meta || meta->getClassSize() != 208 || !bind()) {
        venus_hid_stats[0] = -2;
        IOLog("venus-hid: IOHIDDevice not bound (keepsyms=1 keeps the kext symbol tables)\n");
        return;
    }
    venus_hid_stats[0] = 2;
    if (!addKeyboardPersonality()) {venus_hid_stats[0] = -3; IOLog("venus-hid: keyboard personality not added\n"); return;}
    // sheng's provider is the IOHIDResource nub, whose personality waits for IOBSD (published after this probe on zeta); the
    // resource root it would attach to serves as well.
    OSDictionary *match = IOService::serviceMatching("IOHIDResource");
    IOService *resource = match ? IOService::waitForMatchingService(match, 1000000000ULL) : nullptr;
    OSSafeReleaseNULL(match);
    if (!resource && (resource = IOService::getResourceService())) resource->retain();
    gLoop = resource ? IOWorkLoop::workLoop() : nullptr;
    if (!gLoop) {venus_hid_stats[0] = -4; IOLog("venus-hid: no provider (%d)\n", resource != nullptr); OSSafeReleaseNULL(resource); return;}
    IOLog("venus-hid: provider %s\n", resource->getName());
    auto make = [&]() -> IOService * {
        void *memory = allocate(meta->getClassSize());
        if (!memory) return nullptr;
        construct(memory, meta);
        *reinterpret_cast<const uintptr_t **>(memory) = gTable + 2;
        return reinterpret_cast<IOService *>(memory);
    };
    IOService *device = make();
    gDevice = device;
    const bool valid = device && device->init() && device->setProperty("HIDDefaultBehavior", true);
    const bool attached = valid && device->attach(resource);
    const bool started = attached && device->start(resource);
    if (!started) {
        venus_hid_stats[0] = -5;
        IOLog("venus-hid: device init %d attach %d start 0\n", valid, attached);
        if (attached) device->detach(resource);
        OSSafeReleaseNULL(device);
        gDevice = nullptr;
        OSSafeReleaseNULL(resource);
        return;
    }
    OSSafeReleaseNULL(resource);
    gTimer = IOTimerEventSource::timerEventSource(device, tick);
    if (!gTimer || gLoop->addEventSource(gTimer) != kIOReturnSuccess) {
        venus_hid_stats[0] = -6;
        IOLog("venus-hid: no timer\n");
        return;
    }
    gHomeSeen = unixnu_dwc3_home_requests;
    venus_hid_stats[0] = 3;
    IOLog("venus-hid: virtual Home input started\n");
    venus_touch061_probe();
    gTimer->setTimeoutMS(1000);
}

