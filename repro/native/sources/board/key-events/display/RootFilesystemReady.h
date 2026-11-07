// SPDX-License-Identifier: BSD-2-Clause-Patent
#pragma once
#include <IOKit/IOService.h>
#include <libkern/c++/OSDictionary.h>
#include <libkern/c++/OSSymbol.h>

// Use the same completed-resource predicate as IOFindBSDRoot, not merely the
// presence of the IOBSD property. KDK APFS container startup can otherwise hold
// moduleResourceLock while waiting for the IOBSD match whose APFS service needs
// that same lock. Call only from a separate publisher thread, with no I/O lock.
static IOReturn nativeRootWaitForFilesystemServices(uint64_t timeout)
{
    OSDictionary *matching = IOService::serviceMatching("IOResources");
    const OSSymbol *resource = OSSymbol::withCString("IOBSD");
    IOService *ready = nullptr;
    IOReturn result = kIOReturnNoMemory;
    if (matching && resource && matching->setObject("IOResourceMatched", resource)) {
        ready = IOService::waitForMatchingService(matching, timeout);
        result = ready ? kIOReturnSuccess : kIOReturnTimeout;
    }
    OSSafeReleaseNULL(ready);
    OSSafeReleaseNULL(resource);
    OSSafeReleaseNULL(matching);
    return result;
}
