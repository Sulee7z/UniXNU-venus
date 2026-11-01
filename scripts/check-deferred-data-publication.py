#!/usr/bin/env python3
"""Test real persistent Data publication code after the SystemOS stage boundary."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
RAM=ROOT/'sources/UniXNU-guide/drivers/RamBlock'
OUT=ROOT/'artifacts/venus-data-deferred-publication';OUT.mkdir(exist_ok=True)
patches=[DEVICE/'patches/ram-block'/name for name in ('publish-restored-view.patch','publish-at-data-mount.patch')]
source=OUT/'source';source.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,name):
    result=subprocess.run([str(v) for v in cmd],capture_output=True,text=True,timeout=180)
    (OUT/(name+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(name+': '+result.stdout+result.stderr)
    return result.stdout
for name in ('NativeRamBlock.cpp','DirectDisk.h','PersistOverlay.h','SparseDisk.h','SeedDisk.h'):shutil.copy2(RAM/name,source/name)
for i,patch in enumerate(patches):
    run(['git','-C',source,'apply','--check',patch],f'patch{i}-check')
    run(['git','-C',source,'apply',patch],f'patch{i}-apply')
text=(source/'NativeRamBlock.cpp').read_text()
start=text.split('  native_ram_block_resident_bytes=isBig?big.resident:sparse.pages?sparse.resident:logical;\n',1)[1].split('\n}\n',1)[0]
publish=text.split('  bool publishForData() {\n',1)[1].split('\n  }\n',1)[0]
(OUT/'deferred-start.inc').write_text(start+'\n')
(OUT/'deferred-publish.inc').write_text(publish+'\n')
assert 'if (publishedNow && !deferredData->publishForData()) return 0;' in text
assert 'IOService::waitForMatchingService(matching, 30000000000ULL)' in text
assert 'ram->attachStore();' not in text
run(['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-Wno-address','-Wno-unused-function',
     '-Wno-misleading-indentation','-fno-pie','-no-pie','-fsanitize=address,undefined','-I',source,'-I',OUT,
     DEVICE/'tests/data_deferred_publication.cpp','-o',OUT/'deferred-test'],'build')
result=run([OUT/'deferred-test'],'test')
report={'device':'venus','date':'2026-10-28','source_sha256':sha(RAM/'NativeRamBlock.cpp'),
        'patches':{p.name:sha(p) for p in patches},'patched_source_sha256':sha(source/'NativeRamBlock.cpp'),
        'test_sha256':sha(DEVICE/'tests/data_deferred_publication.cpp'),'result':result.strip(),
        'scope':'Actual start/publication code with real Overlay/DirectDisk and modeled consumers/stage gate; not a physical APFS/UFS reproduction',
        'phone_tested':False}
(DEVICE/'evidence/data-deferred-publication-host.json').write_text(json.dumps(report,indent=2)+'\n')
print(result,end='')
