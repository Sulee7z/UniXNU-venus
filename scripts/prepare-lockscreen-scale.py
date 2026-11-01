#!/usr/bin/env python3
"""Package the scale/retained-cache candidate from current board generation and 6GiB firmware."""
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
BASE=Path('/root/unixnu-build/UniXNU-sheng-base')
WORK=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
CONTROL=ROOT/'artifacts/venus-userspace-6g-001'
OUT=ROOT/'artifacts/venus-lockscreen-scale-001'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
def need(ok,why):
    if not ok:raise SystemExit(why)
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(p.read_text())
def run(argv,timeout=240):return subprocess.check_output([str(x) for x in argv],timeout=timeout)
def fat(image,name):return run(['mtype','-i',image,'::/EFI/UniXNU/'+name])
control=load(CONTROL/'candidate.json')
need(sha(CONTROL/'phone/boot-venus-unixnu.img')==control['image_sha256']=='66f5314a97fb0fb052ded3c0c6d7ceb9d259c9eadd7519367bfef69b8ee5d660','6GiB control changed')
need(sha(CONTROL/'phone/payload.img')==control['payload_sha256'],'Control FAT changed')
tests=load(ROOT/'artifacts/venus-mode-scale-analysis/cache-tests/report.json')
screen=load(ROOT/'artifacts/venus-mode-scale-analysis/screen-tests/screen-report.json')
boot=load(WORK/'tree/build/boot-progress/build-report.json')
need(tests['passed'] and screen['passed'],'Host regression failed')
need(screen['source_sha256']['BootProgress.c']==sha(DEVICE/'package/boot-progress/BootProgress.c'),'Pixel test source changed')
need(sha(DEVICE/'package/boot-progress/BootGestaltCache.h')==tests['header_sha256']==boot['sources']['BootGestaltCache.h'],'Cache helper was not built/tested')
for path in (DEVICE/'package/boot-progress').glob('Boot*'):
    if path.suffix in ('.c','.h','.S'):need(sha(path)==boot['sources'][path.name],'Compiled boot source mismatch: '+path.name)
oldboot=load(ROOT/'artifacts/venus-data-check-002/linked-inputs/boot-progress-report.json')
for name in ('BootDataCheck.h','BootDataCheckCore.h','BootFaultProbe.c','BootFrontBoardMode.h','BootProgressLifecycle.h'):
    need(boot['sources'][name]==oldboot['sources'][name],'Unplanned Data/fault change: '+name)
need(sha(WORK/'tree/build/boot-progress/libBootProgress.a')==boot['archive_sha256'],'Archive receipt mismatch')
sys.path.insert(0,str(BASE/'scripts'))
from unixnu.cli import parser as cli_parser
from unixnu.config import Context
from unixnu.devicetree import generate
ctx=Context(cli_parser().parse_args(['status','-D',str(DEVICE),'--out',str(WORK.parents[2])]))
need(ctx.config_name=='venus_ufs_root_defconfig','Wrong full-root configuration')
board=copy.deepcopy(ctx.board);board['payload']['adt']['owned_memory_size']='0x180000000'
spec=importlib.util.spec_from_file_location('codec',DEVICE/'scripts/inject-a660-firmware-adt.py')
codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
oldadt=(CONTROL/'kernel.macho.adt').read_bytes();oldtree=codec.parse(oldadt)
oldchosen=dict(codec.find(oldtree,'chosen').props)
chip=int.from_bytes(oldchosen['unique-chip-id'],'little')
newtree=codec.parse(generate(ROOT/'artifacts/venus-stage-foundation/hardware/hardware.dtb',board,
                           unique_chip_id=f'{chip:x}',data=True,trust=True))
