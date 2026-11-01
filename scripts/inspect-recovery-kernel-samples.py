#!/usr/bin/env python3
"""Locate photographed timer samples in the exact recovery kernel; not faults."""
import bisect
import hashlib
import json
from pathlib import Path
import subprocess
import sys
DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
WORK=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
sys.path.insert(0,str(WORK/'tree/kits/XnuPrelink'))
from native_prelink import macho,backed_offset
kernel=ROOT/'artifacts/venus-data-read-recovery-001/kernel/kernel.macho'
blob=kernel.read_bytes();image=macho(blob)
assert hashlib.sha256(blob).hexdigest()=='aebf1da232089c88c0a2c1534fa72e06addd74c66cf69db18914c8b7b6795460'
symbols=[]
for line in subprocess.check_output(['/usr/bin/llvm-nm',str(kernel)],text=True).splitlines():
    fields=line.split()
    if len(fields)==3 and fields[1] not in ('U','A','a'):
        try:address=int(fields[0],16)
        except ValueError:continue
        if address:symbols.append((address,fields[2]))
symbols.sort();addresses=[v[0] for v in symbols]
plan=json.loads(kernel.with_suffix('.json').read_text())
samples=[]
for pc in (0xfffffff004a3c774,0xfffffff004a411f0):
    i=bisect.bisect_right(addresses,pc)
    nearest=[{'address':hex(a),'name':name,'offset_from_sample':pc-a} for a,name in symbols[max(0,i-4):i]]
    off=backed_offset(image['segments'],pc-16,48,len(blob))
    extents=[e for e in plan['extents'] if e['va']<=pc<e['va']+e['size']]
    samples.append({'sample_pc':hex(pc),'bytes_at_minus16':blob[off:off+48].hex(),'nearest_preceding_symbols':nearest,
                    'original_component_extents':extents})
report={'device':'venus','date':'2026-10-28','kernel_sha256':hashlib.sha256(blob).hexdigest(),
        'samples':samples,'scope':'Manually transcribed timer PC samples; nearest symbols are not a fault/backtrace or stall-cause proof'}
(DEVICE/'evidence/recovery-kernel-samples.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
