#!/usr/bin/env python3
"""Losslessly archive completed QEMU variable disks after verified gzip roundtrip."""
import gzip
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'artifacts';records=[]
runs=[ART/'venus-st-touch'/n for n in ('qemu-hid-before','qemu-hid-before-r2','qemu-hid-fixed','qemu-hid-fixed-r2','qemu-hid-matching','qemu-startup-report')]
runs += [ART/'venus-ufs-root'/n for n in ('qemu-metal-touch-default-off','qemu-metal-touch-mode3','qemu-metal-touch-default-off-r2','qemu-metal-touch-mode1',
    'qemu-metal-touch-default-off-r3','qemu-metal-touch-mode1-r2','qemu-metal-touch-mode1-r4','qemu-touch017-default-off')]
for run in runs:
    path=run/'vars.fd';out=run/'vars.fd.gz'
    if not path.exists():continue
    if not (run/'gdb-stop.json').exists() or out.exists():raise ValueError('Require completed run and new archive')
    data=path.read_bytes();assert len(data)==67108864
    compressed=gzip.compress(data,compresslevel=6,mtime=0);out.write_bytes(compressed)
    restored=gzip.decompress(out.read_bytes());assert restored==data
    records.append({'source':str(path),'archive':str(out),'bytes':len(data),'compressed_bytes':len(compressed),'sha256':hashlib.sha256(data).hexdigest(),'compressed_sha256':hashlib.sha256(compressed).hexdigest()})
    path.unlink()
receipt=ART/'venus-st-touch/archived-qemu-vars.json';assert not receipt.exists()
receipt.write_text(json.dumps({'files':records,'freed_bytes':sum(r['bytes']-r['compressed_bytes'] for r in records)},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'files':len(records),'freed_bytes':sum(r['bytes']-r['compressed_bytes'] for r in records),'receipt':str(receipt)},indent=2))
