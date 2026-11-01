#!/usr/bin/env python3
"""Package the DT/dot-pitch read-only probe on the current kernel (004)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
WORK=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
CONTROL=ROOT/'artifacts/venus-userspace-6g-001'
ADTSRC=ROOT/'artifacts/venus-lockscreen-scale-001/kernel.macho.adt'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');parser.add_argument('--out-name',default='venus-lockscreen-dtprobe-004');args=parser.parse_args()
OUTNAME=args.out_name
OUT=ROOT/'artifacts'/OUTNAME
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(p.read_text())
def need(ok,why):
    if not ok:raise SystemExit(why)
def run(argv):return subprocess.check_output([str(x) for x in argv],timeout=300)
def fat(image,name):return run(['mtype','-i',image,'::/EFI/UniXNU/'+name])
control=load(CONTROL/'candidate.json')
need(sha(CONTROL/'phone/boot-venus-unixnu.img')==control['image_sha256'],'6GiB control image changed')
need(sha(CONTROL/'phone/payload.img')==control['payload_sha256'],'6GiB control payload changed')
kernel=WORK/'kernel/kernel.macho';report=load(WORK/'tree/build/boot-progress/build-report.json')
need(sha(WORK/'tree/build/boot-progress/libBootProgress.a')==report['archive_sha256'],'BootProgress archive mismatch')
for name in ('BootProgress.c','BootGestaltCache.h'):
    need(sha(DEVICE/'package/boot-progress'/name)==report['sources'][name],'Compiled source mismatch: '+name)
disp=load(WORK/'tree/build/native-legacy-display/build-report.json')
need(sha(WORK/'tree/build/native-legacy-display/libNativeLegacyDisplay.late.a')==disp['archive_sha256'],'Display archive mismatch')
need(sha(DEVICE/'package/LegacyDisplayProbe.cpp')==disp['source_sha256']['kits/venus/LegacyDisplayProbe.cpp'],'Display source not the compiled one')
need(b'DT=%d/%x dp=%d mg=%d' in kernel.read_bytes() and b'DT2 root=' in kernel.read_bytes() and b'DT3 absnull=' in kernel.read_bytes() and b'MODE %u/4 ' in kernel.read_bytes(),'DT/MODE probe rows absent from the kernel')
adt=ADTSRC.read_bytes()
baseargs=[a for a in control['args'].split() if not a.startswith('sheng-build-tag=')]
kernelargs=' '.join([*baseargs,'sheng-build-tag='+args.out_name.replace('venus-lockscreen-','')])
phone=OUT/'phone'
if not args.check:
    need(not OUT.exists(),'Preserve existing candidate')
    OUT.mkdir();phone.mkdir();(OUT/'kernel').mkdir();(OUT/'linked-inputs').mkdir()
    for name in ('kernel.macho','kernel.json'):shutil.copy2(WORK/'kernel'/name,OUT/'kernel'/name)
    (OUT/'kernel.macho.adt').write_bytes(adt)
    for name in ('payload.img','SILICIUM_UEFI.fd','UniXNU.efi','UniXNUDxe.efi','DarwinBoot.efi','Sec.efi'):
        shutil.copy2(CONTROL/'phone'/name,phone/name)
    config=(CONTROL/'phone/unixnu.toml').read_text()
    need(config.count(control['args'])==1,'Ambiguous control args')
    config=config.replace(control['args'],kernelargs)
    if 'action = "tools"' not in config:
        config+='\n[[entry]]\nid = "tools"\ntitle = "Tools"\ntype = "action"\naction = "tools"\n'
    (phone/'unixnu.toml').write_text(config)
    for local,target in ((OUT/'kernel/kernel.macho','Payloads/kernel.macho'),(OUT/'kernel.macho.adt','Payloads/kernel.macho.adt'),(phone/'unixnu.toml','unixnu.toml')):
        run(['mcopy','-o','-i',phone/'payload.img',local,'::/EFI/UniXNU/'+target])
    run(['python3',ROOT/'tools/package-venus-uefi.py','--tree',ROOT/'ports/uefi-venus','--workspace',ROOT,'--artifacts',phone,'--payload',phone/'payload.img'])
    for source,name in ((WORK/'tree/build/boot-progress/build-report.json','boot-progress-report.json'),
                        (WORK/'tree/build/native-legacy-display/build-report.json','display-build-report.json'),
                        (DEVICE/'package/LegacyDisplayProbe.cpp','LegacyDisplayProbe.cpp'),
                        (DEVICE/'package/boot-progress/BootProgress.c','BootProgress.c')):
        shutil.copy2(source,OUT/'linked-inputs'/name)
    qargs=[a for a in kernelargs.split() if not a.startswith(('native-ufs-root=','sheng-pmgr='))]
    subprocess.run(['python3',str(DEVICE/'scripts/test-venus-root-mount.py'),'--kernel',str(OUT/'kernel/kernel.macho'),
        '--prelink-report',str(OUT/'kernel/kernel.json'),'--owned-memory-size','0x180000000','--qemu-memory-mib','8192',
        '--systemos-checkpoint','--inspect-memory-budget','--inspect-os-services','--out-name','qemu-'+args.out_name,
        '--extra-kernel-arg',' '.join(qargs)],check=True,timeout=900)
kernelsha=sha(kernel)
need(fat(phone/'payload.img','Payloads/kernel.macho')==kernel.read_bytes(),'Kernel FAT mismatch')
need(fat(phone/'payload.img','Payloads/kernel.macho.adt')==adt,'ADT FAT mismatch')
need(tomllib.loads(fat(phone/'payload.img','unixnu.toml').decode())['entry'][0]['args']==kernelargs,'Args mismatch')
v=load(phone/'verification.json')
need(v['roundtrip_verified'] and not v['uefi_memory_conflicts'] and v['fd_sha256']==control['fd_sha256'] and v['efi']==control['efi'],'Container/firmware mismatch')
qdir=ROOT/'artifacts/venus-ufs-root'/('qemu-'+args.out_name)
qemu=load(qdir/'gdb-stop.json');budget=load(qdir/'memory-budget.json');services=load(qdir/'os-services.json')
need(qemu['kernel_sha256']==kernelsha and not qemu['bounded_timeout_interrupted'] and
     qemu['owner_cache_mount']['_native_owner_cache_status']==0,'QEMU SystemOS checkpoint failed')
need(budget['_max_mem']==0x180000000 and services['aks_state_passed'] and services['hid_state_passed'],'QEMU memory/services failed')
result={'device':'venus','date':'2026-10-29','purpose':'Make IODeviceTree:/chosen resolvable by mirroring display-scale/rotation onto a plane-root chosen entry, and report reachability/bytes/dot-pitch/mirror on the diagnostic row',
        'image':str(phone/'boot-venus-unixnu.img'),'image_sha256':sha(phone/'boot-venus-unixnu.img'),
        'image_bytes':(phone/'boot-venus-unixnu.img').stat().st_size,'kernel_sha256':kernelsha,
        'adt_sha256':sha(OUT/'kernel.macho.adt'),'args':kernelargs,'board_sha256':sha(DEVICE/'board.toml'),
        'row_format':'OS t=.. AKS=.. HID=.. DT=<found>/<scale-bits> dp=<dot-pitch-property> mg=<mirror>',
        'probe_code':{'chosen_path':'IORegistryEntry::fromPath("IODeviceTree:/chosen",gIODTPlane)',
                      'scale_property':'/chosen display-scale first 4 bytes','dot_pitch':'display provider property dot-pitch presence'},
        'qemu_systemos_sha256':sha(qdir/'gdb-stop.json'),'qemu_aks_hid_passed':True,
        'phone_tested':False,'normal_data_writes_expected':True,
        'scope':'Read-only instrumentation of the path MobileGestalt uses; does not change scale, validation or display behaviour.'}
if args.check:need(load(OUT/'candidate.json')==result,'Saved candidate differs')
else:
    (OUT/'candidate.json').write_text(json.dumps(result,indent=2)+'\n')
    (DEVICE/'evidence/lockscreen-dtprobe-candidate.json').write_text(json.dumps(result,indent=2)+'\n')
os.sync();print(json.dumps(result,indent=2))
