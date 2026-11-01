#!/usr/bin/env python3
"""Recheck the recovery image, original marker and compiled-source identities."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess
import tomllib

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out-name',default='venus-data-read-recovery-001')
options=parser.parse_args()
assert options.out_name.startswith('venus-data-read-recovery-') and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in options.out_name)
OUT=ROOT/'artifacts'/options.out_name
WORK=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(path):return json.loads(path.read_text())
candidate=load(OUT/'candidate.json');plan=load(ROOT/'artifacts/venus-data-check-001/plan.json')
assert candidate['original_marker']==plan and sha(OUT/'expected-marker.bin')==plan['file_sha256']
assert sha(OUT/'phone/boot-venus-unixnu.img')==candidate['image_sha256']==candidate['verification']['sha256']
assert sha(OUT/'phone/payload.img')==candidate['payload_sha256']
assert sha(OUT/'kernel/kernel.macho')==candidate['kernel_sha256']==sha(WORK/'kernel/kernel.macho')
assert candidate['read_phase_only'] and not candidate['marker_mutation_allowed']
assert sha(DEVICE/'board.toml')==candidate['board_sha256']
boot=load(WORK/'tree/build/boot-progress/build-report.json')
compiled={name:sha(DEVICE/'package/boot-progress'/name)
          for name in ('BootDataCheck.h','BootDataCheckCore.h','BootWatchdogPolicy.c','BootProgress.c')}
for name,digest in compiled.items():
    assert boot['sources'][name]==digest
    assert sha(ROOT/'artifacts/venus-data-check-001/linked-inputs'/name)==digest
    # Save the exact unchanged qualification code used in this kernel too.
    (OUT/'linked-inputs'/name).write_bytes((DEVICE/'package/boot-progress'/name).read_bytes())
build=load(OUT/'linked-inputs/data-publication-build.json')
assert sha(OUT/'linked-inputs/data-publication-build.json')==candidate['source_build_sha256']
assert build['kernel_sha256']==candidate['kernel_sha256']
assert sha(OUT/'linked-inputs/NativeRamBlock.o')==build['ram_block']['object_sha256']
assert sha(OUT/'linked-inputs/libRamBlock.a')==build['ram_block']['archive_sha256']
assert sha(OUT/'linked-inputs/publish-restored-view.patch')==build['ram_block']['patch_sha256']
if candidate.get('publication_deferred_until_systemos'):
    assert sha(OUT/'linked-inputs/publish-at-data-mount.patch')==build['ram_block']['deferred_patch_sha256']
    assert build['qemu_systemos_passed']
assert build['qemu_root_passed'] and build['qemu_services']['aks_state_passed'] and build['qemu_services']['hid_state_passed']
payload=OUT/'phone/payload.img'
def content(path):return subprocess.check_output(['mtype','-i',str(payload),'::/EFI/UniXNU/'+path])
assert hashlib.sha256(content('Payloads/kernel.macho')).hexdigest()==candidate['kernel_sha256']
assert hashlib.sha256(content('Payloads/kernel.macho.adt')).hexdigest()==candidate['adt_sha256']
actual=tomllib.loads(content('unixnu.toml').decode())['entry'][0]['args']
assert actual==candidate['args'];args=actual.split()
assert 'venus-data-check=2' in args and 'venus-data-token='+plan['token'] in args
assert len({a.split('=',1)[0] for a in args})==len(args)
assert not any(a.startswith(('sheng-data-reset=','sheng-autoreset=','sheng-log=')) for a in args)
assert {'sheng-data-persist=2','sheng-log-reserve=1024','sheng-gpu-power=0','sheng-fb-gpu=0'}<=set(args)
for name,digest in candidate['retained_inputs'].items():
    assert hashlib.sha256(content('Payloads/'+name)).hexdigest()==digest
assert candidate['verification']['roundtrip_verified'] and not candidate['verification']['uefi_memory_conflicts']
report={'device':'venus','date':'2026-10-28','image_sha256':candidate['image_sha256'],
        'candidate_sha256':sha(OUT/'candidate.json'),'kernel_sha256':candidate['kernel_sha256'],
        'original_marker_identity_preserved':True,'compiled_data_test_sources':compiled,
        'corrected_ram_block_object_verified':True,'payload_readback_verified':True,
        'retained_seed_trust_firmware_verified':True,'qemu_root_services_verified':True,
        'host_checks_passed':True,'phone_tested':False,
        'scope':'Recovery candidate host validation only; Data mount/file persistence not exercised in QEMU',
        'requires_user_return_and_exact_phone_operation_authorization':True}
evidence_name='data-read-recovery-check.json' if options.out_name=='venus-data-read-recovery-001' else options.out_name.removeprefix('venus-')+'-check.json'
(DEVICE/'evidence'/evidence_name).write_text(json.dumps(report,indent=2)+'\n')
print('PASS: original marker/full token, unchanged compiled file test, corrected disk object, image/payload/ADT and retained inputs')
print('READ recovery image SHA256:',candidate['image_sha256'])
