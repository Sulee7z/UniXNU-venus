#!/usr/bin/env python3
"""Reclaim only verified duplicate payload files from this touch QEMU work."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'artifacts';records=[]
receipt=ART/'venus-st-touch/reclaimed-qemu-copies.json'
if receipt.exists():records=json.loads(receipt.read_text(encoding='utf-8'))['files']
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
runs=[(ART/'venus-st-touch'/name,ART/'venus-metal-touch'/kernel/'kernel.macho') for name,kernel in (
    ('qemu-hid-before','kernel-link-6'),('qemu-hid-before-r2','kernel-link-7'),('qemu-hid-fixed','kernel-link-8'),('qemu-hid-fixed-r2','kernel-link-9'),
    ('qemu-hid-matching','kernel-link-10'),('qemu-startup-report','kernel-link-11'))]
runs += [(ART/'venus-ufs-root'/name,ART/'venus-metal-touch'/kernel/'kernel.macho') for name,kernel in (
    ('qemu-metal-touch-default-off','kernel-link-2'),('qemu-metal-touch-mode3','kernel-link-2'),
    ('qemu-metal-touch-default-off-r2','kernel-link-4'),('qemu-metal-touch-mode1','kernel-link-4'),
    ('qemu-metal-touch-default-off-r3','kernel-link-5'),('qemu-metal-touch-mode1-r2','kernel-link-5'),('qemu-metal-touch-mode1-r4','kernel-link-5'))]
for run,kernel in runs:
    payload=run/'esp/EFI/UniXNU/Payloads'
    for name,source in (('kernel.macho',kernel),('scratch-data.img',ART/'venus-deployment/Data.dbr')):
        target=payload/name
        if not target.is_file() or not source.is_file():continue
        digest=sha(target)
        if digest!=sha(source):continue
        record={'duplicate':str(target),'retained_source':str(source),'sha256':digest,'bytes':target.stat().st_size}
        target.unlink();records.append(record)
receipt.write_text(json.dumps({'files':records,'freed_bytes':sum(r['bytes'] for r in records),'scope':'Only byte-identical QEMU payload copies; logs/register state and authoritative kernels/seed retained'},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'receipt':str(receipt),'files':len(records),'freed_bytes':sum(r['bytes'] for r in records)},indent=2))
