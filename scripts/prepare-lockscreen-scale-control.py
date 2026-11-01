#!/usr/bin/env python3
"""Keep the phone-qualified kernel; test early scale properties independently."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
CONTROL=ROOT/'artifacts/venus-userspace-6g-001'
FAILED=ROOT/'artifacts/venus-lockscreen-scale-001'
BASE=Path('/root/unixnu-build/UniXNU-sheng-base')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check',action='store_true')
parser.add_argument('--scale',type=int,default=2,help='chosen display-scale value')
parser.add_argument('--out-name',default='venus-lockscreen-scale-002')
args=parser.parse_args()
OUT=ROOT/'artifacts'/args.out_name
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(path):return json.loads(path.read_text())
def need(ok,why):
    if not ok:raise SystemExit(why)
need(1 <= args.scale <= 3, 'display-scale must be 1..3')
def run(argv):return subprocess.check_output([str(x) for x in argv],timeout=240)
def fat(image,name):return run(['mtype','-i',image,'::/EFI/UniXNU/'+name])
control=load(CONTROL/'candidate.json');failed=load(FAILED/'candidate.json')
need(sha(CONTROL/'phone/boot-venus-unixnu.img')==control['image_sha256'] and
     sha(CONTROL/'phone/payload.img')==control['payload_sha256'],'Original6GiB control changed')
need(sha(CONTROL/'kernel/kernel.macho')==control['kernel_sha256']=='4b1ae1c0bc6ea2b7dbb440099ef5c0a0c413d26aab8bfe304f1fbc8b1a2760be','Qualified kernel changed')
need(sha(FAILED/'kernel.macho.adt')==failed['adt_sha256'],'001 sidecar changed')
need(sha(DEVICE/'board.toml')==failed['board_sha256'],'Current board differs from scale001')
spec=importlib.util.spec_from_file_location('codec',DEVICE/'scripts/inject-a660-firmware-adt.py')
codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
# Start from the 6GiB control sidecar (no chosen scale) and add only the two
# properties, so the value under test is the sole difference from the control.
tree=codec.parse((CONTROL/'kernel.macho.adt').read_bytes());chosen=codec.find(tree,'chosen');props=dict(chosen.props)
need('display-scale' not in props and 'display-rotation' not in props,'6GiB control already carries chosen scale')
need(int.from_bytes(props['darwinboot-memory-size'],'little')==0x180000000,'Not6GiB')
chosen.props=[(k,(args.scale).to_bytes(4,'little') if k=='display-scale' else v) for k,v in chosen.props]
chosen.props.append(('display-scale',args.scale.to_bytes(4,'little')))
chosen.props.append(('display-rotation',bytes(4)))
adt=codec.dump(tree)
med=codec.parse((FAILED/'kernel.macho.adt').read_bytes());mc=codec.find(med,'chosen')
mc.props=[(k,(args.scale).to_bytes(4,'little') if k=='display-scale' else v) for k,v in mc.props]
need(codec.dump(med)==adt,'Generated sidecar differs from 001-equivalent shape for this scale')
sys.path.insert(0,str(BASE/'scripts'))
from unixnu.cli import parser as cli_parser
from unixnu.config import Context
from unixnu.devicetree import generate
ctx=Context(cli_parser().parse_args(['status','-D',str(DEVICE),'--out','/root/unixnu-build/venus-legacy-full']))
board=copy.deepcopy(ctx.board);board['payload']['adt']['owned_memory_size']='0x180000000'
chosen_cfg=board.setdefault('adt',{}).setdefault('chosen',{}).setdefault('u32',{})
chosen_cfg['display-scale']=args.scale;chosen_cfg['display-rotation']=0
generated=codec.parse(generate(ROOT/'artifacts/venus-stage-foundation/hardware/hardware.dtb',board,
    unique_chip_id=f"{int.from_bytes(props['unique-chip-id'],'little'):x}",data=True,trust=True))
gc=codec.find(generated,'chosen');gc.props=[(k,props[k] if k=='random-seed' else v) for k,v in gc.props]
need(codec.dump(generated)==adt,'Actual current board generator mismatch')
baseargs=[a for a in control['args'].split() if not a.startswith('sheng-build-tag=')]
need(baseargs==board['payload']['kernel_args'],'Functional args changed')
kernelargs=' '.join([*baseargs,f'sheng-build-tag=lockscreen-scale-{args.scale:03d}'])
qdir=ROOT/'artifacts/venus-ufs-root/qemu-userspace-6g'
qemu=load(qdir/'gdb-stop.json');budget=load(qdir/'memory-budget.json');services=load(qdir/'os-services.json')
need(sha(qdir/'gdb-stop.json')==control['qemu_systemos_sha256'] and qemu['kernel_sha256']==control['kernel_sha256'] and
     qemu['owner_cache_mount']['_native_owner_cache_status']==0 and not qemu['bounded_timeout_interrupted'],'Prior same-kernel SystemOS receipt mismatch')
need(budget['_max_mem']==0x180000000 and services['aks_state_passed'] and services['hid_state_passed'],'Prior6GiB/services check mismatch')
phone=OUT/'phone'
if not args.check:
    need(not OUT.exists(),'Preserve existing control candidate')
    OUT.mkdir();phone.mkdir();(OUT/'kernel').mkdir();(OUT/'linked-inputs').mkdir()
    for name in ('kernel.macho','kernel.json'):shutil.copy2(CONTROL/'kernel'/name,OUT/'kernel'/name)
    for name in ('payload.img','SILICIUM_UEFI.fd','UniXNU.efi','UniXNUDxe.efi','DarwinBoot.efi','Sec.efi'):
        shutil.copy2(CONTROL/'phone'/name,phone/name)
    (OUT/'kernel.macho.adt').write_bytes(adt)
    config=(CONTROL/'phone/unixnu.toml').read_text()
    need(config.count(control['args'])==1,'Ambiguous old args')
    config=config.replace(control['args'],kernelargs)
    config+='\n[[entry]]\nid = "tools"\ntitle = "Tools"\ntype = "action"\naction = "tools"\n'
    need(len({e['id'] for e in tomllib.loads(config)['entry']})==len(tomllib.loads(config)['entry']),'Duplicate menu entry')
    (phone/'unixnu.toml').write_text(config)
    for local,target in ((OUT/'kernel.macho.adt','Payloads/kernel.macho.adt'),(phone/'unixnu.toml','unixnu.toml')):
        run(['mcopy','-o','-i',phone/'payload.img',local,'::/EFI/UniXNU/'+target])
    run(['python3',ROOT/'tools/package-venus-uefi.py','--tree',ROOT/'ports/uefi-venus','--workspace',ROOT,'--artifacts',phone,'--payload',phone/'payload.img'])
    for source,name in ((qdir/'gdb-stop.json','prior-same-kernel-qemu.json'),(DEVICE/'board.toml','board.toml'),
                        (DEVICE/'evidence/lockscreen-scale-phone.json','failed001-phone.json'),
                        (DEVICE/'evidence/lockscreen-scale-stall-host.json','stall-host.json')):
        shutil.copy2(source,OUT/'linked-inputs'/name)
retained={}
for name in ('kernel.macho','scratch-data.img','kernel.macho.trustcache'):
    blob=fat(phone/'payload.img','Payloads/'+name)
    need(blob==fat(CONTROL/'phone/payload.img','Payloads/'+name),'Payload input changed: '+name)
    retained[name]=hashlib.sha256(blob).hexdigest()
need(fat(phone/'payload.img','Payloads/kernel.macho.adt')==adt,'Wrong early-scale ADT')
config=tomllib.loads(fat(phone/'payload.img','unixnu.toml').decode())
need(config['entry'][0]['args']==kernelargs,'Wrong boot args')
v=load(phone/'verification.json')
need(v['roundtrip_verified'] and not v['uefi_memory_conflicts'] and v['fd_sha256']==control['fd_sha256'] and v['efi']==control['efi'],'Container/firmware mismatch')
need(sha(phone/'boot-venus-unixnu.img')==v['sha256'],'Image changed')
report={'device':'venus','date':'2026-10-29','image':str(phone/'boot-venus-unixnu.img'),
        'image_sha256':v['sha256'],'image_bytes':v['bytes'],'kernel_sha256':control['kernel_sha256'],
        'adt_sha256':sha(OUT/'kernel.macho.adt'),'payload_sha256':sha(phone/'payload.img'),
        'fd_sha256':v['fd_sha256'],'board_sha256':sha(DEVICE/'board.toml'),'args':kernelargs,
        'retained_payload_inputs':retained,'requested_display_scale':args.scale,
        'uses_phone_qualified_kernel':True,'cache_refresh_code_included':False,
        'prior_same_kernel_qemu_systemos_sha256':sha(qdir/'gdb-stop.json'),
        'qemu_rerun_for_this_packaging':False,'phone_tested':False,'normal_data_writes_expected':True,
        'scope':'Narrower control: original4b1ae1c0 kernel with early chosen scale2/rotation0. Tests input/timing sensitivity, not a proven SystemOS-stall fix or lockscreen result.'}
if args.check:need(load(OUT/'candidate.json')==report,'Saved candidate differs')
else:
    (OUT/'candidate.json').write_text(json.dumps(report,indent=2)+'\n')
    (DEVICE/'evidence/lockscreen-scale-control-candidate.json').write_text(json.dumps(report,indent=2)+'\n')
os.sync();print(json.dumps(report,indent=2))
