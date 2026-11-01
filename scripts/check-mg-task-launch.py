#!/usr/bin/env python3
"""Test the production task wrapper with real host fork/exec/identity and timeout."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
OUT=ROOT/'artifacts/venus-mg-query-009/task-host-tests-r2';OUT.mkdir(exist_ok=False)
if os.geteuid()!=0:raise SystemExit('Real501 identity test runs as root in the G-backed build distro')
probe=OUT/'query-fixture'
subprocess.run(['gcc','-D_GNU_SOURCE','-Wall','-Wextra','-Werror',str(DEVICE/'tests/mg_task_query.c'),'-o',str(probe)],check=True)
cases=[]
for name in ('success','missing-query','timeout','existing-output','closed-stdio'):
    case=OUT/name;case.mkdir();os.chmod(case,0o777)
    query=str(case/'missing') if name=='missing-query' else str(probe)
    macros={'MG_TASK_ORIGINAL':'/usr/bin/true','MG_TASK_QUERY':query,'MG_TASK_LOG':str(case/'launch.jsonl'),
            'MG_TASK_STDOUT':str(case/'answer.json'),'MG_TASK_STDERR':str(case/'answer.stderr')}
    command=['gcc','-D_GNU_SOURCE','-DMG_TASK_HOST_TEST','-DMG_TASK_DELAY=0','-DMG_TASK_TIMEOUT=3',
             '-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined',
             '-fno-pie','-no-pie',*[f'-D{k}="{v}"' for k,v in macros.items()],
             str(DEVICE/'package/MGTaskLaunch.c'),'-o',str(case/'wrapper')]
    subprocess.run(command,check=True,timeout=60)
    if name=='existing-output':(case/'answer.json').write_text('preserve-me')
    env={**os.environ,'MG_TEST_MODE':name,'MG_TEST_CONTEXT':'inherited-from-launchd-model'}
    def close_stdio():
        for fd in (0,1,2):
            try:os.close(fd)
            except OSError:pass
    start=time.monotonic();result=subprocess.run([str(case/'wrapper')],env=env,capture_output=True,text=True,timeout=5,
                                               preexec_fn=close_stdio if name=='closed-stdio' else None)
    assert result.returncode==0,(name,result.stderr)
    assert time.monotonic()-start<2,'Original task must run without waiting for query'
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        text=(case/'launch.jsonl').read_text() if (case/'launch.jsonl').exists() else ''
        if 'supervisor_finished' in text:break
        time.sleep(.1)
    else:raise AssertionError((name,'Supervisor did not finish',text,result.stderr))
    events=[json.loads(line) for line in text.splitlines()]
    if name in ('success','closed-stdio'):
        answer=json.loads((case/'answer.json').read_text())
        assert answer=={'uid':501,'gid':501,'environment':'inherited-from-launchd-model','complete':True},answer
    if name=='missing-query':assert any(e['event']=='query_exec_failed' and e['value']==2 for e in events)
    if name=='timeout':assert any(e['event']=='query_timeout' for e in events)
    if name=='existing-output':assert (case/'answer.json').read_text()=='preserve-me'
    before=(case/'launch.jsonl').read_bytes()
    subprocess.run([str(case/'wrapper')],env=env,check=True,timeout=5)
    time.sleep(.1);assert (case/'launch.jsonl').read_bytes()==before,'One-shot marker must prevent repeat'
    cases.append({'case':name,'events':events,'original_task_exit':result.returncode})
mount=OUT/'mount-check'
subprocess.run(['gcc','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                '-fno-pie','-no-pie','-I',str(DEVICE/'package'),str(DEVICE/'tests/mg_task_mount.c'),'-o',str(mount)],check=True)
result=subprocess.run([str(mount)],capture_output=True,text=True,check=True,timeout=15)
(OUT/'mount.log').write_text(result.stdout+result.stderr)
record={'passed':True,'source_sha256':hashlib.sha256((DEVICE/'package/MGTaskLaunch.c').read_bytes()).hexdigest(),
        'mount_source_sha256':hashlib.sha256((DEVICE/'package/MGTaskMount.h').read_bytes()).hexdigest(),
        'cases':cases,'scope':'Actual wrapper with host POSIX fork/exec/UID501 under sanitizers and actual mount helper with modeled VFS. Not device MG answers.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS: wrapper immediate original exec, mobile identity, inherited context, timeout, errno, existing-file preservation and mount contract')
