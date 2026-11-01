#!/usr/bin/env python3
"""Qualify and build the ShengHidInput component against this Venus kernel.

This is the sheng component recipe with the Venus kernel/plan as the ABI source.
The original IOHIDFamily text, 207-slot device dispatch, constructor binding and
report path were checked against the fixed sheng anchors; the toolchain's
llvm-objcopy cannot remove Mach-O sections, so the owned initializer is staged
with macho-late-init.py instead.
"""
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/sheng-hid-input'
OUT.mkdir(parents=True, exist_ok=True)
KERNEL = ROOT.parent / 'kernel/kernel.macho'
PLAN = ROOT.parent / 'kernel/kernel.json'
HID_TEXT_SHA = '7e4c5104814f2e773d5be13d092dec53ee44ba5a61a81264b229780406e86b72'
sys.path.insert(0, str(ROOT / 'kits/XnuPrelink'))
from native_prelink import macho, backed_offset, exports


def run(cmd, **kw):
    return subprocess.check_output([str(x) for x in cmd], timeout=120, **kw)


def require(value, why):
    if not value:
        raise SystemExit(why)


blob = KERNEL.read_bytes()
plan = json.loads(PLAN.read_text())
require(hashlib.sha256(blob).hexdigest() == plan.get('native_sha256') or
        hashlib.sha256(blob).hexdigest() == plan.get('candidate_sha256'),
        'HID audit kernel does not match its prelink plan')
image = macho(blob)
text = next(e for e in plan['extents'] if e['module'] == 'com.apple.iokit.IOHIDFamily' and e['segment'] == '__TEXT_EXEC')


def read(va, n):
    at = backed_offset(image['segments'], va, n, len(blob))
    return blob[at:at + n]


require(hashlib.sha256(read(text['va'], text['size'])).hexdigest() == HID_TEXT_SHA,
        'The Venus original IOHIDFamily instructions differ from the qualified reference')
names = {n: a for a, group in exports(blob, image).items() for n in group}
vptr = 0xfffffff005d045c0
methods = struct.unpack('<207Q', read(vptr, 207 * 8))
base = struct.unpack('<168Q', read(names['__ZTV9IOService'] + 16, 168 * 8))
changed = [i for i in range(168) if methods[i] != base[i]]
require(changed == [0, 1, 7, 12, 14, 21, 23, 76, 81, 82, 86, 87, 91, 92, 93, 101, 132, 140],
        'Exact original HID native-base overrides')
require([i for i, a in enumerate(methods) if a == names['___cxa_pure_virtual']] == [180] and
        all(methods) and read(vptr + 207 * 8, 24) == bytes(24), 'Exact original 207-slot abstract device')
require(read(0xfffffff004ad94f8, 0x20) == bytes.fromhex(
    'fd7bbfa9fd0300912bd90094489100f008011791080000f9fd7bc1a8c0035fd6'),
    'Original protected constructor and exact vptr store')
require(struct.unpack('<Q', read(0xfffffff005d00f10, 8))[0] == names['__ZN9IOServiceC2EPK11OSMetaClass'],
        'Actual native protected constructor binding')
require(struct.unpack('<Q', read(0xfffffff005d00f18, 8))[0] == names['__ZN9IOServiceD2Ev'],
        'Actual native protected destructor binding')
require(read(0xfffffff004ad9aec, 0x34) == bytes.fromhex(
    '680240f908a142f9e00313aae10314aa00013fd6680240f9603d003608d142f9e1630091e00313aa00013fd6a02d0035e00f40f9'),
    'Original handleStart and report-descriptor ABI')
require(methods[181] == 0xfffffff004add0c4 and read(0xfffffff004add110, 28) == bytes.fromhex(
    '680240f9081543f9e00313aae20316aae30315aae40314aa00013fd6'),
    'Original handleReport forwards timestamp, report, type and options')
header = '''// Generated from the qualified original image; opaque private storage only.
#pragma once
#include <IOKit/IOService.h>
#include <IOKit/IOMemoryDescriptor.h>
class IOHIDDevice : public IOService {
 OSDeclareAbstractStructors(IOHIDDevice)
 unsigned char originalPrivate[0xd0-sizeof(IOService)];
public:
 using IOService::setProperty;
 IOReturn Dispatch(IORPC) override;
 void free() override;
 bool init(OSDictionary *properties=nullptr) override;
 bool setProperty(const OSSymbol *,OSObject *) override;
 bool willTerminate(IOService *,IOOptionBits) override;
 IOReturn configureReport(IOReportChannelList *,IOReportConfigureAction,void *,void *) override;
 IOReturn updateReport(IOReportChannelList *,IOReportUpdateAction,void *,void *) override;
 bool start(IOService *) override;
 void stop(IOService *) override;
 bool handleOpen(IOService *,IOOptionBits,void *) override;
 void handleClose(IOService *,IOOptionBits) override;
 bool handleIsOpen(const IOService *) const override;
 bool matchPropertyTable(OSDictionary *,SInt32 *) override;
 IOReturn message(UInt32,IOService *,void *) override;
 IOReturn newUserClient(task_t,void *,UInt32,OSDictionary *,IOUserClient **) override;
'''
for i in range(168, 207):
    if i == 171:
        header += ' virtual OSString *newTransportString() const;\n'
    elif i == 173:
        header += ' virtual OSString *newProductString() const;\n'
    elif i == 180:
        header += ' virtual IOReturn newReportDescriptor(IOMemoryDescriptor **) const=0;\n'
    elif i == 181:
        header += ' virtual IOReturn handleReport(IOMemoryDescriptor *,unsigned,IOOptionBits);\n'
    else:
        header += f' virtual __attribute__((deprecated("Unqualified prototype: never call from source"))) void opaque{i}();\n'
