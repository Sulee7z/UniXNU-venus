#!/usr/bin/env python3
"""Build the Venus legacy display archive from the audited original ABI.

This follows the sheng success record's display order:
  audited original Legacy ABI -> NativeLegacyDisplay + bindings ->
  LegacyDisplayProbe -> NativeGOPPresenter -> late display archive.
It builds the actual display sources and empty stubs for board probes that
Venus does not implement yet. It does not publish a display or scan out a
frame; those require runtime observation.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/native-legacy-display'
OUT.mkdir(parents=True, exist_ok=True)
KERNEL = ROOT.parent / 'kernel/kernel.macho'
PLAN = ROOT.parent / 'kernel/kernel.json'
AUDIT = ROOT / 'build/display-analysis/mobile-graphics-legacy-abi.json'
# LLVM 18 supports Mach-O section removal; LLVM 23 does not. The late-init
# helper uses llvm-objcopy and then exports the own initializer in Python.
os.environ['PATH'] = ('/root/unixnu-toolchain/llvm/bin:/root/unixnu-toolchain/CommandLineTools/usr/bin:'
                      '/usr/lib/llvm-18/bin:' + os.environ.get('PATH', ''))
# xcrun on Linux is a shim that needs the same fakeroot the kernel build uses.
fakeroot = ROOT / '.cache/fakeroot'
os.environ.setdefault('UNIXNU_SDKROOT', str(fakeroot))
os.environ.setdefault('UNIXNU_SDK_VERSION', '17.0')
os.environ.setdefault('UNIXNU_PLATFORM_PATH', str(fakeroot / 'Platforms/iPhoneOS.platform'))
# The source-kernel records are compiled with -Werror; upstream clang diagnoses
# two warnings Apple's clang does not. The UniXNU kernel build applies these
# overrides through CCC_OVERRIDE_OPTIONS, and the archive builders must too.
os.environ.setdefault('CCC_OVERRIDE_OPTIONS',
                      '# +-Wno-missing-designated-field-initializers +-Wno-unused-but-set-global')
sys.path.insert(0, str(ROOT / 'kits/XnuPrelink'))
from native_prelink import macho, backed_offset, exports


def run(cmd, **kw):
    return subprocess.check_output([str(x) for x in cmd], timeout=180, **kw)


def require(value, why):
    if not value:
        raise SystemExit(why)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


blob = KERNEL.read_bytes()
image = macho(blob)
audit = json.loads(AUDIT.read_text())
methods = audit['methods']
pure = audit['abstract_slots']
legacy_vptr = int(audit['legacy_vptr'], 16)
base_vptr = int(audit['base_vptr'], 16)
service_vptr = int(audit['service_vptr'], 16)
require(audit['static_dispatch_audit'] and len(methods) == 358 and
        pure == [211, 213, 245, 246, 306, 307, 337, 338, 345],
        'Unexpected audited Legacy ABI')
require(sha(KERNEL) == audit['kernel_sha256'], 'Audit belongs to a different Venus kernel')


def read(va, size):
    at = backed_offset(image['segments'], va, size, len(blob))
    return blob[at:at + size]


# Generate the opaque original superclass ABI used by NativeLegacyDisplay.cpp.
header = '''// SPDX-License-Identifier: BSD-2-Clause-Patent
// Opaque ABI storage for the exact original class, not source-level access
// to its private fields. The actual original metadata supplies its full
// Framebuffer/Service/IOService ancestry.
#pragma once
#include <IOKit/IOService.h>
#include <libkern/libkern.h>
struct OriginalLegacySwapRequest;
class IOMobileFramebufferLegacy : public IOService {
 OSDeclareAbstractStructors(IOMobileFramebufferLegacy)
 unsigned char originalPrivate[0x18a0-sizeof(IOService)];
public:
 void installBootDimensions(uint32_t width,uint32_t height) {
  *reinterpret_cast<uint32_t *>(reinterpret_cast<unsigned char *>(this)+5808)=width;
  *reinterpret_cast<uint32_t *>(reinterpret_cast<unsigned char *>(this)+5812)=height;
 }
 const OriginalLegacySwapRequest *pendingSwapRequest() const {
  const OriginalLegacySwapRequest *request=nullptr;
  memcpy(&request,reinterpret_cast<const unsigned char *>(this)+5480,sizeof(request));return request;
 }
 bool activateOnlyPendingSwap(const OriginalLegacySwapRequest *request) {
  auto self=reinterpret_cast<unsigned char *>(this);
  auto bytes=reinterpret_cast<const unsigned char *>(request);
  const void *current=nullptr,*head=nullptr,*tail=nullptr,*next=nullptr,*previous=nullptr;
  memcpy(&current,self+5472,8);memcpy(&head,self+5480,8);memcpy(&tail,self+5488,8);
  if(!request || current || head!=request)return false;
  memcpy(&next,bytes+2960,8);memcpy(&previous,bytes+2968,8);
  if(previous!=self+5480)return false;
  if(next) {
   const void *link=self+5480;
   memcpy(const_cast<unsigned char *>(reinterpret_cast<const unsigned char *>(next))+2968,&link,8);
  } else if(tail!=bytes+2960)return false;
  memcpy(self+5472,&request,8);
  if(next) {memcpy(self+5480,&next,8);}
  else {const void *empty=nullptr,*emptyTail=self+5480;memcpy(self+5480,&empty,8);memcpy(self+5488,&emptyTail,8);}
  return true;
 }
 void free() override;
 bool init(OSDictionary *properties=nullptr) override;
 IOReturn setProperties(OSObject *) override;
 void systemWillShutdown(IOOptionBits) override;
 IOService *probe(IOService *,SInt32 *) override;
 bool start(IOService *) override;
 void stop(IOService *) override;
 IOWorkLoop *getWorkLoop() const override;
 IOReturn newUserClient(task_t,void *,UInt32,IOUserClient **) override;
 IOReturn setPowerState(unsigned long,IOService *) override;
'''
for i in range(168, 358):
    if i == 184:
        header += ' virtual bool isMainDisplay();\n'
    elif i == 188:
        header += ' virtual IOReturn getDotPitch(uint32_t *);\n'
    elif i == 213:
        header += ' virtual IOReturn supportedFrameInfo(uint32_t,uint32_t *,char *,uint32_t *)=0;\n'
    elif i == 249:
        header += ' virtual void getDisplayDimensions(uint32_t *,uint32_t *);\n'
    elif i == 290:
        header += ' virtual void kickSwapQueue();\n'
    elif i == 296:
        header += ' virtual bool validateSwap(const OriginalLegacySwapRequest *);\n'
    elif i == 295:
        header += ' virtual void completeCurrentSwap();\n'
    elif i == 337:
        header += ' virtual IOReturn collectCompletionReports(uint32_t,void *,uint32_t *,uint32_t)=0;\n'
    elif i == 288:
        header += ' virtual bool startHardware();\n'
    elif i == 301:
        header += ' virtual bool getRefreshAttributes(uint64_t *,bool);\n'
    elif i in pure:
        header += f' virtual __attribute__((noreturn)) void opaque{i}()=0;\n'
    else:
        header += f' virtual __attribute__((deprecated("Unclassified ABI: never call from source"))) void opaque{i}();\n'
header += '};\nstatic_assert(sizeof(IOMobileFramebufferLegacy)==0x18a0,"Actual original instance extent");\n'
(OUT / 'OriginalLegacyFramebufferABI.h').write_text(header)

# Build NativeLegacyDisplay from the original class. The generated header is in
# OUT, which build-arm-driver adds to the include path for the auxiliary target.
print(run(['python3', ROOT / 'scripts/build-arm-driver.py', 'NativeLegacyDisplay'], text=True), end='')
obj = OUT / 'NativeLegacyDisplay.o'
raw = obj.read_bytes()
image_obj = macho(raw)
st = next(p for c, p, _ in image_obj['commands'] if c == 2)
sy, count, strings, _ = struct.unpack_from('<4I', raw, st + 8)
symbols = []
for i in range(count):
    ix, kind, section, _, va = struct.unpack_from('<IBBHQ', raw, sy + i * 16)
    symbols.append((raw[strings + ix:raw.index(b'\0', strings + ix)].decode(), va, kind))
native_vtable = next(va for name, va, _ in symbols if name == '__ZTV19NativeLegacyDisplay')
require(native_vtable, 'NativeLegacyDisplay vtable missing')
relocations = {}
for segment in image_obj['segments']:
    for section in segment['sections']:
        if section['va'] <= native_vtable < section['va'] + section['size']:
            ro, rc = struct.unpack_from('<2I', raw, section['command_offset'] + 56)
            for index in range(rc):
                address, word = struct.unpack_from('<2I', raw, ro + index * 8)
                if word >> 27 & 1 and word >> 28 == 0 and word >> 25 & 3 == 3:
                    relocations[section['va'] + address] = symbols[word & 0xffffff][0]
compiled = [relocations.get(native_vtable + 16 + i * 8) for i in range(358)]
require(all(compiled) and native_vtable + 16 + 358 * 8 not in relocations,
        'NativeLegacyDisplay does not own a complete 358-entry dispatch table')
names = {name: value for value, group in exports(blob, image).items() for name in group}
bindings = {}
for i, name in enumerate(compiled):
    expected = int(methods[i]['address'], 16)
    if name.startswith(('__ZN19NativeLegacyDisplay', '__ZNK19NativeLegacyDisplay')):
        require(i in (0, 1, 7, 14, 84, 86, 87, 141, 155, 184, 188, 288, 290, 296, 301) or i in pure,
                'Unexpected owned Legacy override at slot ' + str(i))
    elif '25IOMobileFramebufferLegacy' in name:
        require(i not in pure, 'Unresolved original abstract Legacy target')
        bindings[name] = expected
    else:
        require(i < 168 and names.get(name) == expected,
                'Unexpected inherited native method at slot ' + str(i))
late = OUT / 'NativeLegacyDisplay.late.o'
run(['python3', ROOT / 'scripts/macho-late-init.py', obj, late,
     '--initializer', '__GLOBAL__sub_I_NativeLegacyDisplay.cpp'])


def code(data):
    info = macho(data)
    section = next(s for g in info['segments'] for s in g['sections'] if s['name'] == '__text')
    return data[section['fileoff']:section['fileoff'] + section['size']]


require(code(raw) == code(late.read_bytes()), 'Only the owned initializer registration changed')

# The original class imports are bound to the audited original methods.
bindings.update({
    '__ZN25IOMobileFramebufferLegacyC2EPK11OSMetaClass': 0xfffffff0057865cc,
    '__ZN25IOMobileFramebufferLegacyD2Ev': 0xfffffff005786618,
    '__ZN25IOMobileFramebufferLegacy10gMetaClassE': 0xfffffff006b35940,
    '__ZTV25IOMobileFramebufferLegacy': legacy_vptr - 16,
})
# The display backend reads IOSurface fields and calls the original vsync and
# refresh-property senders. These are exact original-family methods observed
# through the qualified swap request, not substituted layouts.
for name, address, field, wide in [
    ('descriptor', 0xfffffff004b9ead0, 48, True),
    ('width', 0xfffffff004b9ebbc, 88, True),
    ('height', 0xfffffff004b9ebc4, 96, True),
    ('stride', 0xfffffff004b9ebd4, 104, True),
    ('allocation', 0xfffffff004b9ebfc, 144, True),
    ('format', 0xfffffff004b9ebac, 128, False),
    ('planes', 0xfffffff004b9ebf4, 152, False),
]:
    expected = (0xf9400000 if wide else 0xb9400000) | ((field // (8 if wide else 4)) << 10)
    require(read(address, 8) == struct.pack('<2I', expected, 0xd65f03c0),
            'Exact original surface getter ' + name)
    bindings['_native_legacy_surface_' + name] = address
require(read(0xfffffff005796720, 16) == bytes.fromhex('ff0302d1fd7b07a9fdc30191a0831ff8') and
        read(0xfffffff005796830, 4) == bytes.fromhex('08ed4af9') and
        read(0xfffffff00579685c, 16) == bytes.fromhex('e2230091c3008052240080521684ff97') and
        read(0xfffffff005795fbc, 4) == bytes.fromhex('0ab182d2'),
        'Original vsync sender and queue differ')
bindings['_native_legacy_vsync_notify'] = 0xfffffff005796720
require(read(0xfffffff00579ebb8, 16) == bytes.fromhex('ff0302d1fd7b07a9fdc30191a0031ff8') and
        read(0xfffffff00579ed54, 16) == bytes.fromhex('086540f90173ff90218c0c9100013fd6'),
        'Original refresh-property sender differs')
bindings['_native_legacy_set_refresh_properties'] = 0xfffffff00579ebb8
asm = OUT / 'original-bindings.S'
asm.write_text(''.join(f'.globl {name}\n.set {name}, {va:#x}\n' for name, va in sorted(bindings.items())))
sdk = run(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
run(['xcrun', 'clang', '-target', 'arm64-apple-ios17.0', '-isysroot', sdk, '-Werror', '-c',
     asm, '-o', OUT / 'original-bindings.o'])

# LegacyDisplayProbe is the sheng success record's registration/observation
# layer. Its non-display board probes are satisfied by DisplayProbeStubs.c.
record = json.loads((ROOT / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json').read_text().strip().rstrip(','))


def compile_cpp(source, destination):
    cmd = []
    args = record['arguments']
    i = 0
    while i < len(args):
        value = args[i]
        if value == record['file']:
            cmd.append(str(source))
        elif value == '-o':
            cmd += ['-o', str(destination)]
            i += 1
        elif value == '-Xclang' and args[i + 1].startswith('-W'):
            i += 1
        elif not value.startswith('-W'):
            cmd.append(value)
        i += 1
    cmd += ['-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', '-Wno-unnecessary-virtual-specifier',
            '-Wno-c99-designator', '-Wno-reorder-init-list', '-Wno-deprecated-enum-enum-conversion',
            '-I', str(ROOT / '.cache/xnu-work/osfmk'), '-I', str(ROOT / 'drivers/GopFramebuffer'),
            '-I', str(OUT), '-I', str(ROOT / 'kits/venus')]
    run(cmd, cwd=record['directory'])


sources = ROOT / 'kits/venus/LegacyDisplayProbe.cpp'
compile_cpp(sources, OUT / 'LegacyDisplayProbe.o')

# The same OS-17 AppleKeyStore stand-in as sheng/qemu/tb128fu. It answers the
# state queries only; it is not key storage. Without it MKBEventsRegister
# fails, liveactivitiesd crashes, chronod waits and SpringBoard never takes
# the display. The event service registers through a deferred initializer.
keystore_probe = ROOT / 'kits/venus/KeyStoreProbe.cpp'
compile_cpp(keystore_probe, OUT / 'KeyStoreProbe.o')
keyevents_source = ROOT / 'drivers/AppleKeyStoreState/NativeKeyStoreEvents.cpp'
require(keyevents_source.is_file(), 'AppleKeyStoreState component source is missing from the build tree')
compile_cpp(keyevents_source, OUT / 'NativeKeyStoreEvents.o')
keyevents_late = OUT / 'NativeKeyStoreEvents.late.o'
run(['python3', ROOT / 'scripts/macho-late-init.py', OUT / 'NativeKeyStoreEvents.o', keyevents_late,
     '--initializer', '__GLOBAL__sub_I_NativeKeyStoreEvents.cpp'])
require(code((OUT / 'NativeKeyStoreEvents.o').read_bytes()) == code(keyevents_late.read_bytes()),
        'Only the owned key-store initializer registration changed')

# ShengHidInput: an offline keyboard/Home HID device on the unchanged original
# IOHIDDevice/IOHIDEventDriver. It gives SpringBoard the input service the
# CPU-rendered qemu/tb128fu references have; the touch source is still absent.
hid_probe = ROOT / 'kits/venus/HidInputProbe.cpp'
compile_cpp(hid_probe, OUT / 'HidInputProbe.o')
hid_dir = ROOT / 'build/sheng-hid-input'
hid_late = hid_dir / 'NativeHidInput.late.o'
hid_bindings = hid_dir / 'hid-original-bindings.o'
require(hid_late.is_file() and hid_bindings.is_file(),
        'ShengHidInput component outputs are missing; the component archive must run first')

# Empty board-probe stand-ins for this display-only stage.
startup = json.loads((ROOT / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/osfmk/DEVELOPMENT/startup.o.json').read_text().strip().rstrip(','))
stubs_cmd = []
pa = startup['arguments']
j = 0
while j < len(pa):
    value = pa[j]
    if value == startup['file']:
        stubs_cmd.append(str(ROOT / 'kits/venus/DisplayProbeStubs.c'))
    elif value in ('-o', '-MF', '-MT', '-MJ'):
        if value == '-o':
            stubs_cmd += ['-o', str(OUT / 'DisplayProbeStubs.o')]
        j += 1
    elif value == '-Xclang' and pa[j + 1].startswith('-W'):
        j += 1
    elif not value.startswith('-W'):
        stubs_cmd.append(value)
    j += 1
stubs_cmd += ['-Wall', '-Wextra', '-Werror', '-mgeneral-regs-only', '-I', str(ROOT / '.cache/xnu-work/osfmk')]
run(stubs_cmd, cwd=startup['directory'])

# Presenter owns the GOP scanout copy; it is a separate late-initialized class.
print(run(['python3', ROOT / 'scripts/build-arm-driver.py', 'NativeGOPPresenter'], text=True), end='')
gop = ROOT / 'build/native-gop-presenter'
gop_obj = gop / 'NativeGOPPresenter.o'
gop_late = gop / 'NativeGOPPresenter.late.o'
run(['python3', ROOT / 'scripts/macho-late-init.py', gop_obj, gop_late,
     '--initializer', '__GLOBAL__sub_I_NativeGOPPresenter.cpp'])
require(code(gop_obj.read_bytes()) == code(gop_late.read_bytes()),
        'Only the presenter initializer registration changed')

# The late archive is exactly the display/provider set; no non-display probe
# is linked in this first display-only candidate.
archive = OUT / 'libNativeLegacyDisplay.late.a'
archive.unlink(missing_ok=True)
run(['xcrun', 'ar', 'rcs', archive, late, OUT / 'original-bindings.o',
     OUT / 'LegacyDisplayProbe.o', OUT / 'DisplayProbeStubs.o', gop_late,
     OUT / 'KeyStoreProbe.o', keyevents_late, OUT / 'HidInputProbe.o', hid_late, hid_bindings])

report_sources = [ROOT / 'drivers/GopFramebuffer/NativeLegacyDisplay.cpp',
                  ROOT / 'drivers/GopFramebuffer/NativeLegacyRequest.h',
                  ROOT / 'drivers/GopFramebuffer/NativeGOPPresenter.cpp',
                  ROOT / 'drivers/GopFramebuffer/NativeGOPWire.h',
                  sources, keystore_probe, keyevents_source, hid_probe,
                  ROOT / 'drivers/ShengHidInput/NativeHidInput.cpp',
                  ROOT / 'scripts/build-sheng-hid-input.py',
                  ROOT / 'kits/venus/DisplayProbeStubs.c', OUT / 'OriginalLegacyFramebufferABI.h']
(OUT / 'build-report.json').write_text(json.dumps({
    'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in report_sources},
    'audit_sha256': sha(AUDIT), 'kernel_sha256': sha(KERNEL),
    'generated_abi_sha256': sha(OUT / 'OriginalLegacyFramebufferABI.h'),
    'compiled_object_sha256': sha(obj), 'late_object_sha256': sha(late),
    'archive_sha256': sha(archive), 'bindings': {n: hex(v) for n, v in bindings.items()},
    'native_vtable': hex(native_vtable), 'virtual_entries': 358, 'abstract_slots': pure,
    'board_probe_stubs': ['native_touch_probe',
                          'sheng_cpufreq_probe', 'sheng_wifi_probe',
                          'sheng_adsp_probe', 'sheng_battery_probe', 'sheng_audio_probe',
                          'sheng_buttons_probe', 'sheng_backlight_probe', 'sheng_dpu_probe'],
    'hid_input': {'probe': 'kits/venus/HidInputProbe.cpp',
                  'component': 'drivers/ShengHidInput/NativeHidInput.cpp',
                  'abi_audit': 'build/sheng-hid-input/abi-audit.json',
                  'scope': 'offline keyboard/Home HID device; no touch source on Venus yet'},
    'key_store_state': {'probe': 'kits/venus/KeyStoreProbe.cpp',
                        'component': 'drivers/AppleKeyStoreState/NativeKeyStoreEvents.cpp',
                        'late_initializer': '__GLOBAL__sub_I_NativeKeyStoreEvents.cpp',
                        'capability': 'offline keybag/state queries only; no keys or data protection'},
    'original_instructions_modified': False, 'driver_initialized': False,
    'display_presented': False, 'desktop': False,
}, indent=2) + '\n')
print('Built the Venus display archive from the audited original Legacy ABI; runtime display still unverified')
