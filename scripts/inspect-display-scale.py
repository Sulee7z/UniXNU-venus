#!/usr/bin/env python3
"""Inspect original display-scale reads in the retained 6GiB kernel (host only)."""
import hashlib
import json
import re
from pathlib import Path
import struct
import subprocess
import sys

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[1]
WORK = Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
sys.path.insert(0, str(WORK/'tree/kits/XnuPrelink'))
from native_prelink import macho, backed_offset

OUT = ROOT/'artifacts/venus-mode-scale-analysis'
OUT.mkdir(exist_ok=True)
control = ROOT/'artifacts/venus-userspace-6g-001'
candidate = json.loads((control/'candidate.json').read_text())
blob = (control/'kernel/kernel.macho').read_bytes()
assert hashlib.sha256(blob).hexdigest() == candidate['kernel_sha256']
image = macho(blob)
plan = json.loads((control/'kernel/kernel.json').read_text())
extent = next(e for e in plan['extents'] if e['module']=='com.apple.iokit.IOMobileGraphicsFamily' and e['segment']=='__TEXT_EXEC')
def read(va, size):
    at = backed_offset(image['segments'], va, size, len(blob))
    return blob[at:at+size]
text = read(extent['va'], extent['size'])
assert hashlib.sha256(text).hexdigest() == '2e044ee68c1650397e1435234ca6459206262e4c7ed709cb7131c6f664f9bd9b'
strings = {}
family_strings = []
for ext in plan['extents']:
    if ext['module'] != 'com.apple.iokit.IOMobileGraphicsFamily' or ext['segment']=='__TEXT_EXEC': continue
    data = read(ext['va'], ext['size'])
    for match in re.finditer(rb'[\x20-\x7e]{4,}\x00', data):
        if re.search(rb'scale|pitch|resolution', match[0], re.I):
            value = match[0][:-1].decode()
            strings[ext['va']+match.start()] = value
            family_strings.append({'address':hex(ext['va']+match.start()), 'text':value})
for key in (b'display-scale', b'display-rotation', b'IOFBDisplayScale', b'IOMFBDisplayScale', b'preferredScale'):
    start = 0
    while (pos := blob.find(key+b'\0', start)) >= 0:
        start = pos+1
        for segment in image['segments']:
            for section in segment['sections']:
                if section['fileoff'] <= pos < section['fileoff'] + section['size']:
                    va = section['va'] + pos-section['fileoff']
                    strings[va] = key.decode()
regs, refs = {}, []
for off in range(0, len(text)-3, 4):
    pc = extent['va']+off
    word = struct.unpack_from('<I', text, off)[0]
    rd, rn = word&31, (word>>5)&31
    if word&0x9f000000 == 0x90000000:
        imm = ((word>>5)&0x7ffff)*4+((word>>29)&3)
        if imm & (1<<20): imm -= 1<<21
        regs[rd] = (pc&~4095)+(imm<<12)
    elif word&0xffc00000 == 0x91000000 and rn in regs:
        regs[rd] = regs[rn]+((word>>10)&4095)
        if regs[rd] in strings:
            refs.append({'pc':hex(pc), 'string':strings[regs[rd]], 'address':hex(regs[rd])})
    elif word&0xfc000000 == 0x94000000:
        for r in range(19): regs.pop(r, None)
def dump(begin, size, name):
    data = read(begin, size)
    result = subprocess.run(['/usr/bin/llvm-mc','--triple=aarch64','--disassemble'],
        input=' '.join(f'0x{x:02x}' for x in data), text=True, capture_output=True, check=True)
    lines = [s.strip() for s in result.stdout.splitlines() if s.strip() and s.strip()!='.text']
    assert len(lines) == size//4, result.stderr
    (OUT/name).write_text('\n'.join(f'{begin+i*4:#x} {data[i*4:i*4+4].hex()} {line}' for i,line in enumerate(lines))+'\n')
for ref in refs:
    pc = int(ref['pc'],16)
    dump(pc-128, 512, 'kernel-'+ref['pc']+'.txt')
audit = json.loads((ROOT/'artifacts/venus-exit-fault/display-analysis/mobile-graphics-legacy-abi.json').read_text())
dump(int(audit['original_start'],16), 0x1400, 'original-start.txt')
report = {'kernel_sha256': candidate['kernel_sha256'], 'strings':{hex(k):v for k,v in strings.items()},
          'family_strings':family_strings,
          'references':refs, 'original_start':audit['original_start'],
          'scope':'Original instructions and string references; execution order must be checked separately.'}
(OUT/'kernel-scale-refs.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
