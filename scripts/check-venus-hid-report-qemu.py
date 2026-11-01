#!/usr/bin/env python3
"""Run actual original HID parser/driver and Venus reports with QEMU-only input."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--kernel-dir',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True);parser.add_argument('--expect',choices=('pass','fail'),default='pass');args=parser.parse_args()
KERNEL=args.kernel_dir;OUT=args.output;OUT.mkdir(parents=True,exist_ok=False)
assert json.loads((KERNEL/'report.json').read_text())['qemu_only']
symbols=subprocess.check_output(['/usr/bin/llvm-nm',str(KERNEL/'kernel.macho')],text=True)
fields=['_venus_st_test_passed','_venus_st_test_reads','_venus_st_test_sink','_venus_st_hid_reports','_venus_st_hid_ready','_venus_st_hid_status']
for name in ('_venus_st_hid_ticks','_venus_st_hid_phase','_venus_st_hid_registry'):
    if re.search(r'\b'+name+r'$',symbols,re.M):fields.append(name)
reads={}
for name in fields:
    addresses=re.findall(r'^([0-9a-f]+)\s+\S\s+'+re.escape(name)+r'$',symbols,re.M);assert len(addresses)==1
    reads[name]=addresses[0]+(':400' if name.endswith('registry') else ':4')
digest=hashlib.sha256((KERNEL/'kernel.macho').read_bytes()).hexdigest()
(OUT/'metadata.json').write_text(json.dumps({'kernel_sha256':digest,'read_memory':list(reads.values())},indent=2)+'\n')
fdt=OUT/'qemu.dtb';command=['qemu-system-aarch64','-machine','virt,virtualization=off,secure=off,gic-version=3,dumpdtb='+str(fdt),'-cpu','cortex-a710','-m','8192','-smp','1','-display','none','-nic','none','-device','ramfb','-global','virtio-mmio.force-legacy=false']
for label,name in (('offline-block','OS.raw'),('offline-extra','SystemOS.raw')):
    command+=['-blockdev',json.dumps({'driver':'raw','node-name':label,'read-only':True,'file':{'driver':'file','filename':str(ROOT/'artifacts/venus-deployment'/name),'read-only':True,'locking':'off'}}),'-device','virtio-blk-device,drive='+label]
subprocess.run(command,check=True,timeout=30)
flags=json.loads((ROOT/'artifacts/venus-touch-015/candidate.json').read_text())['args'].split()
flags=[f for f in flags if not f.startswith(('native-ufs-root=','sheng-pmgr=','sheng-data-persist=','sheng-build-tag='))]
flags+=['native-ufs-root=0','sheng-pmgr=2','sheng-data-persist=0']
probe=['python3','-B',str(DEVICE/'scripts/probe-venus-prelinked.py'),'--kernel',str(KERNEL/'kernel.macho'),'--prelink-report',str(KERNEL/'kernel.json'),'--output',str(OUT),
    '--armvirt','--armdt-platform','--armcpu','--nvram-proxy','--qemu-ramfb','--crypto-hash-method','sha2-384','--osenvironment','main','--amfi-platform-only',
    '--owned-memory-size','0x180000000','--qemu-memory-mib','8192','--virtio-block-image',str(ROOT/'artifacts/venus-deployment/OS.raw'),
    '--virtio-extra-block-image',str(ROOT/'artifacts/venus-deployment/SystemOS.raw'),'--virtio-mmio-fdt',str(fdt),'--root-match-volume-uuid','04769D26-2CA0-4825-B443-E2E5F88300F2',
    '--trust-cache',str(ROOT/'artifacts/venus-deployment/original-static-system.bundle'),'--load-apfs','--inspect-owner-root','--kernel-extra-args',' '.join(flags),
    '--data-ramdisk',str(ROOT/'artifacts/venus-deployment/Data.dbr'),'--packed-data-fixture',
    '--metadata-plan',str(OUT/'metadata.json'),'--break-symbol','_venus_st_hid_test_done','--timeout','240']
result=subprocess.run(probe,capture_output=True,text=True,timeout=360);(OUT/'probe.log').write_text(result.stdout+result.stderr)
report=json.loads((OUT/'gdb-stop.json').read_text());state={}
for name,address in reads.items():
    raw=report['memory'][address];assert len(raw)==int(address.split(':')[1],16)*2 and not raw.startswith('E')
    data=bytes.fromhex(raw);state[name]=data.split(b'\0')[0].decode('utf-8','replace') if name.endswith('registry') else int.from_bytes(data,'little')
valid=report['stop_symbol']=='_venus_st_hid_test_done' and not report['bounded_timeout_interrupted']
passed=valid and state['_venus_st_test_passed']==1
receipt={'kernel_sha256':digest,'stop':report['stop_symbol'],'state':state,'passed':passed,'qemu_only':True,
    'scope':'Original17 HID parser/event-driver match and actual Venus report down/move/up. QEMU-only producer; no physical touchscreen or UIKit qualification.'}
(OUT/'report.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if not valid or passed!=(args.expect=='pass'):raise SystemExit('HID report result differs from expected outcome')
