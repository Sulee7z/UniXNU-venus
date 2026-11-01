#!/usr/bin/env python3
"""Stage pinned iOS17 Metal with reviewed zeta fixes into isolated work copies."""
import hashlib
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path('/mnt/g/UniXNU-Port');BASE=ROOT/'sources/UniXNU-zeta-base'
REF=ROOT/'references/zeta-metal/eb489285a1d9153872f00c93ebb519a269b249b5'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--attempt',type=int,default=5);args=parser.parse_args()
if not 1<=args.attempt<=9:parser.error('Invalid attempt')
OUT=Path('/root/unixnu-build')/f'venus-metal-work-r{args.attempt}';OUT.mkdir(exist_ok=True)
def git(path):return subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
if git(BASE)!='35c384e84266343991fd14706e8c651f7d2e09ed' or git(BASE/'drivers/NativeMetal')!='ff0c70d7249a04ee381d9854c214069324a34d5c':raise ValueError('Base Metal pin changed')
receipt=json.loads((REF/'receipt.json').read_text())
for path,row in receipt['files'].items():
    if hashlib.sha256((REF/path).read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Reference source changed')
source=OUT/'AdrenoMetal';source.mkdir(exist_ok=False)
for path in (BASE/'drivers/NativeMetal').iterdir():
    if path.name=='.git':continue
    if path.is_dir():shutil.copytree(path,source/path.name)
    else:shutil.copy2(path,source/path.name)
# spi26 also supplies generic view-parent/resource fields used by later fixes.
# Apply the coherent series, then adapt/verify the final17 ABI rather than
# dropping one prerequisite and accepting partially applied sources.
excluded=set()
patches=[p for p in sorted((REF/'package').glob('NativeMetal-*.patch')) if p.name not in excluded]
logs=OUT/'patch-logs';logs.mkdir(exist_ok=True);applied=[]
for patch in patches:
    result=subprocess.run(['patch','-p1','--batch','--forward','--fuzz=0','-d',str(source),'-i',str(patch)],capture_output=True,text=True,timeout=60)
    (logs/(patch.name+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit('Patch failed '+patch.name+'\n'+result.stdout+result.stderr)
    applied.append({'path':patch.name,'sha256':hashlib.sha256(patch.read_bytes()).hexdigest()})
# The G: checkout and upstream patches leave mixed CRLF/LF in untouched plugin
# regions. Normalize only generated source before our LF-context board patch.
for path in source.rglob('*'):
    if path.is_file() and path.suffix in ('.mm','.h','.c','.cpp','.rs'):
        path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
patch=ROOT/'ports/UniXNU-venus/package/Metal13/venus-ios17-runtime.patch'
result=subprocess.run(['patch','-p1','--batch','--forward','--fuzz=0','-d',str(source),'-i',str(patch)],capture_output=True,text=True,timeout=60)
(logs/(patch.name+'.log')).write_text(result.stdout+result.stderr)
if result.returncode:raise SystemExit('Board patch failed\n'+result.stdout+result.stderr)
applied.append({'path':patch.name,'sha256':hashlib.sha256(patch.read_bytes()).hexdigest()})
translator=Path('/root/unixnu-build/venus-metal-tools/metal2vulkan')
if git(translator)!='720ef1ce9ae2a2068999a8675717418b9416283e':raise ValueError('Translator pin changed')
translator_work=OUT/'metal2vulkan';shutil.copytree(translator,translator_work,ignore=shutil.ignore_patterns('.git'))
bridge_patches=sorted((source/'bridge/patches').glob('*.patch'))
for patch in bridge_patches:
    result=subprocess.run(['patch','-p1','--batch','--forward','--fuzz=0','-d',str(translator_work),'-i',str(patch)],capture_output=True,text=True,timeout=60)
    (logs/('translator-'+patch.name+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit('Translator patch failed '+patch.name+'\n'+result.stdout+result.stderr)
record={'metal_base_revision':git(BASE/'drivers/NativeMetal'),'zeta_revision':receipt['revision'],
        'source':str(source),'translator_source':str(translator_work),'translator_revision':git(translator),
        'metal_patches':applied,'excluded_os26_selector_patch':sorted(excluded),
        'translator_patches':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in bridge_patches},
        'scope':'Isolated exact-source work copies; patched frontend must compile and iOS17 ABI/runtime tests must qualify it.'}
(OUT/'source-receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
