#!/usr/bin/env python3
"""Build paired Data-file write/read images from the corrected board baseline.

Host packaging only. Each phone operation needs its exact-image authorization.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tomllib

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[1]
BASE = Path('/root/unixnu-build/UniXNU-sheng-base')
BUILD = Path('/root/unixnu-build/venus-legacy-full')
WORK = BUILD/'venus/ipados-17.7.11-21H461/venus_ufs_root'
CONTROL = ROOT/'artifacts/venus-legacy/full-phone'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--kernel-sha256',required=True)
parser.add_argument('--out-name',default='venus-data-check-001')
options = parser.parse_args()
if not options.out_name.startswith('venus-data-check-') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in options.out_name):
    parser.error('Expected a venus-data-check-* output directory name')
OUT = ROOT/'artifacts'/options.out_name


def need(ok,message):
    if not ok:
        raise SystemExit(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text())


def run(command,**kw):
    return subprocess.check_output([str(x) for x in command],**kw)


need(not OUT.exists(),'Output already exists; preserve any partial/tested artifacts')
need(sha(WORK/'kernel/kernel.macho')==options.kernel_sha256,'Kernel identity changed')
sync_check=load(DEVICE/'evidence/data-sync-contract-host.json')
boot_build=load(WORK/'tree/build/boot-progress/build-report.json')
need(sync_check['passed'] and sync_check['sync_contract']==2,'Run current durable transaction checks first')
for name,digest in sync_check['sources'].items():
    need(sha(DEVICE/'package/boot-progress'/name)==digest==boot_build['sources'][name],'Transaction source/compile/test mismatch: '+name)
need(sha(CONTROL/'boot-venus-unixnu.img')=='28051b5a09fc7ff875d11202cd179173a0b30f40272a765937e92d0eb0d037f0','Control image changed')
control = load(CONTROL/'verification.json')
need(sha(CONTROL/'payload.img')==control['ramdisk_sha256'],'Control payload changed')
foundation = load(DEVICE/'evidence/stage-foundation.json')
need(sha(DEVICE/'board.toml')==foundation['board_after_sha256'],'Board no longer matches foundation checks')
need(sha(BASE/'scripts/unixnu/devicetree.py')==foundation['active_converter_sha256'],'Active ADT converter changed')
sys.path.insert(0,str(BASE/'scripts'))
from unixnu.cli import parser as cli_parser
from unixnu.config import Context
from unixnu.devicetree import generate
ctx = Context(cli_parser().parse_args(['status','-D',str(DEVICE),'--out',str(BUILD)]))
need(ctx.config_name=='venus_ufs_root_defconfig','Wrong selected configuration')
base_args = ctx.board['payload']['kernel_args']
need({'cpus=1','sheng-gpu-power=0','sheng-fb-gpu=0','sheng-data-persist=2','sheng-log-reserve=1024'}<=set(base_args),
     'Qualification baseline gates differ')
need(not any(a.startswith(('venus-data-check=','venus-data-token=','sheng-build-tag=')) for a in base_args),
     'Per-run arguments already exist in board defaults')
OUT.mkdir()
kernel = OUT/'kernel';kernel.mkdir()
for name in ('kernel.macho','kernel.json'):
    shutil.copy2(WORK/'kernel'/name,kernel/name)
spec = importlib.util.spec_from_file_location('adt_codec',DEVICE/'scripts/inject-a660-firmware-adt.py')
adt_codec = importlib.util.module_from_spec(spec);spec.loader.exec_module(adt_codec)
control_adt = run(['mtype','-i',CONTROL/'payload.img','::/EFI/UniXNU/Payloads/kernel.macho.adt'])
chosen = dict(adt_codec.find(adt_codec.parse(control_adt),'chosen').props)
identity = int.from_bytes(chosen['unique-chip-id'],'little')
adt = generate(ROOT/'artifacts/venus-stage-foundation/hardware/hardware.dtb',ctx.board,
               unique_chip_id=f'{identity:x}',data=True,trust=True)
def normalize(node):
    return (node.name,[(k,v) for k,v in node.props if k!='random-seed'],[normalize(n) for n in node.children])
need(normalize(adt_codec.parse(adt))==normalize(adt_codec.parse((ROOT/'artifacts/venus-stage-foundation/kernel.macho.adt').read_bytes())),
     'Board-generated ADT differs from the foundation check')
(OUT/'kernel.macho.adt').write_bytes(adt)

# Generate the exact path/content through the same C core used by the kernel.
token = secrets.token_hex(16)
source = OUT/'marker-inputs.c'
source.write_text('#include <stdio.h>\n#include "BootDataCheckCore.h"\n'
    'int main(int argc,char **argv){char path[VdcPathBytes],data[VdcContentBytes];'
    'if(argc!=2||vdc_inputs(argv[1],path,data))return 1;puts(path);'
    'return fwrite(data,1,sizeof(data),stdout)==sizeof(data)?0:2;}\n')
run(['gcc','-std=c11','-D_POSIX_C_SOURCE=200809L','-I',DEVICE/'package/boot-progress',source,'-o',OUT/'marker-inputs'])
path,content = run([OUT/'marker-inputs',token]).split(b'\n',1)
need(len(content)==53,'Unexpected marker length')
plan = {'device':'venus','serial':'55870427','kernel_sha256':options.kernel_sha256,
        'token':token,'file_path':path.decode(),'file_bytes':len(content),
        'file_sha256':hashlib.sha256(content).hexdigest(),'content_ascii':content.decode(),
        'owned_memory_bytes':0x40000000,'data_store_first_lba':59299519,
        'sync_contract':2,'parent_path':'/private/var/db','require_file_and_parent_on_mounted_data_device':True,
        'phase1':'exclusive openat/write/fsync/parent-fsync/F_FULLFSYNC/UFS-sync/close/reopen/read/compare; require persisted writes; then wait before launchd',
        'phase2':'require resumed store and parent/file device identity; openat/read/compare existing file only; then wait before launchd',
        'automatic_reboot':False,'phone_tested':False}
(OUT/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
(OUT/'expected-marker.bin').write_bytes(content)

images = {}
for phase,label in ((1,'write'),(2,'read')):
    phone = OUT/label;phone.mkdir()
    shutil.copy2(CONTROL/'payload.img',phone/'payload.img')
    for name in ('SILICIUM_UEFI.fd','UniXNU.efi','UniXNUX.efi','UniXNUDxe.efi','DarwinBoot.efi'):
        if (CONTROL/name).exists():shutil.copy2(CONTROL/name,phone/name)
    args = ' '.join([*base_args,f'venus-data-check={phase}',f'venus-data-token={token}',f'sheng-build-tag={options.out_name.removeprefix("venus-")}-{label}'])
    need(len(args.encode())<1000,'Kernel command-line budget exceeded')
    config = ('version = 1\n[boot]\ntimeout = 5\ndefault = "xnu"\n[kits]\nautoload = false\n'
        '[[entry]]\nid = "xnu"\ntitle = "Venus Data '+label+' qualification"\ntype = "xnu"\n'
        'path = "Payloads/kernel.macho"\ninitrd = "Payloads/scratch-data.img"\nargs = "'+args+'"\n')
    (phone/'unixnu.toml').write_text(config)
    for local,target in ((kernel/'kernel.macho','Payloads/kernel.macho'),(OUT/'kernel.macho.adt','Payloads/kernel.macho.adt'),
                         (phone/'unixnu.toml','unixnu.toml')):
        run(['mcopy','-o','-i',phone/'payload.img',local,'::/EFI/UniXNU/'+target])
        need(run(['mtype','-i',phone/'payload.img','::/EFI/UniXNU/'+target])==local.read_bytes(),'Payload readback mismatch: '+target)
    retained = {}
    for name in ('scratch-data.img','kernel.macho.trustcache'):
        before = run(['mtype','-i',CONTROL/'payload.img','::/EFI/UniXNU/Payloads/'+name])
        after = run(['mtype','-i',phone/'payload.img','::/EFI/UniXNU/Payloads/'+name])
        need(before==after,'Data seed/trustcache changed')
        retained[name] = hashlib.sha256(after).hexdigest()
    actual = tomllib.loads(run(['mtype','-i',phone/'payload.img','::/EFI/UniXNU/unixnu.toml']).decode())
    need(actual['entry'][0]['args']==args,'Boot arguments changed')
    run(['python3',ROOT/'tools/package-venus-uefi.py','--tree',ROOT/'ports/uefi-venus','--workspace',ROOT,
         '--artifacts',phone,'--payload',phone/'payload.img'],timeout=180)
    verification = load(phone/'verification.json')
    need(verification['roundtrip_verified'] and not verification['uefi_memory_conflicts'],'Container validation failed')
    need(verification['fd_sha256']==control['fd_sha256'] and verification['efi']==control['efi'],'Firmware changed')
    images[label] = {'image':str(phone/'boot-venus-unixnu.img'),'sha256':sha(phone/'boot-venus-unixnu.img'),
                     'bytes':verification['bytes'],'payload_sha256':sha(phone/'payload.img'),
                     'args':args,'retained_inputs':retained,'phone_tested':False}

qemu_name = 'qemu-'+options.out_name.removeprefix('venus-')
command = ['python3',DEVICE/'scripts/test-venus-root-mount.py','--kernel',kernel/'kernel.macho',
    '--prelink-report',kernel/'kernel.json','--owned-memory-size','0x40000000','--qemu-memory-mib','2048',
    '--inspect-memory-budget','--inspect-os-services','--systemos-checkpoint','--out-name',qemu_name]
for arg in base_args:
    if arg.startswith(('offline-legacy-','offline-mobile-graphics-','offline-key-events=',
                       'offline-hid-','sheng-aks=','sheng-gpu-power=','sheng-fb-gpu=',
                       'sheng-vsync=','boot-progress=')):
        command += ['--extra-kernel-arg='+arg]
run(command,timeout=600)
qemu_dir = ROOT/'artifacts/venus-ufs-root'/qemu_name
qemu = load(qemu_dir/'gdb-stop.json')
need(qemu['kernel_sha256']==options.kernel_sha256 and not qemu['bounded_timeout_interrupted'] and
     qemu['stop_symbol']=='_native_owner_cache_checkpoint','QEMU SystemOS control failed')
report = {'plan':plan,'images':images,'adt_sha256':sha(OUT/'kernel.macho.adt'),
          'board_sha256':sha(DEVICE/'board.toml'),'foundation_report_sha256':sha(DEVICE/'evidence/stage-foundation.json'),
          'packager_sha256':sha(Path(__file__)),'qemu_root':str(qemu_dir/'gdb-stop.json'),
          'qemu_root_sha256':sha(qemu_dir/'gdb-stop.json'),'qemu_services':load(qemu_dir/'os-services.json'),
          'qemu_data_file_operation_exercised':False,'qemu_systemos_passed':True,'phone_tested':False,
          'requires_exact_operation_authorization':True}
(OUT/'candidate.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