header += '};\nstatic_assert(sizeof(IOHIDDevice)==0xd0,"Original device instance size");\n'
(OUT / 'OriginalHidDeviceABI.h').write_text(header)
print(run(['python3', ROOT / 'scripts/build-arm-driver.py', 'NativeHidInput'], text=True), end='')
obj = OUT / 'NativeHidInput.o'
raw = obj.read_bytes()
om = macho(raw)
st = next(p for c, p, _ in om['commands'] if c == 2)
sy, count, strings, _ = struct.unpack_from('<4I', raw, st + 8)
symbols = []
for i in range(count):
    ix, kind, section, _, va = struct.unpack_from('<IBBHQ', raw, sy + i * 16)
    symbols.append((raw[strings + ix:raw.index(b'\0', strings + ix)].decode(), va, kind))
vt = next(va for name, va, _ in symbols if name == '__ZTV14NativeHidInput')
relocations = {}
for segment in om['segments']:
    for sec in segment['sections']:
        if sec['va'] <= vt < sec['va'] + sec['size']:
            ro, rc = struct.unpack_from('<2I', raw, sec['command_offset'] + 56)
            for i in range(rc):
                offset, bits = struct.unpack_from('<2I', raw, ro + i * 8)
                if bits >> 27 & 1 and bits >> 28 == 0 and bits >> 25 & 3 == 3:
                    relocations[sec['va'] + offset] = symbols[bits & 0xffffff][0]
compiled = [relocations.get(vt + 16 + i * 8) for i in range(207)]
require(all(compiled) and vt + 16 + 207 * 8 not in relocations, 'Compiled exact 207-slot vtable')
bindings = {'__ZN11IOHIDDeviceC2EPK11OSMetaClass': 0xfffffff004ad94f8,
            '__ZN11IOHIDDeviceD2Ev': 0xfffffff004ad9518,
            '__ZN11IOHIDDevice10gMetaClassE': 0xfffffff006ae6fa0,
            '__ZTV11IOHIDDevice': vptr - 16}
owned = []
for i, name in enumerate(compiled):
    if name.startswith(('__ZN14NativeHidInput', '__ZNK14NativeHidInput')):
        owned.append(i)
    elif '11IOHIDDevice' in name:
        bindings[name] = methods[i]
    else:
        require(i < 168 and names.get(name) == methods[i], 'Actual inherited native method ' + str(i))
require(owned == [0, 1, 7, 14, 86, 87, 111, 171, 173, 180], 'Only qualified HID methods overridden')
undefined = {n for n, _, k in symbols if k == 1 and '11IOHIDDevice' in n}
require(undefined == set(bindings), 'All and only actual original HID imports bound')
asm = OUT / 'hid-original-bindings.S'
asm.write_text(''.join(f'.globl {n}\n.set {n}, {a:#x}\n' for n, a in sorted(bindings.items())))
sdk = run(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
run(['xcrun', 'clang', '-target', 'arm64-apple-ios17.0', '-isysroot', sdk, '-Werror', '-c',
     asm, '-o', OUT / 'hid-original-bindings.o'])
late = OUT / 'NativeHidInput.late.o'
run(['python3', ROOT / 'scripts/macho-late-init.py', obj, late,
     '--initializer', '__GLOBAL__sub_I_NativeHidInput.cpp'])


def code(data):
    info = macho(data)
    sec = next(s for g in info['segments'] for s in g['sections'] if s['name'] == '__text')
    return data[sec['fileoff']:sec['fileoff'] + sec['size']]


require(code(raw) == code(late.read_bytes()), 'Owned HID code unchanged by deferred metaclass registration')
archive = OUT / 'libShengHidInput.a'
archive.unlink(missing_ok=True)
run(['xcrun', 'ar', 'rcs', archive, late, OUT / 'hid-original-bindings.o'])
(OUT / 'abi-audit.json').write_text(json.dumps({
    'kernel_sha256': hashlib.sha256(blob).hexdigest(),
    'original_text_sha256': HID_TEXT_SHA, 'original_slots': 207, 'original_instance_size': 208,
    'owned_slots': owned, 'bindings': {n: hex(v) for n, v in bindings.items()},
    'runtime_qualified': False,
    'source_sha256': hashlib.sha256((ROOT / 'drivers/ShengHidInput/NativeHidInput.cpp').read_bytes()).hexdigest(),
    'deferred_initializer': '__GLOBAL__sub_I_NativeHidInput.cpp',
    'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
}, indent=2) + '\n')
print('PASS: original HID instruction identity, base imports, call boundaries and exact owned vtable')
