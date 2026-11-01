#!/usr/bin/env python3
"""Prepare a normal CPU-display boot from the exact phone-qualified Data pair.

Only the payload menu configuration changes. This does not run phone commands.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
BASE=Path('/root/unixnu-build/UniXNU-sheng-base')
WORK=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
CONTROL=ROOT/'artifacts/venus-data-check-002'
OUT=ROOT/'artifacts/venus-userspace-001'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check',action='store_true',help='Recheck existing packaged artifacts without rebuilding them')
options=parser.parse_args()
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def need(condition,why):
    if not condition:raise SystemExit(why)
def run(argv):return subprocess.check_output([str(v) for v in argv],timeout=240)
def payload(image,name):return run(['mtype','-i',image,'::/EFI/UniXNU/'+name])

qualified=load(DEVICE/'evidence/data-persistence-qualified.json')
control=load(CONTROL/'candidate.json');verification=load(CONTROL/'read/verification.json')
need(qualified['passed'] and qualified['kernel_sha256']==control['plan']['kernel_sha256'],'Data baseline not qualified')
for label,row in qualified['records'].items():
    need(sha(DEVICE/row['reference'])==row['record_sha256'],'Phone evidence changed: '+label)
    need(sha(CONTROL/label/'boot-venus-unixnu.img')==row['image_sha256'],'Control image changed: '+label)
need(sha(WORK/'kernel/kernel.macho')==qualified['kernel_sha256'],'Current kernel differs from the qualified Data kernel')
need(sha(CONTROL/'read/payload.img')==control['images']['read']['payload_sha256'],'Control payload changed')
board=tomllib.loads((DEVICE/'board.toml').read_text())
need(sha(DEVICE/'board.toml')==control['board_sha256'],'Board changed since Data qualification')
boot=load(CONTROL/'linked-inputs/boot-progress-report.json')
for name in ('BootDataCheck.h','BootDataCheckCore.h','BootWatchdogPolicy.c','BootProgress.c'):
    need(sha(DEVICE/'package/boot-progress'/name)==boot['sources'][name],'Current boot source differs from qualified kernel: '+name)
data_source=(DEVICE/'package/boot-progress/BootDataCheck.h').read_text()
need('!PE_parse_boot_argn("venus-data-check",&phase,sizeof(phase))||!phase)return;' in data_source,
     'Review the default-off Data gate before normal boot')
args=board['payload']['kernel_args']
need(len(args)==len({a.split('=',1)[0] for a in args}),'Duplicate board arguments')
need({'sheng-data-persist=2','sheng-log-reserve=1024','offline-legacy-cpu-present=1',
      'sheng-gpu-power=0','sheng-fb-gpu=0','offline-key-events=1','sheng-aks=1',
      'offline-hid-input=1','offline-hid-home=1'}<=set(args),'Normal CPU-display baseline changed')
need(not any(a.startswith(('venus-data-check=','venus-data-token=','sheng-build-tag=',
                          'sheng-data-reset=','sheng-autoreset=','sheng-setup=')) for a in args),'Unexpected test/reset argument')
control_args=control['images']['read']['args'].split()
removed=[a for a in control_args if a.startswith(('venus-data-check=','venus-data-token=','sheng-build-tag='))]
need([a for a in control_args if a not in removed]==args,'Normal board args differ beyond test gate/tag')
kernel_args=' '.join([*args,'sheng-build-tag=userspace-001'])
need(len(kernel_args.encode())<1000,'Boot arguments exceed the qualified budget')

# Re-generate for comparison using the current board/converter. Retain the
# exact proven sidecar bytes (including its random seed) in this A/B candidate.
foundation=load(DEVICE/'evidence/stage-foundation.json')
need(sha(BASE/'scripts/unixnu/devicetree.py')==foundation['active_converter_sha256'],'ADT converter changed')
sys.path.insert(0,str(BASE/'scripts'))
from unixnu.cli import parser as cli_parser
from unixnu.config import Context
from unixnu.devicetree import generate
ctx=Context(cli_parser().parse_args(['status','-D',str(DEVICE),'--out',str(WORK.parents[2])]))
need(ctx.config_name=='venus_ufs_root_defconfig','Wrong selected configuration')
spec=importlib.util.spec_from_file_location('codec',DEVICE/'scripts/inject-a660-firmware-adt.py')
codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
adt=(CONTROL/'kernel.macho.adt').read_bytes()
chip=int.from_bytes(dict(codec.find(codec.parse(adt),'chosen').props)['unique-chip-id'],'little')
generated=generate(ROOT/'artifacts/venus-stage-foundation/hardware/hardware.dtb',ctx.board,
                   unique_chip_id=f'{chip:x}',data=True,trust=True)
def normal(node):return(node.name,[(k,v) for k,v in node.props if k!='random-seed'],[normal(c) for c in node.children])
need(normal(codec.parse(adt))==normal(codec.parse(generated)),'Current generated ADT differs from qualified hardware input')
qemu=load(Path(control['qemu_root']))
need(sha(Path(control['qemu_root']))==control['qemu_root_sha256'] and
     qemu['kernel_sha256']==qualified['kernel_sha256'] and qemu['stop_symbol']=='_native_owner_cache_checkpoint' and
     not qemu['bounded_timeout_interrupted'] and qemu['owner_cache_mount']['_native_owner_cache_status']==0,
     'Same-kernel SystemOS QEMU evidence changed')

phone=OUT/'phone'
if not options.check:
    need(not OUT.exists(),'Output already exists; preserve the candidate')
    OUT.mkdir();phone.mkdir();(OUT/'kernel').mkdir();(OUT/'linked-inputs').mkdir()
    for name in ('kernel.macho','kernel.json'):shutil.copy2(CONTROL/'kernel'/name,OUT/'kernel'/name)
    shutil.copy2(CONTROL/'kernel.macho.adt',OUT/'kernel.macho.adt')
    shutil.copy2(CONTROL/'read/payload.img',phone/'payload.img')
    for name in ('SILICIUM_UEFI.fd','UniXNU.efi','UniXNUX.efi','UniXNUDxe.efi','DarwinBoot.efi'):
        if (CONTROL/'read'/name).exists():shutil.copy2(CONTROL/'read'/name,phone/name)
    config=('version = 1\n[boot]\ntimeout = 5\ndefault = "xnu"\n[kits]\nautoload = false\n'
            '[[entry]]\nid = "xnu"\ntitle = "Mi 11 iPadOS CPU system boot"\ntype = "xnu"\n'
            'path = "Payloads/kernel.macho"\ninitrd = "Payloads/scratch-data.img"\nargs = "'+kernel_args+'"\n')
    (phone/'unixnu.toml').write_text(config)
    run(['mcopy','-o','-i',phone/'payload.img',phone/'unixnu.toml','::/EFI/UniXNU/unixnu.toml'])
    run(['python3',ROOT/'tools/package-venus-uefi.py','--tree',ROOT/'ports/uefi-venus','--workspace',ROOT,
         '--artifacts',phone,'--payload',phone/'payload.img'])
    for name in ('BootDataCheck.h','BootDataCheckCore.h','BootWatchdogPolicy.c','BootProgress.c','boot-progress-report.json',
                 'ram-build-report.json','publish-restored-view.patch','publish-at-data-mount.patch'):
        shutil.copy2(CONTROL/'linked-inputs'/name,OUT/'linked-inputs'/name)
    shutil.copy2(DEVICE/'evidence/data-persistence-qualified.json',OUT/'linked-inputs/data-persistence-qualified.json')
    shutil.copy2(Path(control['qemu_root']),OUT/'linked-inputs/qemu-systemos.json')

retained={}
for name in ('kernel.macho','kernel.macho.adt','scratch-data.img','kernel.macho.trustcache'):
    data=payload(phone/'payload.img','Payloads/'+name)
    need(data==payload(CONTROL/'read/payload.img','Payloads/'+name),'Payload input changed: '+name)
    retained[name]=hashlib.sha256(data).hexdigest()
actual_config=payload(phone/'payload.img','unixnu.toml')
need(actual_config==(phone/'unixnu.toml').read_bytes(),'Boot configuration readback differs')
need(tomllib.loads(actual_config.decode())['entry'][0]['args']==kernel_args,'Wrong normal-boot arguments')
current=load(phone/'verification.json')
need(current['roundtrip_verified'] and not current['uefi_memory_conflicts'],'Boot container verification failed')
need(current['fd_sha256']==verification['fd_sha256'] and current['efi']==verification['efi'],'Firmware changed')
need(sha(phone/'boot-venus-unixnu.img')==current['sha256'],'Final image differs from its roundtrip record')
report={'device':'venus','serial':'55870427','date':'2026-10-28',
        'image':str(phone/'boot-venus-unixnu.img'),'image_sha256':current['sha256'],'image_bytes':current['bytes'],
        'payload_sha256':sha(phone/'payload.img'),'kernel_sha256':qualified['kernel_sha256'],
        'adt_sha256':sha(OUT/'kernel.macho.adt'),'board_sha256':sha(DEVICE/'board.toml'),
        'args':kernel_args,'removed_control_args':removed,'added_args':['sheng-build-tag=userspace-001'],
        'retained_payload_inputs':retained,'firmware_sha256':current['fd_sha256'],
        'data_qualification_passed':True,'data_qualification_sha256':sha(DEVICE/'evidence/data-persistence-qualified.json'),
        'qemu_systemos_same_kernel_verified':True,'qemu_systemos_sha256':control['qemu_root_sha256'],
        'normal_launchd_path_enabled':True,'cpu_display_enabled':True,'phone_tested':False,
        'normal_data_and_userspace_writes_expected':True,
        'scope':'Normal iPadOS launchd/CPU-display attempt using the exact Data-qualified kernel/ADT/seed/trust/firmware; no claim of an already working UI'}
if not options.check:(OUT/'candidate.json').write_text(json.dumps(report,indent=2)+'\n')
else:need(load(OUT/'candidate.json')==report,'Saved normal-boot candidate no longer matches inputs')
(DEVICE/'evidence/userspace-candidate.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: normal launchd arguments; exact qualified payload inputs and firmware retained; current ADT generation matches')
print('BOOT:',report['image'])
print('SHA256:',report['image_sha256'])