chosen=codec.find(newtree,'chosen')
chosen.props=[(k,oldchosen[k] if k=='random-seed' else v) for k,v in chosen.props]
values=dict(chosen.props)
need(values['display-scale']==b'\x02\x00\x00\x00' and values['display-rotation']==bytes(4),'Missing correctly typed boot scale/rotation')
need(values['darwinboot-memory-size']==(0x180000000).to_bytes(8,'little'),'6GiB window changed')
adt=codec.dump(newtree)
chosen.props=[(k,v) for k,v in chosen.props if k not in ('display-scale','display-rotation')]
need(codec.dump(newtree)==oldadt,'ADT changed beyond two intended properties')
boardargs=board['payload']['kernel_args']
need(boardargs==[a for a in control['args'].split() if not a.startswith('sheng-build-tag=')],'Functional board args changed')
kernelargs=' '.join([*boardargs,'venus-gestalt-refresh=1','sheng-build-tag=lockscreen-scale-001'])
need(len(kernelargs.encode())<1024,'Boot args too long')
phone=OUT/'phone'
if not args.check:
    need(not OUT.exists(),'Preserve existing candidate directory')
    OUT.mkdir();phone.mkdir();(OUT/'kernel').mkdir();(OUT/'linked-inputs').mkdir()
    for name in ('kernel.macho','kernel.json'):shutil.copy2(WORK/'kernel'/name,OUT/'kernel'/name)
    (OUT/'kernel.macho.adt').write_bytes(adt)
    for name in ('payload.img','SILICIUM_UEFI.fd','UniXNU.efi','UniXNUDxe.efi','DarwinBoot.efi','Sec.efi'):
        shutil.copy2(CONTROL/'phone'/name,phone/name)
    config=('version = 1\n[boot]\ntimeout = 5\ndefault = "xnu"\n[kits]\nautoload = false\n'
            '[[entry]]\nid = "xnu"\ntitle = "Mi 11 lockscreen scale 001 (6GiB)"\ntype = "xnu"\n'
            'path = "Payloads/kernel.macho"\ninitrd = "Payloads/scratch-data.img"\nargs = "'+kernelargs+'"\n'
            '[[entry]]\nid = "tools"\ntitle = "Tools"\ntype = "action"\naction = "tools"\n')
    (phone/'unixnu.toml').write_text(config)
    for local,target in ((OUT/'kernel/kernel.macho','Payloads/kernel.macho'),(OUT/'kernel.macho.adt','Payloads/kernel.macho.adt'),(phone/'unixnu.toml','unixnu.toml')):
        run(['mcopy','-o','-i',phone/'payload.img',local,'::/EFI/UniXNU/'+target])
    run(['python3',ROOT/'tools/package-venus-uefi.py','--tree',ROOT/'ports/uefi-venus','--workspace',ROOT,'--artifacts',phone,'--payload',phone/'payload.img'])
    for source in (DEVICE/'package/boot-progress').glob('Boot*'):
        if source.is_file():shutil.copy2(source,OUT/'linked-inputs'/source.name)
    for source,name in ((WORK/'tree/build/boot-progress/build-report.json','boot-progress-report.json'),
                        (WORK/'tree/build/boot-progress/libBootProgress.a','libBootProgress.a'),
                        (DEVICE/'board.toml','board.toml'),
                        (ROOT/'artifacts/venus-mode-scale-analysis/cache-tests/report.json','cache-tests.json'),
                        (ROOT/'artifacts/venus-mode-scale-analysis/screen-tests/screen-report.json','screen-tests.json')):
        shutil.copy2(source,OUT/'linked-inputs'/name)
    qargs=[a for a in kernelargs.split() if not a.startswith(('native-ufs-root=','sheng-pmgr='))]
    run(['python3',DEVICE/'scripts/test-venus-root-mount.py','--kernel',OUT/'kernel/kernel.macho',
         '--prelink-report',OUT/'kernel/kernel.json','--owned-memory-size','0x180000000','--qemu-memory-mib','8192',
         '--systemos-checkpoint','--inspect-memory-budget','--inspect-os-services','--out-name','qemu-lockscreen-scale-001',
         '--extra-kernel-arg',' '.join(qargs)],timeout=600)
