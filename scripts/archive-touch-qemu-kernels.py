#!/usr/bin/env python3
"""Losslessly archive finished QEMU-only input kernels; phone kernels stay live."""
import gzip
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'artifacts';records=[]
receipt=ART/'venus-st-touch/archived-qemu-kernels.json'
if receipt.exists():raise SystemExit('Archive receipt already exists')
for attempt in (6,7,8,9,10):
    directory=ART/'venus-metal-touch'/('kernel-link-'+str(attempt))
    report=json.loads((directory/'report.json').read_text());assert report['qemu_only']
    for name in ('native.macho','kernel.macho'):
        source=directory/name;archive=directory/(name+'.gz');assert source.is_file() and not archive.exists()
        data=source.read_bytes();packed=gzip.compress(data,compresslevel=6,mtime=0);archive.write_bytes(packed)
        assert gzip.decompress(archive.read_bytes())==data
        records.append({'source':str(source),'archive':str(archive),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'compressed_bytes':len(packed)})
        source.unlink()
receipt.write_text(json.dumps({'files':records,'freed_bytes':sum(r['bytes']-r['compressed_bytes'] for r in records),
    'restore':'gzip.decompress(archive.read_bytes()) reproduces each original input exactly; verify recorded SHA before reuse. All five inputs are QEMU-only, never phone candidates.'},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'files':len(records),'freed_bytes':sum(r['bytes']-r['compressed_bytes'] for r in records),'receipt':str(receipt)},indent=2))
