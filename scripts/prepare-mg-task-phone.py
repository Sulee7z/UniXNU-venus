#!/usr/bin/env python3
"""Package009 explicit early-task wrapper with original task and preserved query."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
OUT=ROOT/'artifacts/venus-mg-query-009';CONTROL=ROOT/'artifacts/venus-mg-query-008'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def load(path):return json.loads(path.read_text())
def need(ok,why):
    if not ok:raise ValueError(why)
def run(command):return subprocess.check_output([str(x) for x in command],timeout=240)
def fat(image,name):return run(['mtype','-i',image,'::/EFI/UniXNU/'+name])
def members(archive):
    names=run(['xcrun','ar','t',archive]).decode().splitlines()
    need(len(names)==len(set(names)),'Ambiguous archive members')
    return {n:hashlib.sha256(run(['xcrun','ar','p',archive,n])).hexdigest() for n in names}

control=load(CONTROL/'candidate.json');wrapper=load(OUT/'task-wrapper-r2/build.json')
tests=load(OUT/'task-host-tests-r2/report.json');activation=OUT/'activation-link-3';baseline=OUT/'baseline-link-4'
need(tests['passed'] and tests['source_sha256']==wrapper['source_sha256']==sha(DEVICE/'package/MGTaskLaunch.c'),'Wrapper build/test/source mismatch')
need(tests['mount_source_sha256']==load(activation/'report.json')['source_hook_sha256']==sha(DEVICE/'package/MGTaskMount.h'),'Mount build/test/source mismatch')
need(sha(OUT/'task-wrapper-r2/prng_seedctl')==wrapper['executable_sha256'] and wrapper['signature_pages_verified'],'Wrapper signature mismatch')
need(sha(OUT/'task-wrapper-r2/task-probe-original.trustcache')==wrapper['trustcache_sha256'],'Trust changed')
boot1=members(baseline/'libBootProgress.a');boot2=members(activation/'libBootProgress.a')
need(boot1.keys()==boot2.keys() and [n for n in boot1 if boot1[n]!=boot2[n]]==['BootWatchdogPolicy.o'],'Unexpected native boot member change')
display1=members(baseline/'libNativeLegacyDisplay.late.a');display2=members(activation/'libNativeLegacyDisplay.late.a')
need(display1==display2,'Display members changed between baseline and activation')
need(load(baseline/'report.json')['kernel_objects_archive_sha256']==load(activation/'report.json')['kernel_objects_archive_sha256'],'Kernel object archive changed')
tree=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root/tree')
need(sha(tree/'build/ram-block/NativeRamBlock.o')==sha(ROOT/'artifacts/venus-data-check-002/linked-inputs/ram-NativeRamBlock.o'),'Qualified RamBlock object changed')
for suffix,directory in (('',activation),('-baseline',baseline)):
    qdir=ROOT/'artifacts/venus-ufs-root'/('qemu-mg-query-009'+suffix)
    q=load(qdir/'gdb-stop.json');budget=load(qdir/'memory-budget.json');services=load(qdir/'os-services.json')
    need(q['kernel_sha256']==sha(directory/'kernel.macho') and q['stop_symbol']=='_native_owner_cache_checkpoint' and
         not q['bounded_timeout_interrupted'] and q['owner_cache_mount']['_native_owner_cache_status']==0,'Actual SystemOS check failed')
    need(budget['_max_mem']==0x180000000 and services['aks_state_passed'] and services['hid_state_passed'],'QEMU budget/services failed')
original=OUT/'original-task/usr_libexec_prng_seedctl'
need(sha(original)=='873619dd215aac7a61e7776f458fad231a93c234cc555d1cb469a6f2df6fc5e4','Original task differs from deployed OS')
probe=ROOT/'artifacts/venus-mg-query-probe/venus-mg-query'
need(sha(probe)==control['probe_executable_sha256'],'Actual query helper changed')
files=[('bin/venus-mg-query',0o755,probe.read_bytes()),('boot/prng_seedctl',0o755,(OUT/'task-wrapper-r2/prng_seedctl').read_bytes()),
       ('original/prng_seedctl',0o755,original.read_bytes())]
body=bytearray();entries=[]
for name,mode,data in files:
    encoded=name.encode()+b'\0';packed=zlib.compress(data,9)
    body+=struct.pack('<IIQQ',len(encoded),mode,len(data),len(packed))+encoded+bytes(-len(encoded)%8)+packed+bytes(-len(packed)%8)
    entries.append({'path':'/private/var/ngpu/'+name,'mode':oct(mode),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
addon=b'NGPUADD2'+struct.pack('<IIQ',3,0,24+len(body))+body
at=24;decoded=[]
for _ in range(3):
    namebytes,mode,size,packed=struct.unpack_from('<IIQQ',addon,at);at+=24
    name=addon[at:at+namebytes-1].decode();at+=(namebytes+7)&~7
    stream=zlib.decompressobj();data=stream.decompress(addon[at:at+packed])+stream.flush();at+=(packed+7)&~7
    need(stream.eof and not stream.unused_data and len(data)==size,'Addon inflate failure');decoded.append((name,mode,data))
need(at==len(addon) and decoded==files,'Addon wire mismatch')
flags=[f for f in control['args'].split() if not f.startswith('sheng-build-tag=')]
flags+=['venus-mg-task=1','sheng-build-tag=mg-query-009'];kernelargs=' '.join(flags)
need(len(kernelargs.encode())<1024,'Boot arguments exceed ABI')
phone=OUT/'phone-r2'
if not args.check:
    phone.mkdir(exist_ok=False)
    for name in ('payload.img','SILICIUM_UEFI.fd','UniXNU.efi','UniXNUDxe.efi','DarwinBoot.efi'):
        shutil.copy2(CONTROL/'phone'/name,phone/name)
    config=(CONTROL/'phone/unixnu.toml').read_text()
    need(config.count(control['args'])==1,'Ambiguous args');config=config.replace(control['args'],kernelargs)
    (phone/'unixnu.toml').write_text(config);(phone/'kernel.macho.gpuaddon').write_bytes(addon)
    for source,destination in ((activation/'kernel.macho','Payloads/kernel.macho'),
        (OUT/'task-wrapper-r2/task-probe-original.trustcache','Payloads/kernel.macho.trustcache'),
        (phone/'kernel.macho.gpuaddon','Payloads/kernel.macho.gpuaddon'),(phone/'unixnu.toml','unixnu.toml')):
        run(['mcopy','-o','-i',phone/'payload.img',source,'::/EFI/UniXNU/'+destination])
    run(['python3',ROOT/'tools/package-venus-uefi.py','--tree',ROOT/'ports/uefi-venus','--workspace',ROOT,
         '--artifacts',phone,'--payload',phone/'payload.img'])
for name,data in (('Payloads/kernel.macho',(activation/'kernel.macho').read_bytes()),
                  ('Payloads/kernel.macho.gpuaddon',addon),
                  ('Payloads/kernel.macho.trustcache',(OUT/'task-wrapper-r2/task-probe-original.trustcache').read_bytes())):
    need(fat(phone/'payload.img',name)==data,'FAT mismatch: '+name)
for name in ('Payloads/kernel.macho.adt','Payloads/scratch-data.img'):
    need(fat(phone/'payload.img',name)==fat(CONTROL/'phone/payload.img',name),'ADT/seed changed')
need(fat(phone/'payload.img','unixnu.toml')==(phone/'unixnu.toml').read_bytes(),'Config changed')
verify=load(phone/'verification.json')
need(verify['roundtrip_verified'] and not verify['uefi_memory_conflicts'] and verify['fd_sha256']==control['fd_sha256'] and
     verify['efi']==control['efi'] and sha(phone/'boot-venus-unixnu.img')==verify['sha256'],'Boot/firmware verification failed')
record={'device':'venus','image':str(phone/'boot-venus-unixnu.img'),'image_sha256':verify['sha256'],'image_bytes':verify['bytes'],
        'kernel_sha256':sha(activation/'kernel.macho'),'rebuilt_baseline_kernel_sha256':sha(baseline/'kernel.macho'),
        'original_008_kernel_reused':False,'only_boot_member_change_from_rebuilt_baseline':'BootWatchdogPolicy.o',
        'display_members_equal_to_rebuilt_baseline':True,'qualified_ramblock_object_preserved':True,
        'args':kernelargs,'installed_files':entries,'task_wrapper':wrapper,'task_host_tests_passed':True,
        'original_prng_task_sha256':sha(original),'original_seed_and_adt_preserved':True,'fd_sha256':verify['fd_sha256'],
        'qemu_systemos_and_services_passed':True,'qemu_actual_task_execution_verified':False,'phone_tested':False,
        'integration':'Opt-in readonly union /private/var/ngpu/boot over /usr/libexec. Existing early task prng_seedctl starts shim; parent immediately execs the exact original. One detached supervisor delays5s, runs preserved query as mobile501 in inherited bootstrap context, waits30s then kills/reaps on timeout.',
        'output_paths':['/private/var/tmp/venus-mg-query-009-launch.jsonl','/private/var/tmp/venus-mg-query-009.json','/private/var/tmp/venus-mg-query-009.stderr'],
        'scope':'Prepared host-verified009 activation repair. Runtime union/task/AMFI/helper/bootstrap/output remains to be measured in one exact authorized phone run.'}
if args.check:need(load(OUT/'candidate-r2.json')==record,'Saved candidate mismatch')
else:
    (OUT/'candidate-r2.json').write_text(json.dumps(record,indent=2)+'\n')
    (DEVICE/'evidence/mg-task-candidate.json').write_text(json.dumps(record,indent=2)+'\n')
os.sync();print(json.dumps({k:record[k] for k in ('image','image_sha256','image_bytes','kernel_sha256','scope')},indent=2))
