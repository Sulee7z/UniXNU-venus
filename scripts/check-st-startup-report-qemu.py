#!/usr/bin/env python3
"""Exercise real post-Data APFS report write/readback/fsync and scratch preservation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--kernel-dir',type=Path,default=ROOT/'artifacts/venus-metal-touch/kernel-link-11')
parser.add_argument('--output',type=Path,default=ROOT/'artifacts/venus-st-touch/qemu-startup-report');args=parser.parse_args()
KERNEL=args.kernel_dir;OUT=args.output;OUT.mkdir(parents=True,exist_ok=False)
names=['_venus_st_report_status','_venus_st_report_full_status','_venus_st_report_medium_status','_venus_st_report_bytes','_venus_st_report_readback_ok','_venus_st_report_env_ok']
symbols=subprocess.check_output(['/usr/bin/llvm-nm',str(KERNEL/'kernel.macho')],text=True);reads={}
for name in names:
    addresses=re.findall(r'^([0-9a-f]+)\s+\S\s+'+re.escape(name)+r'$',symbols,re.M);assert len(addresses)==1;reads[name]=addresses[0]+':4'
digest=hashlib.sha256((KERNEL/'kernel.macho').read_bytes()).hexdigest()
(OUT/'metadata.json').write_text(json.dumps({'kernel_sha256':digest,'read_memory':list(reads.values())},indent=2)+'\n')
fdt=OUT/'qemu.dtb';command=['qemu-system-aarch64','-machine','virt,virtualization=off,secure=off,gic-version=3,dumpdtb='+str(fdt),'-cpu','cortex-a710','-m','8192','-smp','1','-display','none','-nic','none','-device','ramfb','-global','virtio-mmio.force-legacy=false']
for label,name in (('offline-block','OS.raw'),('offline-extra','SystemOS.raw')):
    command+=['-blockdev',json.dumps({'driver':'raw','node-name':label,'read-only':True,'file':{'driver':'file','filename':str(ROOT/'artifacts/venus-deployment'/name),'read-only':True,'locking':'off'}}),'-device','virtio-blk-device,drive='+label]
subprocess.run(command,check=True,timeout=30)
flags=json.loads((ROOT/'artifacts/venus-touch-015/candidate.json').read_text())['args'].split()
flags=[f for f in flags if not f.startswith(('native-ufs-root=','sheng-pmgr=','sheng-data-persist=','sheng-build-tag=','venus-st-touch='))]
flags+=['native-ufs-root=0','sheng-pmgr=2','sheng-data-persist=0','venus-st-touch=0','venus-st-report=1']
probe=['python3','-B',str(DEVICE/'scripts/probe-venus-prelinked.py'),'--kernel',str(KERNEL/'kernel.macho'),'--prelink-report',str(KERNEL/'kernel.json'),'--output',str(OUT),
    '--armvirt','--armdt-platform','--armcpu','--nvram-proxy','--qemu-ramfb','--crypto-hash-method','sha2-384','--osenvironment','main','--amfi-platform-only',
    '--owned-memory-size','0x180000000','--qemu-memory-mib','8192','--virtio-block-image',str(ROOT/'artifacts/venus-deployment/OS.raw'),
    '--virtio-extra-block-image',str(ROOT/'artifacts/venus-deployment/SystemOS.raw'),'--virtio-mmio-fdt',str(fdt),'--root-match-volume-uuid','04769D26-2CA0-4825-B443-E2E5F88300F2',
    '--trust-cache',str(ROOT/'artifacts/venus-deployment/original-static-system.bundle'),'--load-apfs','--inspect-owner-root','--kernel-extra-args',' '.join(flags),
    '--data-ramdisk',str(ROOT/'artifacts/venus-deployment/Data.dbr'),'--packed-data-fixture',
    '--metadata-plan',str(OUT/'metadata.json'),'--break-symbol','_venus_st_report_checkpoint','--timeout','240']
result=subprocess.run(probe,capture_output=True,text=True,timeout=360);(OUT/'probe.log').write_text(result.stdout+result.stderr)
report=json.loads((OUT/'gdb-stop.json').read_text());state={}
for name,address in reads.items():
    raw=report['memory'][address];assert len(raw)==8 and not raw.startswith('E');state[name]=int.from_bytes(bytes.fromhex(raw),'little',signed=True)
passed=report['stop_symbol']=='_venus_st_report_checkpoint' and not report['bounded_timeout_interrupted'] and state['_venus_st_report_readback_ok']==1 and state['_venus_st_report_env_ok']==1 and state['_venus_st_report_bytes']>0 and state['_venus_st_report_status']==5 and state['_venus_st_report_medium_status']==5 and state['_venus_st_report_full_status']==0
receipt={'kernel_sha256':digest,'state':state,'passed':passed,'scope':'Real APFS report exact write/pread verification, file/full/directory sync, scratch400-700 unchanged; final mediumEIO expected with no QEMU UFS. Not phone persistence/physical touch.'}
(OUT/'report.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if not passed:raise SystemExit('Startup report APFS check failed')
