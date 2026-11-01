#!/usr/bin/env python3
"""Package documented MG invalidation with durable begin/end and original chain."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
OUT=ROOT/'artifacts/venus-scale-refresh-011';CONTROL=ROOT/'artifacts/venus-sheng-chain-010'
KERNEL=OUT/'refresh-link-2';BASELINE=ROOT/'artifacts/venus-mg-query-009/baseline-link-4'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
parser.add_argument('--version',choices=('011','012'),default='011');args=parser.parse_args()
VERSION=args.version
if VERSION=='012':OUT=ROOT/'artifacts/venus-scale-refresh-012';KERNEL=OUT/'refresh-link-3'
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(path):return json.loads(path.read_text())
def need(ok,why):
    if not ok:raise ValueError(why)
def run(command):return subprocess.check_output([str(x) for x in command],timeout=240)
def fat(image,path):return run(['mtype','-i',image,'::/EFI/UniXNU/'+path])
def members(archive):
    names=run(['xcrun','ar','t',archive]).decode().splitlines();need(len(names)==len(set(names)),'Ambiguous archive members')
    return {n:hashlib.sha256(run(['xcrun','ar','p',archive,n])).hexdigest() for n in names}
control=load(CONTROL/'candidate.json');tests=load(OUT/'host-tests-r3/report.json');build=load(KERNEL/'report.json')
need(tests['passed'],'Host transaction tests failed')
for name,digest in tests['sources'].items():
    need(sha(DEVICE/'package/boot-progress'/name)==digest==sha(KERNEL/name),'Build/test/source differ: '+name)
need(sha(CONTROL/'phone/boot-venus-unixnu.img')==control['image_sha256']=='5f9061214acfd829ec893af61904d438844e1fb4ae584122565360653fb9a57d','010 changed')
qdir=ROOT/'artifacts/venus-ufs-root'/('qemu-scale-refresh012-systemos-r3' if VERSION=='012' else 'qemu-scale-refresh011-systemos')
q=load(qdir/'gdb-stop.json');services=load(qdir/'os-services.json');budget=load(qdir/'memory-budget.json')
need(q['kernel_sha256']==sha(KERNEL/'kernel.macho') and not q['bounded_timeout_interrupted'] and
     q['owner_cache_mount']['_native_owner_cache_status']==0 and budget['_max_mem']==0x180000000 and
     services['aks_state_passed'] and services['hid_state_passed'],'Actual QEMU SystemOS/services failed')
data=load(OUT/('qemu-data-checkpoint-r3' if VERSION=='012' else 'qemu-data-checkpoint')/'result.json')
need(data['passed'] and data['kernel_sha256']==sha(KERNEL/'kernel.macho') and data['state']['_native_owner_data_stage']==4,'Actual post-Data checkpoint failed')
if VERSION=='011':need(data['state']['_venus_scale011_journal_status']==5 and data['state']['_venus_gestalt_requested']==0 and data['state']['_venus_gestalt_moved']==0,'Sync refusal guard failed')
else:need(data['state']['_venus_gestalt_moved']==1 and data['state']['_venus_gestalt_missing']==6 and data['state']['_venus_gestalt_status']==5 and data['state']['_venus_scale012_source_uid']==4294967294,'Actual captured-cache APFS rename failed')
old=members(BASELINE/'libBootProgress.a');new=members(KERNEL/'libBootProgress.a')
need(old.keys()==new.keys() and [n for n in old if old[n]!=new[n]]==['BootWatchdogPolicy.o'],'Unexpected boot member change')
need(members(BASELINE/'libNativeLegacyDisplay.late.a')==members(KERNEL/'libNativeLegacyDisplay.late.a'),'Display changed from rebuilt control')
need(load(BASELINE/'report.json')['kernel_objects_archive_sha256']==build['kernel_objects_archive_sha256'],'Kernel object archive changed')
tree=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root/tree')
need(sha(tree/'build/ram-block/NativeRamBlock.o')==sha(ROOT/'artifacts/venus-data-check-002/linked-inputs/ram-NativeRamBlock.o'),'Qualified RamBlock changed')
sys.path.insert(0,str(DEVICE/'scripts'));import data_store_view as store
snapshot=ROOT/'artifacts/venus-data-forensics'/('read-20261029T074228Z' if VERSION=='012' else 'read-20261029T063818Z')
view,apfs,volume=store.open_volume(snapshot,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT)
paths=['/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist',
       '/private/var/mobile/Library/Preferences/com.apple.MobileGestalt.plist',
       '/private/var/mobile/Library/Preferences/com.apple.mobilegestalt.plist']
try:
    present=[]
    for path in paths:
        try:
            content=store.read_file(view,apfs,volume,path);present.append({'path':path,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
        except ValueError as error:
            need('has 0 directory records' in str(error),'Source file error: '+str(error));present.append({'path':path,'absent':True})
        target=('/private/var/db/venus-scale-012/cache-'+str(len(present)-1)+'.plist') if VERSION=='012' else path+'.venus-scale-011.bak'
        try:store.file_info(apfs,volume,target)
        except ValueError as error:need('has 0 directory records' in str(error),'Backup file error')
        else:raise ValueError('Backup already exists')
    journal='/private/var/db/venus-scale-012/refresh.jsonl' if VERSION=='012' else '/tmp/venus-scale-011.jsonl'
    try:store.file_info(apfs,volume,journal)
    except ValueError as error:need('has 0 directory records' in str(error),'Journal file error')
    else:raise ValueError('Journal already exists')
finally:view.close()
flags=[f for f in control['args'].split() if not f.startswith('sheng-build-tag=')]
need(not any(f.startswith(('venus-gestalt-refresh=','venus-mg-task=','sheng-data-reset=','sheng-gpu-addon=')) for f in flags),'Unexpected intervention')
flags+=['venus-gestalt-refresh=1','sheng-build-tag=scale-refresh-'+VERSION];kernelargs=' '.join(flags)
need(len(kernelargs.encode())<1024,'Boot args exceed ABI')
phone=OUT/'phone'
if not args.check:
    phone.mkdir(exist_ok=False)
    for name in ('payload.img','SILICIUM_UEFI.fd','UniXNU.efi','UniXNUDxe.efi','DarwinBoot.efi'):
        shutil.copy2(CONTROL/'phone'/name,phone/name)
    config=(CONTROL/'phone/unixnu.toml').read_text();need(config.count(control['args'])==1,'Ambiguous args')
    config=config.replace(control['args'],kernelargs);(phone/'unixnu.toml').write_text(config)
    for source,target in ((KERNEL/'kernel.macho','Payloads/kernel.macho'),(phone/'unixnu.toml','unixnu.toml')):
        run(['mcopy','-o','-i',phone/'payload.img',source,'::/EFI/UniXNU/'+target])
    run(['python3',ROOT/'tools/package-venus-uefi.py','--tree',ROOT/'ports/uefi-venus','--workspace',ROOT,
         '--artifacts',phone,'--payload',phone/'payload.img'])
need(fat(phone/'payload.img','Payloads/kernel.macho')==(KERNEL/'kernel.macho').read_bytes(),'Kernel FAT mismatch')
for path in ('Payloads/kernel.macho.adt','Payloads/scratch-data.img','Payloads/kernel.macho.trustcache'):
    need(fat(phone/'payload.img',path)==fat(CONTROL/'phone/payload.img',path),'Retained input changed: '+path)
need(fat(phone/'payload.img','unixnu.toml')==(phone/'unixnu.toml').read_bytes(),'Config changed')
v=load(phone/'verification.json');oldv=load(CONTROL/'phone/verification.json')
need(v['roundtrip_verified'] and not v['uefi_memory_conflicts'] and v['fd_sha256']==oldv['fd_sha256'] and v['efi']==oldv['efi'] and
     sha(phone/'boot-venus-unixnu.img')==v['sha256'],'Container check failed')
record={'device':'venus','image':str(phone/'boot-venus-unixnu.img'),'image_sha256':v['sha256'],'image_bytes':v['bytes'],
    'kernel_sha256':sha(KERNEL/'kernel.macho'),'args':kernelargs,'host_tests_passed':True,
    'qemu_systemos_passed':True,'qemu_actual_data_checkpoint_passed':True,'qemu_positive_cache_rename_verified':VERSION=='012',
    'qemu_sync_refusal_guard_verified':VERSION=='011','source_cache_snapshot':str(snapshot),'source_cache_files':present,
    'backup_suffix':None if VERSION=='012' else '.venus-scale-011.bak','cache_paths':paths,'journal_path':'/private/var/db/venus-scale-012/refresh.jsonl' if VERSION=='012' else '/private/var/tmp/venus-scale-011.jsonl',
    'only_boot_member_changed_from_rebuilt_baseline':'BootWatchdogPolicy.o','original_010_kernel_reused':False,
    'original_adt_seed_trust_fd_efi_preserved':True,'qualified_ramblock_preserved':True,
    'cache_fix':'After original policy and before normal launchd, persist durable begin; exclusively rename old MG files to backups, fsync parent and medium; persist completion. No cache-answer injection or user job dependency.',
    'phone_tested':False,'scope':'Prepared new kernel'+VERSION+' for a single explicitly authorized MG cache invalidation/backup and journal write. Actual hardware synchronization/fresh MG answer/UI remains to be observed.'}
if VERSION=='012':
    record.update(backup_directory='/private/var/db/venus-scale-012',
        backup_paths=['/private/var/db/venus-scale-012/cache-'+str(i)+'.plist' for i in range(3)],
        cache_fix='Protected db journal/backups, exact shared-cache unowned UID(-2)/mode0 supported; original cache rename/dir/media result is independent of extra FULLFSYNC telemetry, every sync/error stage recorded.',
        qemu_fixture=load(OUT/'snapshot-fixture/report.json'))
if args.check:need(load(OUT/'candidate.json')==record,'Candidate differs')
else:
    (OUT/'candidate.json').write_text(json.dumps(record,indent=2)+'\n')
    (DEVICE/'evidence'/('scale-refresh'+VERSION+'-candidate.json')).write_text(json.dumps(record,indent=2)+'\n')
os.sync();print(json.dumps({k:record[k] for k in ('image','image_sha256','image_bytes','kernel_sha256','scope')},indent=2))
