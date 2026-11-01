#!/usr/bin/env python3
"""Bind the new durable paired Data candidate to kernel, test and source receipts."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tomllib
DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
WORK=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
OUT=ROOT/'artifacts/venus-data-check-002'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(p.read_text())
candidate=load(OUT/'candidate.json');plan=load(OUT/'plan.json')
assert candidate['plan']==plan and plan['sync_contract']==2
assert sha(OUT/'kernel/kernel.macho')==plan['kernel_sha256']==sha(WORK/'kernel/kernel.macho')
assert sha(OUT/'expected-marker.bin')==plan['file_sha256'] and plan['file_bytes']==53
assert plan['token']!=load(ROOT/'artifacts/venus-data-check-001/plan.json')['token']
assert plan['file_path']=='/private/var/db/venus-data-check-'+plan['token']+'.bin'
host=load(DEVICE/'evidence/data-sync-contract-host.json');assert host['passed']
boot=load(WORK/'tree/build/boot-progress/build-report.json')
screen=load(ROOT/'artifacts/venus-a660-live-checks/screen-report.json')
assert screen['passed'] and screen['source_sha256']['BootProgress.c']==sha(DEVICE/'package/boot-progress/BootProgress.c')
saved=OUT/'linked-inputs';saved.mkdir(exist_ok=True)
sources={}
for name in ('BootDataCheck.h','BootDataCheckCore.h','BootWatchdogPolicy.c','BootProgress.c'):
    sources[name]=sha(DEVICE/'package/boot-progress'/name)
    assert sources[name]==boot['sources'][name]
    if name in host['sources']:assert sources[name]==host['sources'][name]
    shutil.copy2(DEVICE/'package/boot-progress'/name,saved/name)
for src,name in ((WORK/'tree/build/boot-progress/build-report.json','boot-progress-report.json'),
                 (WORK/'tree/build/boot-progress/libBootProgress.a','libBootProgress.a'),
                 (DEVICE/'tests/data_check_core.c','data_check_core.c'),
                 (DEVICE/'evidence/data-sync-contract-host.json','data-sync-contract-host.json'),
                 (ROOT/'artifacts/venus-a660-live-checks/screen-report.json','screen-report.json')):
    shutil.copy2(src,saved/name)
ram=WORK/'tree/build/venus-ram-block';ram_report=load(ram/'build-report.json')
assert ram_report['publication_phase']=='original Data selection after SystemOS'
for name in ('NativeRamBlock.o','libRamBlock.a','build-report.json','compile-command.json'):
    shutil.copy2(ram/name,saved/('ram-'+name))
assert sha(ram/'NativeRamBlock.o')==sha(WORK/'tree/build/ram-block/NativeRamBlock.o')==ram_report['object_sha256']
for name,key in (('publish-restored-view.patch','patch_sha256'),('publish-at-data-mount.patch','deferred_patch_sha256')):
    assert sha(DEVICE/'patches/ram-block'/name)==ram_report[key]
    shutil.copy2(DEVICE/'patches/ram-block'/name,saved/name)
for phase,label in ((1,'write'),(2,'read')):
    phone=OUT/label;image=candidate['images'][label]
    assert sha(phone/'boot-venus-unixnu.img')==image['sha256']
    assert sha(phone/'payload.img')==image['payload_sha256']
    def payload(path):return subprocess.check_output(['mtype','-i',str(phone/'payload.img'),'::/EFI/UniXNU/'+path])
    assert hashlib.sha256(payload('Payloads/kernel.macho')).hexdigest()==plan['kernel_sha256']
    assert hashlib.sha256(payload('Payloads/kernel.macho.adt')).hexdigest()==candidate['adt_sha256']
    argv=tomllib.loads(payload('unixnu.toml').decode())['entry'][0]['args']
    assert argv==image['args'];args=argv.split()
    assert {'venus-data-check='+str(phase),'venus-data-token='+plan['token'],'sheng-data-persist=2','sheng-log-reserve=1024'}<=set(args)
    assert len({a.split('=',1)[0] for a in args})==len(args)
    assert not any(a.startswith(('sheng-data-reset=','sheng-autoreset=','sheng-log=')) for a in args)
    assert image['retained_inputs']['scratch-data.img']=='ca732abdafa194ceb1d1ede1b20f930374180d238da6f74ebb00a2caa4c6fb33'
    for name,digest in image['retained_inputs'].items():assert hashlib.sha256(payload('Payloads/'+name)).hexdigest()==digest
    assert load(phone/'verification.json')['roundtrip_verified']
qemu=load(Path(candidate['qemu_root']))
assert sha(Path(candidate['qemu_root']))==candidate['qemu_root_sha256']
assert qemu['kernel_sha256']==plan['kernel_sha256'] and qemu['stop_symbol']=='_native_owner_cache_checkpoint' and not qemu['bounded_timeout_interrupted']
assert qemu['owner_cache_mount']['_native_owner_cache_status']==0 and candidate['qemu_services']['aks_state_passed'] and candidate['qemu_services']['hid_state_passed']
report={'device':'venus','date':'2026-10-28','plan':plan,'images':candidate['images'],
        'candidate_sha256':sha(OUT/'candidate.json'),'compiled_sources':sources,'ram_block':ram_report,
        'host_transaction_passed':True,'pixel_rows_passed':True,'qemu_systemos_passed':True,'phone_tested':False,
        'files':{p.name:sha(p) for p in saved.iterdir() if p.is_file()},
        'scope':'New token and durable file transaction compile/model/rows, current post-SystemOS disk provider, paired payload readback and real SystemOS QEMU; no phone Data-file claim'}
(DEVICE/'evidence/data-sync-candidate.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: durable paired candidate, parent/file identity adapter, source receipts, exact payload and SystemOS control')
print('WRITE',candidate['images']['write']['sha256']);print('READ',candidate['images']['read']['sha256'])
