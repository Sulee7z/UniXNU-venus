#!/usr/bin/env python3
"""Run the production cache helper with explicit namespace/IO stand-ins."""
import hashlib
import json
from pathlib import Path
import subprocess

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
OUT=ROOT/'artifacts/venus-mode-scale-analysis/cache-tests'
OUT.mkdir(exist_ok=True);(OUT/'sys').mkdir(exist_ok=True)
# Same constants as the selected XNU bsd/sys/stdio.h; no Linux rename is used.
(OUT/'sys/stdio.h').write_text('#define RENAME_EXCL 4\n#define RENAME_NOFOLLOW_ANY 16\n')
source=DEVICE/'tests/gestalt_cache.c';header=DEVICE/'package/boot-progress/BootGestaltCache.h'
subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
    '-O1','-g','-fno-pie','-no-pie','-fsanitize=address,undefined','-I',str(OUT),
    '-I',str(header.parent),str(source),'-o',str(OUT/'check')],check=True,timeout=60)
result=subprocess.run([str(OUT/'check')],capture_output=True,text=True,timeout=30)
(OUT/'run.txt').write_text(result.stdout+result.stderr)
result.check_returncode()
report={'passed':True,'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),
        'test_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output':result.stdout,
        'scope':'Actual C helper under ASan/UBSan with explicit kernel-API and filesystem model; not phone/APFS evidence'}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(result.stdout)
