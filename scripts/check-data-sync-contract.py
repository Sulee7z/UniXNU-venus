#!/usr/bin/env python3
"""Exercise durable file transaction gates and preserve the exact tested source."""
import hashlib
import json
from pathlib import Path
import subprocess
DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
OUT=ROOT/'artifacts/venus-data-sync-checks';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,name):
    r=subprocess.run([str(x) for x in cmd],capture_output=True,text=True,timeout=120)
    (OUT/(name+'.log')).write_text(r.stdout+r.stderr)
    if r.returncode:raise SystemExit(name+': '+r.stdout+r.stderr)
    return r.stdout
run(['gcc','-std=c11','-D_POSIX_C_SOURCE=200809L','-O1','-g','-Wall','-Wextra','-Werror',
     '-Wno-misleading-indentation','-fno-pie','-no-pie','-fsanitize=address,undefined',
     DEVICE/'tests/data_check_core.c','-o',OUT/'data-core'],'build')
result=run([OUT/'data-core'],'test')
adapter=(DEVICE/'package/boot-progress/BootDataCheck.h').read_text()
assert 'struct openat_args' in adapter and 'c->parent_fd' in adapter
assert '.cmd=F_FULLFSYNC' in adapter and 'native_ufs_store_sync()?0:EIO' in adapter
assert 'phase==1 && native_data_persist_writes<=context.before_writes' in adapter
report={'device':'venus','date':'2026-10-28','sync_contract':2,'passed':True,'output':result.strip(),
        'sources':{name:sha(DEVICE/'package/boot-progress'/name) for name in ('BootDataCheckCore.h','BootDataCheck.h')},
        'test_sha256':sha(DEVICE/'tests/data_check_core.c'),'phone_verified':False,
        'scope':'Real transaction core over separately modeled namespace/checkpoint/media boundaries; actual APFS adapter requires kernel compile and phone test'}
(DEVICE/'evidence/data-sync-contract-host.json').write_text(json.dumps(report,indent=2)+'\n')
print(result,end='')
