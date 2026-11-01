#!/usr/bin/env python3
"""Host-only reproduction of a seed/overlay view change during disk discovery."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

DEVICE=Path(__file__).resolve().parents[1]
ROOT=DEVICE.parents[1]
RAM=ROOT/'sources/UniXNU-guide/drivers/RamBlock'
OUT=ROOT/'artifacts/venus-data-publication'
PATCH=DEVICE/'patches/ram-block/publish-restored-view.patch'
OUT.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,name):
    result=subprocess.run([str(v) for v in cmd],capture_output=True,text=True,timeout=180)
    (OUT/(name+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(name+' failed: '+result.stdout+result.stderr)
    return result.stdout
source=OUT/'source';source.mkdir(exist_ok=True)
for name in ('NativeRamBlock.cpp','DirectDisk.h','PersistOverlay.h','SparseDisk.h','SeedDisk.h'):
    shutil.copy2(RAM/name,source/name)
before=(source/'NativeRamBlock.cpp').read_text()
run(['git','-C',source,'apply','--check',PATCH],'patch-check')
run(['git','-C',source,'apply',PATCH],'patch-apply')
after=(source/'NativeRamBlock.cpp').read_text()
# Execute the exact publication tails, not a separately handwritten order check.
for label,text in (('before',before),('after',after)):
    tail=text.split('  native_ram_block_resident_bytes=isBig?big.resident:sparse.pages?sparse.resident:logical;\n',1)[1].split('\n}\n',1)[0]
    if tail.count('registerService();')!=1:raise SystemExit('Publication extraction changed')
    (OUT/('publication-'+label+'.inc')).write_text(tail+'\n')
if 'ram->attachStore();' in after:raise SystemExit('UUID selection still changes an already published disk')
run(['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-Wno-address','-Wno-unused-function',
     '-fno-pie','-no-pie','-fsanitize=address,undefined','-I',source,'-I',OUT,
     DEVICE/'tests/data_publication.cpp','-o',OUT/'publication-test'],'build')
result=run([OUT/'publication-test'],'test')
report={'device':'venus','date':'2026-10-28','source_sha256':sha(RAM/'NativeRamBlock.cpp'),
        'patch_sha256':sha(PATCH),'patched_source_sha256':sha(source/'NativeRamBlock.cpp'),
        'test_sha256':sha(DEVICE/'tests/data_publication.cpp'),'result':result.strip(),
        'late_uuid_attachment_removed':True,'phone_tested':False,
        'scope':'Actual publication tails with real persistent block core and modeled caching consumer; not an APFS or phone reproduction',
        'remaining':['Compile and link the changed provider with original storage ABI',
                     'Verify first APFS read and cross-reboot marker on phone after user returns']}
(DEVICE/'evidence/data-publication-host.json').write_text(json.dumps(report,indent=2)+'\n')
print(result,end='')
