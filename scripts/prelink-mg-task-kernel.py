#!/usr/bin/env python3
"""Use the selected format-2 prelink plan with a standalone native input."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True)
parser.add_argument('--hid-touch',action='store_true',help='Include original21H461 codeless digitizer event matching')
parser.add_argument('--resume-failed-write',action='store_true',help='Preserve incomplete output from recorded Errno5 write failure before rerunning')
args=parser.parse_args()
work=args.directory;out=work/'kernel.macho'
if args.resume_failed_write:
    failure=work/'prelink.log'
    if (work/'kernel.json').exists() or not out.exists() or 'OSError: [Errno 5] Input/output error' not in failure.read_text():
        parser.error('Not a recorded incomplete output write')
    saved=work/'kernel.macho.write-failed'
    if saved.exists():parser.error('Failure backup already exists')
    out.rename(saved);failure.rename(work/'prelink.write-failed.log')
if out.exists():parser.error('Preserve completed prelink')
sys.path.insert(0,'/root/unixnu-build/UniXNU-sheng-base/scripts')
from unixnu.cli import parser as cli_parser
from unixnu.config import Context
ctx=Context(cli_parser().parse_args(['status','-D',str(DEVICE),'--out','/root/unixnu-build/venus-legacy-full']))
spec=ctx.board['kernel']['prelink'];native=work/'native.macho'
command=['python3',str(ctx.tree/spec['tool']),'--kernel',str(native),
         '--prelinked',str(ROOT/'artifacts/venus-guide/ipsw/21H461/kernelcache.decompressed'),
         f'--slide={spec["slide"]}','--output',str(out)]
for name in spec.get('roots',[]):command+=['--root',name]
if args.hid_touch:command+=['--root','com.apple.iokit.IOHIDEventDriverSafeBoot']
if spec.get('early_security_init'):command+=['--early-security-init',spec['early_security_init']]
command+=spec.get('extra_args',[])
result=subprocess.run(command,cwd=ctx.tree,capture_output=True,text=True,timeout=300)
(work/'prelink.log').write_text(result.stdout+result.stderr)
(work/'prelink-command.json').write_text(json.dumps(command,indent=2)+'\n')
if result.returncode:raise SystemExit(result.stdout+result.stderr)
print('Prelinked:',out,hashlib.sha256(out.read_bytes()).hexdigest())
