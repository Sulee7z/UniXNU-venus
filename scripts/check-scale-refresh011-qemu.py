#!/usr/bin/env python3
"""Real SystemOS control and post-Data syscall checkpoint; no phone operation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-checkpoint',action='store_true')
parser.add_argument('--version',choices=('011','012'),default='011');args=parser.parse_args()
VERSION=args.version;ARTIFACT=ROOT/'artifacts'/('venus-scale-refresh-'+VERSION)
DIR=ARTIFACT/('refresh-link-3' if VERSION=='012' else 'refresh-link-2')
base=json.loads((DEVICE/'evidence/sheng-chain-control-candidate.json').read_text())
flags=[f for f in base['args'].split() if not f.startswith(('native-ufs-root=','sheng-pmgr=','sheng-build-tag=','sheng-data-persist='))]
flags+=['venus-gestalt-refresh=1','sheng-data-persist=0']
if not args.data_checkpoint:
    subprocess.run(['python3','-B',str(DEVICE/'scripts/test-venus-root-mount.py'),'--kernel',str(DIR/'kernel.macho'),
        '--prelink-report',str(DIR/'kernel.json'),'--owned-memory-size','0x180000000','--qemu-memory-mib','8192',
        '--systemos-checkpoint','--inspect-memory-budget','--inspect-os-services','--out-name','qemu-scale-refresh'+VERSION+'-systemos'+('-r3' if VERSION=='012' else ''),
        '--extra-kernel-arg',' '.join(flags)],check=True,timeout=420)
    raise SystemExit(0)
out=ARTIFACT/('qemu-data-checkpoint-r3' if VERSION=='012' else 'qemu-data-checkpoint');out.mkdir(exist_ok=False)
fields=['_venus_scale'+VERSION+'_journal_status','_venus_gestalt_status','_venus_gestalt_requested','_venus_gestalt_moved',
        '_venus_gestalt_missing','_native_owner_data_stage','_native_owner_data_status','_native_owner_data_readonly']
if VERSION=='012':fields+=['_venus_scale012_full_sync_status','_venus_scale012_source_uid','_venus_scale012_source_mode','_venus_scale012_source_size','_venus_scale012_cache_failure_phase']
symbols=subprocess.check_output(['/usr/bin/llvm-nm',str(DIR/'kernel.macho')],text=True)
reads=[]
for name in fields:
    matches=re.findall(r'^([0-9a-f]+)\s+\S\s+'+re.escape(name)+r'$',symbols,re.M)
    if len(matches)!=1:raise ValueError('Missing checkpoint symbol: '+name)
    reads.append(matches[0]+':4')
(out/'metadata-plan.json').write_text(json.dumps({'kernel_sha256':hashlib.sha256((DIR/'kernel.macho').read_bytes()).hexdigest(),'read_memory':reads},indent=2)+'\n')
fdt=out/'qemu.dtb'
command=['qemu-system-aarch64','-machine','virt,virtualization=off,secure=off,gic-version=3,dumpdtb='+str(fdt),
    '-cpu','cortex-a710','-m','8192','-smp','1','-display','none','-nic','none','-device','ramfb','-global','virtio-mmio.force-legacy=false']
for label,name in (('offline-block','OS.raw'),('offline-extra','SystemOS.raw')):
    command+=['-blockdev',json.dumps({'driver':'raw','node-name':label,'read-only':True,
        'file':{'driver':'file','filename':str(ROOT/'artifacts/venus-deployment'/name),'read-only':True,'locking':'off'}}),
        '-device','virtio-blk-device,drive='+label]
subprocess.run(command,check=True,timeout=30)
probe=['python3','-B',str(DEVICE/'scripts/probe-venus-prelinked.py'),'--kernel',str(DIR/'kernel.macho'),
    '--prelink-report',str(DIR/'kernel.json'),'--output',str(out),'--armvirt','--armdt-platform','--armcpu','--nvram-proxy',
    '--qemu-ramfb','--crypto-hash-method','sha2-384','--osenvironment','main','--amfi-platform-only',
    '--owned-memory-size','0x180000000','--qemu-memory-mib','8192',
    '--virtio-block-image',str(ROOT/'artifacts/venus-deployment/OS.raw'),
    '--virtio-extra-block-image',str(ROOT/'artifacts/venus-deployment/SystemOS.raw'),
    '--virtio-mmio-fdt',str(fdt),'--root-match-volume-uuid','04769D26-2CA0-4825-B443-E2E5F88300F2',
    '--trust-cache',str(ROOT/'artifacts/venus-deployment/original-static-system.bundle'),'--load-apfs','--inspect-owner-root',
    '--kernel-extra-args','sheng-pmgr=2 native-ufs-root=0 '+' '.join(flags),
    '--data-ramdisk',str(ARTIFACT/'snapshot-fixture/metadata-and-MG.dbr' if VERSION=='012' else ROOT/'artifacts/venus-deployment/Data.dbr'),'--packed-data-fixture',
    '--metadata-plan',str(out/'metadata-plan.json'),'--break-symbol','_venus_scale'+VERSION+'_checkpoint','--timeout','240']
result=subprocess.run(probe,capture_output=True,text=True,timeout=330)
(out/'probe.log').write_text(result.stdout+result.stderr)
if result.returncode:raise SystemExit(result.stdout+result.stderr)
report=json.loads((out/'gdb-stop.json').read_text());values={}
for name,address in zip(fields,reads):
    raw=report['memory'][address]
    if len(raw)!=8 or raw.startswith('E'):raise ValueError('Unreadable checkpoint '+name)
    values[name]=int.from_bytes(bytes.fromhex(raw),'little',signed=name.endswith('status'))
passed=(report['stop_symbol']=='_venus_scale'+VERSION+'_checkpoint' and not report['bounded_timeout_interrupted'] and
        values['_native_owner_data_stage']==4 and values['_native_owner_data_status']==0)
if VERSION=='011':passed=passed and values['_venus_scale011_journal_status']==5 and values['_venus_gestalt_requested']==0 and values['_venus_gestalt_moved']==0
else:passed=passed and values['_venus_gestalt_requested']==1 and values['_venus_gestalt_moved']==1 and values['_venus_gestalt_missing']==6 and values['_venus_gestalt_status']==5
record={'passed':passed,'state':values,'kernel_sha256':report['kernel_sha256'],
        'scope':('Actual packed Data/APFS/post-policy/cache-journal checkpoint in QEMU. UFS medium absent, so synchronization refusal and zero cache moves are expected; positive rename/durability is covered by model and phone.' if VERSION=='011' else
                 'Actual APFS cache rename and source/backup directory sync on a QEMU-only metadata+exact-MG snapshot fixture. Moved1/missing6 expected; cache medium sync EIO retained because UFS is absent. No phone durability or UI success claim.')}
(out/'result.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if not passed:raise SystemExit('Data/checkpoint failed')
