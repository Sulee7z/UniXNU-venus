#!/usr/bin/env python3
"""Check the compiled UFS store callbacks and production commands on modeled media."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
OUT=ROOT/'artifacts/venus-ufs-data-command-contract';OUT.mkdir(exist_ok=True)
receipt=json.loads((ROOT/'artifacts/venus-ufs-root-unixnu/venus-build.json').read_text())
command=json.loads((ROOT/'artifacts/venus-ufs-root-unixnu/compile-command.json').read_text())
actual=Path(command[command.index('-xc++')+1]);source=actual.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(actual)==receipt['native_ufs_source_sha256']
copy=OUT/'source';copy.mkdir(exist_ok=True)
files=['RootCommands.h','RootQueue.h','RootDiagnostics.h','RootTransportLayout.h','TransferPoll.h','tests/RootCommandsBridge.cpp']
for name in files:
    target=copy/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,target)
# Include the exact native_ufs_store read/write/sync bodies used to build Venus.
text=actual.read_text();callbacks=[]
for name in ('native_ufs_store_read','native_ufs_store_write','native_ufs_store_sync'):
    start=text.index('extern "C" int '+name+' ')
    end=text.index('\n}\n',start)+3
    callbacks.append(text[start:end])
(OUT/'store-callbacks.inc').write_text('\n'.join(callbacks)+'\n')
def run(argv,name):
    result=subprocess.run([str(v) for v in argv],capture_output=True,text=True,timeout=180)
    (OUT/(name+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(name+': '+result.stdout+result.stderr)
    return result.stdout
run(['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function',
     '-fno-pie','-no-pie','-fsanitize=address,undefined','-I',copy,'-I',OUT,
     '-I',ROOT/'sources/UniXNU-guide/drivers/RamBlock',DEVICE/'tests/ufs_data_command_contract.cpp',
     '-o',OUT/'command-test'],'build')
result=run([OUT/'command-test'],'test')
report={'device':'venus','date':'2026-10-28','ufs_revision':receipt['ufs_revision'],
        'compiled_native_ufs_source_sha256':sha(actual),'source_inputs':{name:sha(source/name) for name in files},
        'compiled_store_callback_bodies_sha256':sha(OUT/'store-callbacks.inc'),
        'test_sha256':sha(DEVICE/'tests/ufs_data_command_contract.cpp'),'passed':True,'result':result.strip(),
        'scope':'Real compiled-source store callbacks and command/overlay cores, modeled DMA/UFS medium and power loss; not real UFS durability or APFS',
        'physical_data_write_reboot_verified':False,'phone_operation_performed':False}
(DEVICE/'evidence/ufs-data-command-contract.json').write_text(json.dumps(report,indent=2)+'\n')
print(result,end='')
