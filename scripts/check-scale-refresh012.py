#!/usr/bin/env python3
"""Sanitizer-check protected012 backup/journal/cache transaction and legacy defaults."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--attempt',type=int,default=3);args=parser.parse_args()
if not 1<=args.attempt<=9:parser.error('Invalid attempt')
OUT=ROOT/'artifacts/venus-scale-refresh-012'/f'host-tests-r{args.attempt}';OUT.mkdir(parents=True,exist_ok=False)
headers=DEVICE/'package/boot-progress';results=[]
for name,extra in (('legacy',[]),('protected012',['-DSCALE_REFRESH_TEST_012'])):
    source=DEVICE/'tests'/('gestalt_cache.c' if name=='legacy' else 'scale_refresh011.c');binary=OUT/name
    command=['gcc','-D_DEFAULT_SOURCE','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
        '-fno-pie','-no-pie','-fsanitize=address,undefined','-I',str(headers),'-I',str(DEVICE/'tests/host-kernel-sys'),
        '-DRENAME_EXCL=4','-DRENAME_NOFOLLOW_ANY=128',*extra,str(source),'-o',str(binary)]
    result=subprocess.run(command,capture_output=True,text=True,timeout=90);(OUT/(name+'-compile.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(result.stdout+result.stderr)
    result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30)
    (OUT/(name+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(result.stdout+result.stderr)
    results.append({'name':name,'passed':True})
report={'passed':True,'sources':{n:hashlib.sha256((headers/n).read_bytes()).hexdigest() for n in ('BootGestaltCache.h','BootScaleRefresh012.h')},
    'cases':results,'scope':'Actual C cache/protected journal under persistent VFS model and ASan/UBSan; extra sync failure separated without masking canonical cache/medium errors.'}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS: actual012 protected cache/journal and legacy defaults')
