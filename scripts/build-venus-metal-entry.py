#!/usr/bin/env python3
"""Compile the zeta-aligned entry while retaining the checked Metal runtime frontend."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus'
OLD=Path('/root/unixnu-build/venus-metal-work-r5/frontend-build')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((OLD/'report.json').read_text())
frontend=next(row for row in old['objects'] if Path(row['source']).name=='NativeBridgeMetalFrontend.mm')
assert sha(Path(frontend['source']))==frontend['source_sha256']
assert sha(Path(frontend['object']))==frontend['object_sha256']
shutil.copy2(frontend['object'],out/'NativeBridgeMetalFrontend.o')
command=json.loads((OLD/'VenusMetalPlugin.command.json').read_text())
command[command.index('-o')+1]=str(out/'VenusMetalPlugin.o')
result=subprocess.run(command,capture_output=True,text=True,timeout=120)
(out/'compile.log').write_text(result.stdout+result.stderr)
if result.returncode:raise SystemExit(result.stdout+result.stderr)
inputs=[DEVICE/'package/Metal13/VenusMetalPlugin.mm',DEVICE/'package/Metal13/VenusMetalCache.h',
        DEVICE/'package/Metal13/VenusMetalDiagnostics.h']
record={'target':'arm64-apple-ios17.0','frontend':frontend,'objects':{
    'NativeBridgeMetalFrontend.o':sha(out/'NativeBridgeMetalFrontend.o'),'VenusMetalPlugin.o':sha(out/'VenusMetalPlugin.o')},
    'inputs':{str(p):sha(p) for p in inputs},'command':command,
    'phone_operations':False,'hardware_rendering_verified':False}
(out/'report.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS: zeta-aligned iOS17 plugin entry compiled; existing frontend object verified and retained')
