#!/usr/bin/env python3
"""Relink same Turnip objects: correct iOS IOKit install-name and ad-hoc4K sign."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
ROOT=Path('/mnt/g/UniXNU-Port');TOOLS=Path('/root/unixnu-build/venus-metal-tools');BUILD=Path('/root/unixnu-build/venus-metal-work-r5/mesa-ios-r2')
OUT=ROOT/'artifacts/venus-metal13/turnip-signed';OUT.mkdir(exist_ok=False)
SDK=TOOLS/'sdks/iPhoneOS16.5.sdk';framework=OUT/'framework-stubs/IOKit.framework';framework.mkdir(parents=True)
stub=SDK/'System/Library/Frameworks/IOKit.framework/IOKit.tbd'
text=stub.read_text();old='/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit'
if old not in text:raise ValueError('Unexpected IOKit stub identity')
newtext=text.replace(old,'/System/Library/Frameworks/IOKit.framework/IOKit');(framework/'IOKit.tbd').write_text(newtext)
target='src/freedreno/vulkan/libvulkan_freedreno.dylib'
commands=subprocess.check_output(['ninja','-C',str(BUILD),'-t','commands',target],text=True).splitlines()
selected=[shlex.split(line) for line in commands if '-o '+target+' ' in line and ' -shared ' in line]
if len(selected)!=1:raise ValueError('Ambiguous Turnip link command')
command=selected[0];at=command.index('-o');command[at+1]=str(OUT/'libvulkan_freedreno.dylib')
command[1:1]=['-F'+str(OUT/'framework-stubs'),'-Wl,-adhoc_codesign,-S,-x']
env={**os.environ,'LD_LIBRARY_PATH':str(TOOLS/'llvm21/usr/lib/x86_64-linux-gnu')}
result=subprocess.run(command,cwd=BUILD,env=env,capture_output=True,text=True,timeout=300);(OUT/'link.log').write_text(result.stdout+result.stderr)
if result.returncode:raise SystemExit(result.stdout+result.stderr)
library=OUT/'libvulkan_freedreno.dylib'
record={'source_dylib_sha256':hashlib.sha256((BUILD/target).read_bytes()).hexdigest(),'signed_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),
        'bytes':library.stat().st_size,'original_sdk_stub_sha256':hashlib.sha256(stub.read_bytes()).hexdigest(),'iOS_import_stub_sha256':hashlib.sha256(newtext.encode()).hexdigest(),
        'command':command,'scope':'Same source/objects relinked with correct flat iOS IOKit import and own4K signature. Signature pages/ABI independently checked by addon packager.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k!='command'},indent=2))
