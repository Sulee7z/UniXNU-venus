#!/usr/bin/env python3
"""Sanitizer-check actual cache invalidation and persistent-stage journal code."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--attempt',type=int,default=3);args=parser.parse_args()
if not 1<=args.attempt<=9:parser.error('Invalid attempt')
OUT=ROOT/'artifacts/venus-scale-refresh-011'/f'host-tests-r{args.attempt}';OUT.mkdir(parents=True,exist_ok=False)
headers=DEVICE/'package/boot-progress';records=[]
for name in ('gestalt_cache','scale_refresh011'):
    source=DEVICE/'tests'/(name+'.c');binary=OUT/name
    command=['gcc','-D_DEFAULT_SOURCE','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
             '-fno-pie','-no-pie','-fsanitize=address,undefined','-I',str(headers),
             '-I',str(DEVICE/'tests/host-kernel-sys'),str(source),'-o',str(binary)]
    if name=='gestalt_cache':command+=['-DRENAME_EXCL=4','-DRENAME_NOFOLLOW_ANY=128']
    result=subprocess.run(command,capture_output=True,text=True,timeout=90)
    (OUT/(name+'-compile.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(result.stdout+result.stderr)
    result=subprocess.run([str(binary)],capture_output=True,text=True,check=True,timeout=30)
    (OUT/(name+'.log')).write_text(result.stdout+result.stderr);records.append({'case':name,'passed':True})
record={'passed':True,'sources':{name:hashlib.sha256((headers/name).read_bytes()).hexdigest()
                                for name in ('BootGestaltCache.h','BootScaleRefresh011.h')},
        'cases':records,'scope':'Actual C transaction/journal with persistent namespace/VFS model under ASan/UBSan; not an APFS or phone execution.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS:011 actual cache invalidation and durable journal failure controls')
