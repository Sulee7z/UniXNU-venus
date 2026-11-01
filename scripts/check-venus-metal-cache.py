#!/usr/bin/env python3
"""Exercise the actual plugin cache helper on the G-backed Linux filesystem."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

DEVICE=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
fixture=out/'fixture';fixture.mkdir()
binary=out/'cache-test'
command=['gcc','-std=gnu11','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
         '-fno-omit-frame-pointer',str(DEVICE/'tests/venus_metal_cache.c'),'-o',str(binary)]
subprocess.run(command,check=True)
result=subprocess.run([str(binary),str(fixture)],capture_output=True,text=True)
(out/'test.log').write_text(result.stdout+result.stderr)
if result.returncode:raise SystemExit(result.stderr)
record={'passed':True,'command':command,'cases':['bounded path/truncation','new/private cache',
    'existing cache','readable-by-other-users refusal','missing write/execute permission','regular file preservation',
    'symlink preservation/refusal','missing parent','wrong owner'],
    'source_sha256':hashlib.sha256((DEVICE/'package/Metal13/VenusMetalCache.h').read_bytes()).hexdigest(),
    'sanitizers':['address','undefined'],'phone_operations':False,'ios_device_open_verified':False}
(out/'report.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS: actual cache/path helpers with filesystem failure cases (ASan/UBSan)')
