#!/usr/bin/env python3
"""Use the qualified original init chain with two supported official policies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
CONTROL=ROOT/'artifacts/venus-lockscreen-scale-002'
OUT=ROOT/'artifacts/venus-sheng-chain-010'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(p.read_text())
def need(ok,why):
    if not ok:raise ValueError(why)
def run(command,timeout=240):return subprocess.check_output([str(x) for x in command],timeout=timeout)
def fat(image,path):return run(['mtype','-i',image,'::/EFI/UniXNU/'+path])
control=load(CONTROL/'candidate.json');comparison=load(DEVICE/'evidence/sheng-startup-comparison.json')
need(sha(CONTROL/'phone/boot-venus-unixnu.img')==control['image_sha256']=='345074da0e66babb5503e8b5f2d5854b8c6474c4c2a34b53b9895ea6bdd647d0','Qualified control changed')
kernel=CONTROL/'kernel/kernel.macho'
need(sha(kernel)==comparison['kernel_sha256']=='4b1ae1c0bc6ea2b7dbb440099ef5c0a0c413d26aab8bfe304f1fbc8b1a2760be','Qualified kernel changed')
adopted=['kt_fixed_zones=120','sheng-disable-watchdogd=1']
need(comparison['policy_equal_except_venus_data_qualification_hook'] and all(comparison['candidate_flag_presence'][f] for f in adopted),'Reference compatibility not established')
flags=[f for f in control['args'].split() if not f.startswith('sheng-build-tag=')]
need(not any(f.startswith(('sheng-data-reset=','venus-gestalt-refresh=','venus-mg-task=','sheng-gpu-addon=')) for f in flags),'Unexpected intervention')
need(not any(f.split('=')[0] in ('kt_fixed_zones','sheng-disable-watchdogd') for f in flags),'Duplicate policy flag')
flags+=adopted+['sheng-build-tag=sheng-chain-010'];kernelargs=' '.join(flags)
phone=OUT/'phone'
if not args.check:
    OUT.mkdir(exist_ok=False);phone.mkdir()
    for name in ('payload.img','SILICIUM_UEFI.fd','UniXNU.efi','UniXNUDxe.efi','DarwinBoot.efi'):
        shutil.copy2(CONTROL/'phone'/name,phone/name)
    config=(CONTROL/'phone/unixnu.toml').read_text();need(config.count(control['args'])==1,'Ambiguous args')
    config=config.replace(control['args'],kernelargs)
    (phone/'unixnu.toml').write_text(config)
    run(['mcopy','-o','-i',phone/'payload.img',phone/'unixnu.toml','::/EFI/UniXNU/unixnu.toml'])
    run(['python3',ROOT/'tools/package-venus-uefi.py','--tree',ROOT/'ports/uefi-venus','--workspace',ROOT,
         '--artifacts',phone,'--payload',phone/'payload.img'])
    qflags=[f for f in flags if not f.startswith(('native-ufs-root=','sheng-pmgr='))]
    run(['python3',DEVICE/'scripts/test-venus-root-mount.py','--kernel',kernel,
         '--prelink-report',CONTROL/'kernel/kernel.json','--owned-memory-size','0x180000000','--qemu-memory-mib','8192',
         '--systemos-checkpoint','--inspect-memory-budget','--inspect-os-services','--out-name','qemu-sheng-chain-010',
         '--extra-kernel-arg',' '.join(qflags)],timeout=420)
for name in ('Payloads/kernel.macho','Payloads/kernel.macho.adt','Payloads/kernel.macho.trustcache','Payloads/scratch-data.img'):
    need(fat(phone/'payload.img',name)==fat(CONTROL/'phone/payload.img',name),'Retained input changed: '+name)
need(tomllib.loads(fat(phone/'payload.img','unixnu.toml').decode())['entry'][0]['args']==kernelargs,'Args differ')
verify=load(phone/'verification.json');oldverify=load(CONTROL/'phone/verification.json')
need(verify['roundtrip_verified'] and not verify['uefi_memory_conflicts'] and verify['fd_sha256']==oldverify['fd_sha256'] and
     verify['efi']==oldverify['efi'] and sha(phone/'boot-venus-unixnu.img')==verify['sha256'],'Boot identity check failed')
qdir=ROOT/'artifacts/venus-ufs-root/qemu-sheng-chain-010'
q=load(qdir/'gdb-stop.json');memory=load(qdir/'memory-budget.json');services=load(qdir/'os-services.json')
need(q['kernel_sha256']==sha(kernel) and not q['bounded_timeout_interrupted'] and q['owner_cache_mount']['_native_owner_cache_status']==0 and
     memory['_max_mem']==0x180000000 and services['aks_state_passed'] and services['hid_state_passed'],'Actual QEMU check failed')
record={'device':'venus','reference_revision':comparison['revision'],'adopted_policies':adopted,
    'image':str(phone/'boot-venus-unixnu.img'),'image_sha256':verify['sha256'],'image_bytes':verify['bytes'],
    'kernel_sha256':sha(kernel),'args':kernelargs,'original_init_chain_preserved':True,
    'kernel_adt_seed_trust_fd_efi_preserved':True,'qemu_systemos_and_services_passed':True,
    'qemu_data_policy_execution_verified':False,'phone_tested':False,
    'scope':'Original4b1 normal /sbin/launchd chain with supported official sheng generic startup policies. Runtime original watchdog-policy rewrites Data; no experimental /usr/libexec union or query shim. UI/MG recovery is unmeasured.'}
if args.check:need(load(OUT/'candidate.json')==record,'Candidate differs')
else:
    (OUT/'candidate.json').write_text(json.dumps(record,indent=2)+'\n')
    (DEVICE/'evidence/sheng-chain-control-candidate.json').write_text(json.dumps(record,indent=2)+'\n')
os.sync();print(json.dumps(record,indent=2))
