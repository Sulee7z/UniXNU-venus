#!/usr/bin/env python3
"""Retain bounded ST protocol references at the same pinned Venus kernel commit."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
OUT=ROOT/'artifacts/venus-touch-source-reference'
pin=json.loads((ROOT/'sources/venus-kernel-reference/SOURCE.json').read_text())
base='https://raw.githubusercontent.com/'+pin['repository']+'/'+pin['commit']+'/'
files=['drivers/input/touchscreen/'+family+'/'+name for family in ('st','fts_spi')
       for name in ('Makefile','fts.h','fts.c','fts_lib/ftsHardware.h','fts_lib/ftsIO.c')]
OUT.mkdir(exist_ok=True)
def fetch(name):
    url=base+name
    request=urllib.request.Request(url,headers={'User-Agent':'UniXNU-venus-host-reference'})
    with urllib.request.urlopen(request,timeout=60) as response:
        data=response.read(2*1024*1024+1)
    if len(data)>2*1024*1024:raise RuntimeError('Reference unexpectedly large: '+name)
    target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and target.read_bytes()!=data:raise RuntimeError('Pinned reference changed: '+name)
    target.write_bytes(data)
    return name,{'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    records=dict(pool.map(fetch,files))
report={'device':'venus','date':'2026-10-28','repository':pin['repository'],'commit':pin['commit'],
        'files':records,'scope':'Pinned Linux ST references for protocol/board comparison; not compiled or selected as an XNU hardware driver',
        'phone_operation_performed':False}
(OUT/'sources.json').write_text(json.dumps(report,indent=2)+'\n')
print('Retained',len(records),'ST reference files at',pin['commit'])