kernelsha=sha(OUT/'kernel/kernel.macho')
need(kernelsha==sha(WORK/'kernel/kernel.macho'),'Built kernel changed')
need(fat(phone/'payload.img','Payloads/kernel.macho')==(OUT/'kernel/kernel.macho').read_bytes(),'Kernel FAT mismatch')
need(fat(phone/'payload.img','Payloads/kernel.macho.adt')==adt==(OUT/'kernel.macho.adt').read_bytes(),'ADT FAT mismatch')
need(tomllib.loads(fat(phone/'payload.img','unixnu.toml').decode())['entry'][0]['args']==kernelargs,'Args FAT mismatch')
retained={}
for name in ('scratch-data.img','kernel.macho.trustcache'):
    data=fat(phone/'payload.img','Payloads/'+name)
    need(data==fat(CONTROL/'phone/payload.img','Payloads/'+name),'Data/trust changed')
    retained[name]=hashlib.sha256(data).hexdigest()
verification=load(phone/'verification.json')
need(verification['roundtrip_verified'] and not verification['uefi_memory_conflicts'],'Boot roundtrip failed')
need(verification['fd_sha256']==control['fd_sha256']==sha(phone/'SILICIUM_UEFI.fd') and verification['efi']==control['efi'],'Firmware/loader changed')
qdir=ROOT/'artifacts/venus-ufs-root/qemu-lockscreen-scale-001'
qemu=load(qdir/'gdb-stop.json');budget=load(qdir/'memory-budget.json');services=load(qdir/'os-services.json')
need(qemu['kernel_sha256']==kernelsha and not qemu['bounded_timeout_interrupted'] and
     qemu['stop_symbol']=='_native_owner_cache_checkpoint' and qemu['owner_cache_mount']['_native_owner_cache_status']==0,'Actual SystemOS checkpoint failed')
need(budget['_max_mem']==0x180000000 and services['aks_state_passed'] and services['hid_state_passed'],'QEMU budget/services failed')
report={'date':'2026-10-29','device':'venus','image':str(phone/'boot-venus-unixnu.img'),
        'image_sha256':sha(phone/'boot-venus-unixnu.img'),'image_bytes':(phone/'boot-venus-unixnu.img').stat().st_size,
        'kernel_sha256':kernelsha,'payload_sha256':sha(phone/'payload.img'),'adt_sha256':sha(OUT/'kernel.macho.adt'),
        'board_sha256':sha(DEVICE/'board.toml'),'args':kernelargs,'owned_bytes':0x180000000,
        'control_image_sha256':control['image_sha256'],'fd_sha256':verification['fd_sha256'],'efi':verification['efi'],
        'retained_payload_inputs':retained,'compiled_sources':boot['sources'],
        'qemu_systemos_sha256':sha(qdir/'gdb-stop.json'),'qemu_memory':budget,
        'qemu_aks_hid_passed':True,'host_cache_transaction_passed':True,'host_pixel_test_passed':True,
        'phone_tested':False,'normal_data_writes_expected':True,
        'cache_refresh':'Opt-in before launchd: exclusive .venus-scale-001.bak renames of the three documented MG files; missing files skipped, errors reported',
        'scope':'Early chosen display-scale=2/rotation=0 plus retained MG-cache refresh; original FBS validation untouched. QEMU checkpoint is before Data/userspace, not a lockscreen result.'}
need(report['image_sha256']==verification['sha256'],'Image SHA mismatch')
if args.check:need(load(OUT/'candidate.json')==report,'Saved candidate differs')
else:
    (OUT/'candidate.json').write_text(json.dumps(report,indent=2)+'\n')
    (DEVICE/'evidence/lockscreen-scale-candidate.json').write_text(json.dumps(report,indent=2)+'\n')
os.sync()
print('PASS: current ADT generator, 6GiB firmware, compiled/tested cache helper, Data/trust, boot roundtrip, actual QEMU SystemOS/AKS/HID')
print('IMAGE:',report['image']);print('SHA256:',report['image_sha256']);print('KERNEL:',kernelsha)
