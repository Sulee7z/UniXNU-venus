#!/usr/bin/env python3
"""Check whether the exact normal-boot policy intentionally freezes its display."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
SOURCE=DEVICE/'package/boot-progress';OUT=ROOT/'artifacts/venus-userspace-001/stall-checks';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
candidate=json.loads((ROOT/'artifacts/venus-userspace-001/candidate.json').read_text())
phone=json.loads((DEVICE/'evidence/userspace-phone.json').read_text())
need_args=candidate['args'].split()
assert 'boot-progress=2' in need_args and not any(a.startswith('venus-data-check=') for a in need_args)
receipt=json.loads((ROOT/'artifacts/venus-data-check-002/linked-inputs/boot-progress-report.json').read_text())
assert sha(SOURCE/'BootProgress.c')==receipt['sources']['BootProgress.c']
progress=(SOURCE/'BootProgress.c').read_text()
assert 'state.continuous=opt==2;' in progress
test=OUT/'continuous-policy.c'
test.write_text('#include <assert.h>\n#include <stdio.h>\n#include "BootProgressCore.h"\n'
    'int main(void){struct bp_core s={.limit=120,.stall=30,.continuous=1};'
    'for(unsigned t=0;t<=300;t++){bp_poll(&s,t,0,0,0);assert(!s.frozen);}'
    'assert(s.reason==2);struct bp_core stopped={.limit=120,.stall=30};'
    'bp_poll(&stopped,87,0,0,0);assert(stopped.frozen);'
    'puts("PASS: actual continuous recorder stays unfrozen through87/120/300s; diagnostic-stop control freezes");}\n')
for name,cmd in [('build',['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function','-O1','-g',
                       '-fno-pie','-no-pie','-fsanitize=address,undefined','-I',SOURCE,test,'-o',OUT/'continuous-policy']),
                 ('run',[OUT/'continuous-policy'])]:
    result=subprocess.run([str(v) for v in cmd],capture_output=True,text=True,timeout=90)
    (OUT/(name+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(result.stdout+result.stderr)
kernel=ROOT/'artifacts/venus-userspace-001/kernel/kernel.macho'
nm=subprocess.check_output(['/usr/bin/llvm-nm',str(kernel)],text=True)
sys.path.insert(0,'/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root/tree/kits/XnuPrelink')
from native_prelink import macho,backed_offset
blob=kernel.read_bytes();image=macho(blob)
hooks={}
for name in ('_boot_process_snapshot','_boot_log_tick','_sheng_cpufreq_poll','_boot_ui_trace_snapshot'):
    matches=[line.split() for line in nm.splitlines() if line.split()[-1:]==[name]]
    assert len(matches)==1 and len(matches[0])==3
    address=int(matches[0][0],16);offset=backed_offset(image['segments'],address,8,len(blob))
    code=blob[offset:offset+8]
    assert code==bytes.fromhex('00008052c0035fd6'),'Optional monitor hook is no longer a return stub: '+name
    hooks[name]={'address':hex(address),'instructions':'mov w0,#0; ret','bytes':code.hex()}
report={'device':'venus','date':'2026-10-28','kernel_sha256':candidate['kernel_sha256'],
        'compiled_progress_source_sha256':sha(SOURCE/'BootProgress.c'),'core_sha256':sha(SOURCE/'BootProgressCore.h'),
        'phone_record_sha256':sha(DEVICE/'evidence/userspace-phone.json'),
        'explicit_data_stop_absent':True,'continuous_policy_does_not_freeze':True,
        'optional_monitor_hooks':hooks,
        'screen_stalled_user_confirmed':phone.get('screen_stalled_user_confirmed',False),
        'free_4k_pages_at_last_photo':phone['observed']['free_4k_pages'],
        'scope':'Host check excludes configured Data/deadline stops; screen alone cannot locate a kernel stall or prove OOM',
        'next_measurement':'A same-kernel larger-owned-memory control can test pressure sensitivity; not a proved memory fix'}
(DEVICE/'evidence/userspace-stall-host.json').write_text(json.dumps(report,indent=2)+'\n')
print(result.stdout,end='');print(json.dumps(hooks,indent=2))
