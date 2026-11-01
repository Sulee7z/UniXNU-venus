#!/usr/bin/env python3
"""Execute the plugin's bounded diagnostic writer against a real test file."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

DEVICE=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
log=out/'native.jsonl';binary=out/'diagnostic-test'
command=['gcc','-std=gnu11','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
         '-fno-omit-frame-pointer',f'-DVENUS_METAL_DIAG_TEST="{log}"',
         str(DEVICE/'tests/venus_metal_diagnostics.c'),'-o',str(binary)]
subprocess.run(command,check=True)
result=subprocess.run([str(binary)],capture_output=True,text=True)
(out/'test.log').write_text(result.stdout+result.stderr)
if result.returncode:raise SystemExit(result.stderr)
lines=log.read_text().splitlines()
assert len(lines)==2
events=[json.loads(line) for line in lines]
assert events[0]=={'schema':1,'process':'backboardd','pid':events[0]['pid'],
                   'seconds':events[0]['seconds'],'stage':'entry',
                   'detail':'quote " slash \\ control \x01','errno':events[0]['errno']}
assert events[1]['stage']=='device' and events[1]['detail']=='Metal device created'
assert events[0]['pid']==events[1]['pid'] and events[0]['seconds']>0
report={'passed':True,'command':command,'events':events,
    'source_sha256':hashlib.sha256((DEVICE/'package/Metal13/VenusMetalDiagnostics.h').read_bytes()).hexdigest(),
    'sanitizers':['address','undefined'],'phone_operations':False,'postlaunch_device_verified':False,
    'scope':'Actual bounded file writer/JSON escaping; not a Metal discovery result.'}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: actual postlaunch diagnostic writer, JSON escaping and append (ASan/UBSan)')
