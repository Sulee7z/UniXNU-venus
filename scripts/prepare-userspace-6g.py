#!/usr/bin/env python3
"""Prepare/check the requested6GiB normal-boot variant and its new memory firmware."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tomllib
DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
BASE=Path('/root/unixnu-build/UniXNU-sheng-base')
CONTROL=ROOT/'artifacts/venus-userspace-001';OUT=ROOT/'artifacts/venus-userspace-6g-001'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--finish',action='store_true',help='Check the built6GiB firmware/image and write its receipt')
options=parser.parse_args()
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def need(ok,why):
    if not ok:raise SystemExit(why)
def run(argv):return subprocess.check_output([str(v) for v in argv],timeout=180)
control=load(CONTROL/'candidate.json');qualified=load(DEVICE/'evidence/data-persistence-qualified.json')
need(control['kernel_sha256']==qualified['kernel_sha256'] and qualified['passed'],'Qualified kernel changed')
need(sha(CONTROL/'phone/boot-venus-unixnu.img')==control['image_sha256'],'Control image changed')
need(sha(CONTROL/'phone/payload.img')==control['payload_sha256'],'Control payload changed')
need(sha(DEVICE/'board.toml')==control['board_sha256'],'Base board changed')
mapping=ROOT/'ports/uefi-venus/Platforms/Xiaomi/venusPkg/Library/MemoryMapLib/MemoryMapLib.c'
dsc=ROOT/'ports/uefi-venus/Platforms/Xiaomi/venusPkg/venus.dsc'
map_report=load(DEVICE/'evidence/highmem-6g-map-check.json')
need(sha(mapping)==map_report['source_sha256'] and map_report['high_region']['bytes']==0x180000000 and
     not map_report['high_reserved_overlaps'] and not map_report['map_overlaps'],'6GiB physical map not qualified on host')
need('UNIXNU_VENUS_6G_MEMORY' in dsc.read_text(),'6GiB firmware switch missing')
qdir=ROOT/'artifacts/venus-ufs-root/qemu-userspace-6g'
qemu=load(qdir/'gdb-stop.json');budget=load(qdir/'memory-budget.json');services=load(qdir/'os-services.json')
need(qemu['kernel_sha256']==control['kernel_sha256'] and qemu['stop_symbol']=='_native_owner_cache_checkpoint' and
     not qemu['bounded_timeout_interrupted'] and qemu['owner_cache_mount']['_native_owner_cache_status']==0,'6GiB QEMU mount check failed')
need(budget['_max_mem']==budget['requested_owned_bytes']==0x180000000,'QEMU did not actually use6GiB')
need(services['aks_state_passed'] and services['hid_state_passed'],'OS service control failed')
spec=importlib.util.spec_from_file_location('codec',DEVICE/'scripts/inject-a660-firmware-adt.py')
codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
original=(CONTROL/'kernel.macho.adt').read_bytes();adt_tree=codec.parse(original)
chosen=codec.find(adt_tree,'chosen');props=dict(chosen.props)
need(int.from_bytes(props['darwinboot-memory-size'],'little')==0x40000000,'Unexpected control window')
chosen.props=[(name,struct.pack('<Q',0x180000000) if name=='darwinboot-memory-size' else value) for name,value in chosen.props]
adt=codec.dump(adt_tree)
sys.path.insert(0,str(BASE/'scripts'))
from unixnu.cli import parser as cli_parser
from unixnu.config import Context
from unixnu.devicetree import generate
ctx=Context(cli_parser().parse_args(['status','-D',str(DEVICE),'--out','/root/unixnu-build/venus-legacy-full']))
board=copy.deepcopy(ctx.board);board['payload']['adt']['owned_memory_size']='0x180000000'
generated=generate(ROOT/'artifacts/venus-stage-foundation/hardware/hardware.dtb',board,
    unique_chip_id=format(int.from_bytes(props['unique-chip-id'],'little'),'x'),data=True,trust=True)
def normalized(node):return(node.name,[(k,v) for k,v in node.props if k!='random-seed'],[normalized(c) for c in node.children])
need(normalized(codec.parse(adt))==normalized(codec.parse(generated)),'6GiB sidecar differs from real board generator')
# Restoring just this property must recover the complete original sidecar.
chosen.props=[(k,props[k] if k=='darwinboot-memory-size' else v) for k,v in chosen.props]
need(codec.dump(adt_tree)==original,'Unexpected additional ADT change')
args=control['args'].split();need(args[-1]=='sheng-build-tag=userspace-001','Unexpected control tag')
args[-1]='sheng-build-tag=userspace-6g-001';kernel_args=' '.join(args)
need(not any(a.startswith(('venus-data-check=','sheng-data-reset=','sheng-autoreset=')) for a in args),'Unexpected stop/reset gate')
phone=OUT/'phone'
if not options.finish:
    need(not OUT.exists(),'Preserve the existing6GiB candidate')
    OUT.mkdir();phone.mkdir();(OUT/'kernel').mkdir();(OUT/'inputs').mkdir()
    for name in ('kernel.macho','kernel.json'):shutil.copy2(CONTROL/'kernel'/name,OUT/'kernel'/name)
    (OUT/'kernel.macho.adt').write_bytes(adt)
    shutil.copy2(CONTROL/'phone/payload.img',phone/'payload.img')
    config=(CONTROL/'phone/unixnu.toml').read_text()
    need(config.count(control['args'])==1,'Ambiguous old arguments')
    config=config.replace(control['args'],kernel_args).replace('Mi 11 iPadOS CPU system boot','Mi 11 iPadOS 6GiB CPU system boot')
    (phone/'unixnu.toml').write_text(config)
    for local,target in ((OUT/'kernel.macho.adt','Payloads/kernel.macho.adt'),(phone/'unixnu.toml','unixnu.toml')):
        run(['mcopy','-o','-i',phone/'payload.img',local,'::/EFI/UniXNU/'+target])
    for src,name in ((mapping,'MemoryMapLib.c'),(dsc,'venus.dsc'),(DEVICE/'evidence/highmem-6g-map-check.json','map-check.json'),
                     (qdir/'gdb-stop.json','qemu-systemos.json'),(qdir/'memory-budget.json','qemu-memory-budget.json')):
        shutil.copy2(src,OUT/'inputs'/name)
    plan={'device':'venus','requested_owned_bytes':0x180000000,'requested_owned_mib':6144,
          'kernel_sha256':control['kernel_sha256'],'adt_sha256':sha(OUT/'kernel.macho.adt'),
          'args':kernel_args,'base_image_sha256':control['image_sha256'],'firmware_six_gib_required':True,
          'map_source_sha256':sha(mapping),'dsc_sha256':sha(dsc),'qemu_systemos_sha256':sha(qdir/'gdb-stop.json')}
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print('Prepared6GiB payload; build its6GiB firmware next');raise SystemExit(0)

plan=load(OUT/'plan.json');need(plan['requested_owned_bytes']==0x180000000,'Plan changed')
need(sha(mapping)==plan['map_source_sha256']==sha(OUT/'inputs/MemoryMapLib.c'),'Firmware source changed after planning')
need(sha(dsc)==plan['dsc_sha256']==sha(OUT/'inputs/venus.dsc'),'Firmware DSC changed after planning')
need((OUT/'kernel.macho.adt').read_bytes()==adt,'Sidecar changed')
def payload(name):return run(['mtype','-i',phone/'payload.img','::/EFI/UniXNU/'+name])
need(payload('Payloads/kernel.macho.adt')==adt,'Payload sidecar mismatch')
need(tomllib.loads(payload('unixnu.toml').decode())['entry'][0]['args']==kernel_args,'Payload args mismatch')
retained={}
for name in ('kernel.macho','scratch-data.img','kernel.macho.trustcache'):
    data=payload('Payloads/'+name)
    need(data==run(['mtype','-i',CONTROL/'phone/payload.img','::/EFI/UniXNU/Payloads/'+name]),'Payload changed: '+name)
    retained[name]=hashlib.sha256(data).hexdigest()
verification=load(phone/'verification.json')
need(verification['efi']==load(CONTROL/'phone/verification.json')['efi'],'Loader EFI modules changed from normal-boot control')
need(verification['roundtrip_verified'] and not verification['uefi_memory_conflicts'],'Firmware boot container failed')
need(sha(phone/'boot-venus-unixnu.img')==verification['sha256'],'Final image changed')
need(sha(phone/'SILICIUM_UEFI.fd')==verification['fd_sha256'],'FD changed')
need('UNIXNU_VENUS_6G_MEMORY' in (phone/'build-report.txt').read_text(),'6GiB compile flag missing')
need(struct.pack('<QQ',0x100000000,0x180000000) in (phone/'Sec.efi').read_bytes(),'Compiled SEC does not contain6GiB descriptor')
need(load(phone/'layout-check.json')['memory_conflicts']==0,'Compiled firmware layout failed')
report={**plan,'image':str(phone/'boot-venus-unixnu.img'),'image_sha256':verification['sha256'],
        'image_bytes':verification['bytes'],'payload_sha256':sha(phone/'payload.img'),
        'fd_sha256':verification['fd_sha256'],'efi':verification['efi'],'retained_payload_inputs':retained,
        'compiled_six_gib_map_verified':True,'loader_efi_modules_unchanged':True,
        'board_sha256':sha(DEVICE/'board.toml'),'qemu_actual_memory':budget,'phone_tested':False,
        'scope':'User-requested6GiB window and matching6GiB firmware region, same normal-start kernel/Data/trust. Host/QEMU checks do not prove physical6GiB allocation or cure the87s stall.'}
(OUT/'candidate.json').write_text(json.dumps(report,indent=2)+'\n')
(DEVICE/'evidence/userspace-6g-candidate.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: actual6GiB QEMU, compiled6GiB SEC descriptor, payload identity and boot container')
print('BOOT:',report['image']);print('SHA256:',report['image_sha256'])
