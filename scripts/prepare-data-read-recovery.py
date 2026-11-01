#!/usr/bin/env python3
"""Prepare a read-only marker recovery image with the corrected disk publisher.

Host packaging only. Uses the original failed test's complete token/path/content;
does not authorize any phone operation or replace the original paired images.
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
BUILD=Path('/root/unixnu-build/venus-legacy-full')
WORK=BUILD/'venus/ipados-17.7.11-21H461/venus_ufs_root'
ORIGINAL=ROOT/'artifacts/venus-data-check-001'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--kernel-sha256',required=True)
parser.add_argument('--out-name',default='venus-data-read-recovery-001')
parser.add_argument('--deferred',action='store_true',help='Use the post-SystemOS Data publication build and receipts')
args=parser.parse_args()
assert args.out_name.startswith('venus-data-read-recovery-') and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.out_name)
OUT=ROOT/'artifacts'/args.out_name
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(path):return json.loads(path.read_text())
def run(command):return subprocess.check_output([str(v) for v in command],timeout=240)
assert not OUT.exists(),'Preserve the existing recovery candidate'
assert sha(WORK/'kernel/kernel.macho')==args.kernel_sha256
build_reference=DEVICE/'evidence'/('data-deferred-publication-build.json' if args.deferred else 'data-publication-build.json')
build=load(build_reference)
assert build['kernel_sha256']==args.kernel_sha256 and build['qemu_root_passed']
assert build['qemu_services']['aks_state_passed'] and build['qemu_services']['hid_state_passed']
assert sha(DEVICE/'patches/ram-block/publish-restored-view.patch')==build['ram_block']['patch_sha256']
if args.deferred:
    assert build['qemu_systemos_passed']
    assert sha(DEVICE/'patches/ram-block/publish-at-data-mount.patch')==build['ram_block']['deferred_patch_sha256']
foundation=load(DEVICE/'evidence/stage-foundation.json')
assert sha(DEVICE/'board.toml')==foundation['board_after_sha256']
assert sha(BASE/'scripts/unixnu/devicetree.py')==foundation['active_converter_sha256']
plan=load(ORIGINAL/'plan.json');old=load(ORIGINAL/'candidate.json')
assert plan==old['plan']
assert sha(ORIGINAL/'read/boot-venus-unixnu.img')==old['images']['read']['sha256']
assert sha(ORIGINAL/'read/payload.img')==old['images']['read']['payload_sha256']
assert sha(ORIGINAL/'expected-marker.bin')==plan['file_sha256']
failed=load(DEVICE/'evidence/data-check-read-phone.json')
assert failed['manual_restart_confirmed'] and failed['observed']['rc']==2 and not failed['file_operation_passed']
sys.path.insert(0,str(BASE/'scripts'))
from unixnu.cli import parser as cli_parser
from unixnu.config import Context
from unixnu.devicetree import generate
ctx=Context(cli_parser().parse_args(['status','-D',str(DEVICE),'--out',str(BUILD)]))
base_args=ctx.board['payload']['kernel_args']
assert {'sheng-data-persist=2','sheng-log-reserve=1024','sheng-gpu-power=0','sheng-fb-gpu=0'}<=set(base_args)
assert not any(a.startswith(('venus-data-check=','venus-data-token=','sheng-data-reset=','sheng-autoreset=')) for a in base_args)
spec=importlib.util.spec_from_file_location('adt_codec',DEVICE/'scripts/inject-a660-firmware-adt.py')
codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
old_adt=(ORIGINAL/'kernel.macho.adt').read_bytes()
chip=int.from_bytes(dict(codec.find(codec.parse(old_adt),'chosen').props)['unique-chip-id'],'little')
adt=generate(ROOT/'artifacts/venus-stage-foundation/hardware/hardware.dtb',ctx.board,
             unique_chip_id=f'{chip:x}',data=True,trust=True)
def normalized(node):return (node.name,[(k,v) for k,v in node.props if k!='random-seed'],[normalized(n) for n in node.children])
assert normalized(codec.parse(adt))==normalized(codec.parse(old_adt))
OUT.mkdir();phone=OUT/'phone';phone.mkdir();kernel=OUT/'kernel';kernel.mkdir()
for name in ('kernel.macho','kernel.json'):shutil.copy2(WORK/'kernel'/name,kernel/name)
(OUT/'kernel.macho.adt').write_bytes(adt)
shutil.copy2(ORIGINAL/'expected-marker.bin',OUT/'expected-marker.bin')
shutil.copy2(ORIGINAL/'read/payload.img',phone/'payload.img')
for name in ('SILICIUM_UEFI.fd','UniXNU.efi','UniXNUX.efi','UniXNUDxe.efi','DarwinBoot.efi'):
    if (ORIGINAL/'read'/name).exists():shutil.copy2(ORIGINAL/'read'/name,phone/name)
kernel_args=' '.join([*base_args,'venus-data-check=2','venus-data-token='+plan['token'],'sheng-build-tag='+args.out_name.removeprefix('venus-')])
assert len(kernel_args.encode())<1000
config=('version = 1\n[boot]\ntimeout = 5\ndefault = "xnu"\n[kits]\nautoload = false\n'
        '[[entry]]\nid = "xnu"\ntitle = "Venus original Data marker readback"\ntype = "xnu"\n'
        'path = "Payloads/kernel.macho"\ninitrd = "Payloads/scratch-data.img"\nargs = "'+kernel_args+'"\n')
(phone/'unixnu.toml').write_text(config)
for local,target in ((kernel/'kernel.macho','Payloads/kernel.macho'),(OUT/'kernel.macho.adt','Payloads/kernel.macho.adt'),
                     (phone/'unixnu.toml','unixnu.toml')):
    run(['mcopy','-o','-i',phone/'payload.img',local,'::/EFI/UniXNU/'+target])
    assert run(['mtype','-i',phone/'payload.img','::/EFI/UniXNU/'+target])==local.read_bytes()
retained={}
for name in ('scratch-data.img','kernel.macho.trustcache'):
    content=run(['mtype','-i',phone/'payload.img','::/EFI/UniXNU/Payloads/'+name])
    assert content==run(['mtype','-i',ORIGINAL/'read/payload.img','::/EFI/UniXNU/Payloads/'+name])
    retained[name]=hashlib.sha256(content).hexdigest()
assert tomllib.loads(config)['entry'][0]['args']==kernel_args
run(['python3',ROOT/'tools/package-venus-uefi.py','--tree',ROOT/'ports/uefi-venus','--workspace',ROOT,
     '--artifacts',phone,'--payload',phone/'payload.img'])
verification=load(phone/'verification.json');control=load(ORIGINAL/'read/verification.json')
assert verification['roundtrip_verified'] and not verification['uefi_memory_conflicts']
assert verification['fd_sha256']==control['fd_sha256'] and verification['efi']==control['efi']
saved=OUT/'linked-inputs';saved.mkdir()
build_inputs=ROOT/('artifacts/venus-data-deferred-publication/linked-inputs' if args.deferred else 'artifacts/venus-data-publication/linked-inputs')
for name in ('NativeRamBlock.o','libRamBlock.a','build-report.json','compile-command.json','publish-restored-view.patch'):
    shutil.copy2(build_inputs/name,saved/name)
if args.deferred:shutil.copy2(build_inputs/'publish-at-data-mount.patch',saved/'publish-at-data-mount.patch')
shutil.copy2(build_reference,saved/'data-publication-build.json')
report={'device':'venus','serial':'55870427','date':'2026-10-28',
    'image':str(phone/'boot-venus-unixnu.img'),'image_sha256':sha(phone/'boot-venus-unixnu.img'),
    'image_bytes':verification['bytes'],'payload_sha256':sha(phone/'payload.img'),
    'kernel_sha256':args.kernel_sha256,'adt_sha256':sha(OUT/'kernel.macho.adt'),
    'board_sha256':sha(DEVICE/'board.toml'),'args':kernel_args,'original_marker':plan,
    'retained_inputs':retained,'source_build_sha256':sha(build_reference),
    'publication_deferred_until_systemos':args.deferred,
    'read_phase_only':True,'marker_mutation_allowed':False,'normal_persistent_data_mount':True,
    'phone_tested':False,'authorized':False,'automatic_reboot':False,
    'expected_success_row':'DATA CHECK phase=2 step=11 rc=0 match=1 bytes=53 token='+plan['token'][:8]+' store=2',
    'scope':'Read the original 53-byte marker using a restored-before-publication disk; no create/rewrite/delete. Normal APFS Data mount retains its existing persistent metadata behavior.',
    'verification':verification}
(OUT/'candidate.json').write_text(json.dumps(report,indent=2)+'\n')
evidence_name='data-read-recovery-candidate.json' if args.out_name=='venus-data-read-recovery-001' else args.out_name.removeprefix('venus-')+'-candidate.json'
(DEVICE/'evidence'/evidence_name).write_text(json.dumps(report,indent=2)+'\n')
print('Prepared original-marker readback image:',report['image'])
print('SHA256:',report['image_sha256'])
print('Phone test deferred until user returns; no phone operation performed')
