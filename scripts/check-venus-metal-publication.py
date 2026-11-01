#!/usr/bin/env python3
"""Execute real publication code with failing IOKit calls and synchronous discovery."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

DEVICE=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
out=args.output
out.mkdir(parents=True,exist_ok=False)
includes=out/'include'
for name in ('IOKit/IOService.h','IOKit/IOLib.h','IOKit/IOPlatformExpert.h',
             'libkern/c++/OSMetaClass.h','libkern/c++/OSSymbol.h','mach/kmod.h'):
    path=includes/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('#include "metal_publication_shim.h"\n')
binary=out/'publication-test'
command=['g++','-std=c++17','-Wall','-Wextra','-Werror','-g',
         '-fsanitize=address,undefined','-fno-omit-frame-pointer',
         '-I'+str(includes),'-I'+str(DEVICE/'tests'),
         str(DEVICE/'tests/metal_publication.cpp'),'-o',str(binary)]
subprocess.run(command,check=True)
result=subprocess.run([str(binary)],capture_output=True,text=True)
(out/'test.log').write_text(result.stdout+result.stderr)
if result.returncode:raise SystemExit(result.stderr)
sources=[DEVICE/'package/Adreno660/VenusMetalPublication.cpp',DEVICE/'tests/metal_publication.cpp',DEVICE/'tests/metal_publication_shim.h']
report={'passed':True,'cases':['disabled','missing transport','parent load failure','missing/wrong parent',
    'metaclass begin/end failure','wrong object size','allocation/init failure','each property failure',
    'attach failure','synchronous discovery ordering','single registration','completed/deferred/timeout startup'],
    'sanitizers':['address','undefined'],'command':command,
    'sources':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    'hardware_rendering_verified':False,'qemu_verified':False,'phone_operations':False}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: real publication failure paths, complete properties at discovery, bounded startup wait (ASan/UBSan)')
