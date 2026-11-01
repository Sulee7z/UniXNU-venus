#!/usr/bin/env python3
"""Verify paired Data qualification images and preserve their compiled-source receipts."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[1]
WORK = Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
OUT = ROOT/'artifacts/venus-data-check-001'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text())


def need(ok,message):
    if not ok:raise SystemExit(message)


candidate = load(OUT/'candidate.json');plan = load(OUT/'plan.json')
need(plan==candidate['plan'],'Marker plan changed')
need(sha(OUT/'kernel/kernel.macho')==plan['kernel_sha256']==sha(WORK/'kernel/kernel.macho'),'Kernel changed')
need(sha(OUT/'expected-marker.bin')==plan['file_sha256'] and plan['file_bytes']==53,'Marker identity changed')
need(plan['file_path']=='/private/var/db/venus-data-check-'+plan['token']+'.bin','Unexpected target path')
need(sha(DEVICE/'board.toml')==candidate['board_sha256'],'Board changed since packaging')
need(sha(OUT/'kernel.macho.adt')==candidate['adt_sha256'],'Generated ADT changed')
boot = load(WORK/'tree/build/boot-progress/build-report.json')
sources = {}
for name in ('BootDataCheck.h','BootDataCheckCore.h','BootWatchdogPolicy.c','BootProgress.c'):
    sources[name] = sha(DEVICE/'package/boot-progress'/name)
    need(sources[name]==boot['sources'][name],'Compiled source receipt mismatch: '+name)
screen = load(ROOT/'artifacts/venus-a660-live-checks/screen-report.json')
need(screen['passed'] and screen['source_sha256']['BootProgress.c']==sources['BootProgress.c'],'Pixel test is stale')
core_log = ROOT/'logs/venus-data-check-core.log'
need('PASS: exclusive create, durable sync/reopen, reboot/readback, no phase2 writes' in core_log.read_text(),
     'Transaction core test did not pass')
qemu_dir = ROOT/'artifacts/venus-ufs-root/qemu-data-check-001'
qemu = load(qemu_dir/'gdb-stop.json')
need(sha(qemu_dir/'gdb-stop.json')==candidate['qemu_root_sha256'] and
     qemu['kernel_sha256']==plan['kernel_sha256'] and not qemu['bounded_timeout_interrupted'] and
     qemu['stop_symbol']=='_native_owner_root_accepted_checkpoint','Root control mismatch')
need(candidate['qemu_services']['aks_state_passed'] and candidate['qemu_services']['hid_state_passed'],'OS service control failed')
for phase,label in ((1,'write'),(2,'read')):
    row = candidate['images'][label];phone = OUT/label
    need(sha(phone/'boot-venus-unixnu.img')==row['sha256'],'Image changed: '+label)
    need(sha(phone/'payload.img')==row['payload_sha256'],'Payload changed: '+label)
    args = row['args'].split()
    need(f'venus-data-check={phase}' in args and 'venus-data-token='+plan['token'] in args,'Phase/token mismatch')
    need('sheng-gpu-power=0' in args and 'sheng-fb-gpu=0' in args and 'sheng-log-reserve=1024' in args,
         'Wrong prerequisite-stage baseline')
    need(not any(a.startswith(('sheng-data-reset=','sheng-autoreset=','sheng-log=')) for a in args),
         'Unexpected reset/log gate')
    need(load(phone/'verification.json')['roundtrip_verified'],'Container did not round-trip')
    data = subprocess.check_output(['mtype','-i',str(phone/'payload.img'),'::/EFI/UniXNU/Payloads/kernel.macho.adt'])
    need(hashlib.sha256(data).hexdigest()==candidate['adt_sha256'],'Phase ADTs differ')
    need(row['retained_inputs']['scratch-data.img']=='ca732abdafa194ceb1d1ede1b20f930374180d238da6f74ebb00a2caa4c6fb33',
         'Data seed changed')
symbols = subprocess.check_output(['/usr/bin/llvm-nm',str(OUT/'kernel/kernel.macho')],text=True)
for name in ('_venus_data_check_phase','_venus_data_check_stage','_venus_data_check_status',
             '_venus_data_check_matched','_venus_data_check_row','_native_ufs_store_mode'):
    need(any(line.split()[-1:]==[name] and int(line.split()[0],16) for line in symbols.splitlines()),'Missing linked symbol: '+name)
snapshots = OUT/'linked-inputs';snapshots.mkdir(exist_ok=True)
for name in sources:shutil.copy2(DEVICE/'package/boot-progress'/name,snapshots/name)
shutil.copy2(WORK/'tree/build/boot-progress/build-report.json',snapshots/'boot-progress-report.json')
shutil.copy2(WORK/'tree/build/boot-progress/libBootProgress.a',snapshots/'libBootProgress.a')
shutil.copy2(DEVICE/'tests/data_check_core.c',snapshots/'data_check_core.c')
shutil.copy2(core_log,snapshots/'core-test.log')
shutil.copy2(ROOT/'artifacts/venus-a660-live-checks/screen-report.json',snapshots/'screen-report.json')
report = {'device':'venus','date':'2026-10-28','plan':plan,'images':candidate['images'],
          'candidate_sha256':sha(OUT/'candidate.json'),'adt_sha256':candidate['adt_sha256'],
          'compiled_sources':sources,'transaction_test_log_sha256':sha(core_log),
          'transaction_test_source_sha256':sha(DEVICE/'tests/data_check_core.c'),
          'screen_regression':screen,'qemu_root_passed':True,'qemu_services':candidate['qemu_services'],
          'scope':'Host checks of exclusive write/sync/reopen and reboot/read-only comparison; bounded post-Data-mount kernel adapter compiled; no actual phone persistence result yet',
          'phone_write_phase_passed':False,'phone_read_phase_passed':False,
          'requires_phase1_success_and_manual_restart_before_phase2':True}
(DEVICE/'evidence/data-check-candidate.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: source receipts, marker identity, paired images, fixed result row, core failure controls and QEMU baseline')
print('WRITE:',candidate['images']['write']['sha256'])
print('READ: ',candidate['images']['read']['sha256'])
