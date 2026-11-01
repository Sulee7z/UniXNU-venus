#!/usr/bin/env python3
"""Compile the actual patched Objective-C Metal frontend with iOS17 deployment."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path('/mnt/g/UniXNU-Port');WORK=Path('/root/unixnu-build/venus-metal-work-r5')
SDK=Path('/root/unixnu-build/venus-metal-tools/sdks/iPhoneOS16.5.sdk');OUT=WORK/'frontend-build';OUT.mkdir(exist_ok=True)
base=['/root/unixnu-toolchain/llvm/bin/clang++','-target','arm64-apple-ios17.0','-isysroot',str(SDK),
      '-isystem',str(SDK/'usr/include/c++/v1'),'-std=c++17','-fobjc-arc','-O2','-Wall','-Wextra','-Werror',
      '-Wno-deprecated-declarations','-fstack-protector-strong','-I',str(WORK/'AdrenoMetal')]
sources=[WORK/'AdrenoMetal/NativeBridgeMetalFrontend.mm',ROOT/'ports/UniXNU-venus/package/Metal13/VenusMetalPlugin.mm']
records=[]
for source in sources:
    target=OUT/(source.stem+'.o');command=[*base,'-c',str(source),'-o',str(target)]
    result=subprocess.run(command,capture_output=True,text=True,timeout=300)
    (OUT/(source.stem+'.log')).write_text(result.stdout+result.stderr)
    (OUT/(source.stem+'.command.json')).write_text(json.dumps(command,indent=2)+'\n')
    if result.returncode:print('FAILED; read',OUT/(source.stem+'.log'));raise SystemExit(result.returncode)
    records.append({'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                    'object':str(target),'object_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size})
record={'objects':records,'target':'arm64-apple-ios17.0','scope':'Actual Objective-C frontend compile; link/Turnip and runtime checks follow.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
