#!/usr/bin/env python3
"""Run real SystemOS/AKS/HID checks for the standalone query kernel and control."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
kind='baseline-link-4' if args.baseline else 'activation-link-3'
directory=ROOT/'artifacts/venus-mg-query-009'/kind
candidate=json.loads((DEVICE/'evidence/mg-query-candidate.json').read_text())
flags=[f for f in candidate['args'].split() if not f.startswith(('native-ufs-root=','sheng-pmgr=','sheng-build-tag=','sheng-gpu-addon='))]
if not args.baseline:flags+=['venus-mg-task=1']
command=['python3','-B',str(DEVICE/'scripts/test-venus-root-mount.py'),'--kernel',str(directory/'kernel.macho'),
         '--prelink-report',str(directory/'kernel.json'),'--owned-memory-size','0x180000000','--qemu-memory-mib','8192',
         '--systemos-checkpoint','--inspect-memory-budget','--inspect-os-services',
         '--out-name','qemu-mg-query-009'+('-baseline' if args.baseline else ''),'--extra-kernel-arg',' '.join(flags)]
subprocess.run(command,check=True,timeout=420)
