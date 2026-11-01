#!/usr/bin/env python3
"""Build real pinned Mesa Turnip/native Darwin backend for Venus/iOS17."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path('/mnt/g/UniXNU-Port');BASE=ROOT/'sources/UniXNU-zeta-base';WORK=Path('/root/unixnu-build/venus-metal-work-r5')
TOOLS=Path('/root/unixnu-build/venus-metal-tools');SDK=TOOLS/'sdks/iPhoneOS16.5.sdk';SOURCE=WORK/'mesa-source';OUT=WORK/'mesa-ios-r2';OUT.mkdir(exist_ok=True)
pins=json.loads((BASE/'scripts/data/adreno-compiler-inputs.json').read_text());pin=pins['mesa']['commit']
if not SOURCE.exists():subprocess.run(['git','-C',str(TOOLS/'mesa'),'worktree','add','--detach',str(SOURCE),pin],check=True)
actual=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()
if actual!=pin:raise ValueError('Wrong Mesa source')
receipt=WORK/'mesa-source-receipt.json'
if not receipt.exists():
    patches={}
    for name in pins['patches']:
        patch=BASE/name;result=subprocess.run(['patch','-p1','--batch','--forward','--fuzz=0','-d',str(SOURCE),'-i',str(patch)],capture_output=True,text=True,timeout=60)
        (OUT/(patch.name+'.log')).write_text(result.stdout+result.stderr)
        if result.returncode:raise SystemExit('Mesa patch failed '+name+'\n'+result.stdout+result.stderr)
        patches[name]=hashlib.sha256(patch.read_bytes()).hexdigest()
    receipt.write_text(json.dumps({'revision':pin,'patches':patches},indent=2)+'\n')
compiler='/usr/bin/clang-18';cpp='/usr/bin/clang++-18';lld=str(TOOLS/'llvm21/usr/lib/llvm-21/bin/ld64.lld')
flags=['-target','arm64-apple-ios17.0','-isysroot',str(SDK),'-fstack-protector-strong']
link=flags+['-fuse-ld='+lld,'-mlinker-version=953']
cross=WORK/'mesa-ios.cross'
cross.write_text('[binaries]\nc = '+repr(compiler)+'\ncpp = '+repr(cpp)+'\nobjc = '+repr(compiler)+"\nar = '/usr/bin/llvm-ar'\nstrip = '/usr/bin/llvm-strip'\npkg-config = '/usr/bin/false'\n"+
    "[host_machine]\nsystem = 'darwin'\ncpu_family = 'aarch64'\ncpu = 'arm64'\nendian = 'little'\n[properties]\nneeds_exe_wrapper = true\n[built-in options]\n"+
    ''.join(k+' = '+repr(v)+'\n' for k,v in {'c_args':flags,'cpp_args':flags+['-isystem',str(SDK/'usr/include/c++/v1')],
        'objc_args':flags,'c_link_args':link,'cpp_link_args':link,'objc_link_args':link}.items()))
options=['-Dgallium-drivers=','-Dvulkan-drivers=freedreno','-Dfreedreno-kmds=darwin','-Dtu-darwin-abi-dir='+str(BASE/'drivers/NativeAdreno'),
    '-Dplatforms=macos','-Dglx=disabled','-Degl=disabled','-Dgbm=disabled','-Dopengl=false','-Dgles1=disabled','-Dgles2=disabled','-Dllvm=disabled',
    '-Dshared-glapi=disabled','-Dxmlconfig=disabled','-Dshader-cache=disabled','-Dtools=','-Dbuild-tests=false','-Dvideo-codecs=','-Dvulkan-layers=',
    '-Dlibunwind=disabled','-Dlmsensors=disabled','-Dvalgrind=disabled','-Dexpat=disabled','-Dzstd=disabled','-Dbuildtype=release','-Db_ndebug=true']
env={**os.environ,'PATH':str(TOOLS/'mesa-venv/bin')+':'+os.environ['PATH'],'LD_LIBRARY_PATH':str(TOOLS/'llvm21/usr/lib/x86_64-linux-gnu')}
meson=str(TOOLS/'mesa-venv/bin/meson');command=[meson,'setup',str(OUT),str(SOURCE),'--wrap-mode=nodownload','--cross-file',str(cross),*options]
if (OUT/'build.ninja').exists():command=[meson,'configure',str(OUT),*options]
with (OUT/'configure.log').open('w') as log:result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
if result.returncode:print('FAILED; read',OUT/'configure.log');raise SystemExit(result.returncode)
with (OUT/'build.log').open('w') as log:result=subprocess.run(['ninja','-C',str(OUT),'-j6'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
if result.returncode:print('FAILED; read',OUT/'build.log');raise SystemExit(result.returncode)
library=OUT/'src/freedreno/vulkan/libvulkan_freedreno.dylib'
record={'library':str(library),'sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'bytes':library.stat().st_size,
        'mesa_revision':pin,'source_receipt':str(receipt),'target':'arm64-apple-ios17.0','scope':'Actual Turnip/native Darwin library build; A660 pixel test remains hardware work.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
