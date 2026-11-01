#!/usr/bin/env python3
"""Qualify retained SystemOS/AKS/HID/memory with new touch code default-off."""
import argparse
import json
from pathlib import Path
import subprocess
ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus';KERNEL=ROOT/'artifacts/venus-metal-touch/kernel-link-5'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--touch-mode',choices=('0','1','3'),default='0')
parser.add_argument('--name',default=None);parser.add_argument('--kernel-dir',type=Path,default=KERNEL);args=parser.parse_args();KERNEL=args.kernel_dir
control=json.loads((ROOT/'artifacts/venus-scale-refresh-012/candidate.json').read_text())
flags=[f for f in control['args'].split() if not f.startswith(('native-ufs-root=','sheng-pmgr=','sheng-build-tag=','sheng-data-persist=','venus-gestalt-refresh=','venus-st-touch='))]
flags+=['sheng-data-persist=0','venus-st-touch='+args.touch_mode]
command=['python3','-B',str(DEVICE/'scripts/test-venus-root-mount.py'),'--kernel',str(KERNEL/'kernel.macho'),
    '--prelink-report',str(KERNEL/'kernel.json'),'--owned-memory-size','0x180000000','--qemu-memory-mib','8192',
    '--systemos-checkpoint','--inspect-memory-budget','--inspect-os-services',
    '--out-name',args.name or ('qemu-metal-touch-default-off' if args.touch_mode=='0' else 'qemu-metal-touch-mode'+args.touch_mode),
    '--extra-kernel-arg',' '.join(flags)]
subprocess.run(command,check=True,timeout=420)
