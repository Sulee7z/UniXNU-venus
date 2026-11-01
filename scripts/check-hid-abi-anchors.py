#!/usr/bin/env python3
"""Check the sheng HID ABI fixed anchors against this Venus kernel."""
import json
from pathlib import Path
import struct
import sys

ROOT = Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
sys.path.insert(0, str(ROOT / 'tree/kits/XnuPrelink'))
from native_prelink import macho, backed_offset, exports

blob = (ROOT / 'kernel/kernel.macho').read_bytes()
plan = json.loads((ROOT / 'kernel/kernel.json').read_text())
image = macho(blob)
names = {n: a for a, g in exports(blob, image).items() for n in g}


def read(va, n):
    at = backed_offset(image['segments'], va, n, len(blob))
    return blob[at:at + n]


extent = next(e for e in plan['extents'] if e['module'] == 'com.apple.iokit.IOHIDFamily' and e['segment'] == '__TEXT_EXEC')
import hashlib
text_sha = hashlib.sha256(read(extent['va'], extent['size'])).hexdigest()
print('HID text sha', text_sha)
print('matches sheng', text_sha == '7e4c5104814f2e773d5be13d092dec53ee44ba5a61a81264b229780406e86b72')
vptr = 0xfffffff005d045c0
methods = struct.unpack('<207Q', read(vptr, 207 * 8))
base = struct.unpack('<168Q', read(names['__ZTV9IOService'] + 16, 168 * 8))
changed = [i for i in range(168) if methods[i] != base[i]]
print('changed native-base slots', changed)
print('pure slots', [i for i, a in enumerate(methods) if a == names['___cxa_pure_virtual']])
print('tail24 zero', read(vptr + 207 * 8, 24) == bytes(24))
print('C2 bytes', read(0xfffffff004ad94f8, 0x20).hex())
print('C2 IOService C2', hex(struct.unpack('<Q', read(0xfffffff005d00f10, 8))[0]), hex(names['__ZN9IOServiceC2EPK11OSMetaClass']))
print('D2 IOService D2', hex(struct.unpack('<Q', read(0xfffffff005d00f18, 8))[0]), hex(names['__ZN9IOServiceD2Ev']))
print('start bytes', read(0xfffffff004ad9aec, 0x34).hex())
print('report bytes', read(0xfffffff004add110, 28).hex())
print('method181', hex(methods[181]))
