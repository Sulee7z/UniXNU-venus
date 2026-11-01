#!/usr/bin/env python3
"""Compare retained storage inputs and compiled boot ordering after the 2s photo."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from PIL import Image

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
WORK=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
CANDIDATE=ROOT/'artifacts/venus-lockscreen-scale-001'
OLD=ROOT/'artifacts/venus-data-check-002/linked-inputs'
OUT=ROOT/'artifacts/venus-lockscreen-scale-stall';OUT.mkdir(exist_ok=True)
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(p.read_text())
candidate=load(CANDIDATE/'candidate.json')
assert sha(CANDIDATE/'phone/boot-venus-unixnu.img')==candidate['image_sha256']
kernel=CANDIDATE/'kernel/kernel.macho'
assert sha(kernel)==candidate['kernel_sha256']==sha(WORK/'kernel/kernel.macho')
old=load(OLD/'ram-build-report.json');newpath=WORK/'tree/build/venus-ram-block/build-report.json';new=load(newpath)
fields=('inputs','patch_sha256','deferred_patch_sha256','publication_phase','patched_source_sha256','object_sha256','archive_sha256','storage_interface_audit_sha256')
same={k:old[k]==new[k] for k in fields}
current=WORK/'tree/build/ram-block/libRamBlock.a'
assert sha(current)==new['archive_sha256']
assert sha(OLD/'ram-libRamBlock.a')==old['archive_sha256']
def archive_members(path):
    names=subprocess.check_output(['/usr/bin/llvm-ar','t',str(path)],text=True).splitlines()
    assert len(names)==len(set(names))
    return {name:hashlib.sha256(subprocess.check_output(['/usr/bin/llvm-ar','p',str(path),name])).hexdigest() for name in names}
oldmembers=archive_members(OLD/'ram-libRamBlock.a');newmembers=archive_members(current)
ufs=load(WORK/'tree/build/sheng-ufs/venus-build.json')
ufsfile=WORK/'tree/build/sheng-ufs/libShengUfs.a'
assert sha(ufsfile)==ufs['archive_sha256']==sha(ROOT/'artifacts/venus-ufs-root-unixnu/libShengUfs.a')
for source,name in ((newpath,'ram-build-report.json'),(current,'libRamBlock.a'),
                    (WORK/'tree/build/venus-ram-block/source/NativeRamBlock.cpp','NativeRamBlock.cpp'),
                    (WORK/'tree/build/sheng-ufs/venus-build.json','ufs-build-report.json')):
    shutil.copy2(source,OUT/name)
nm=subprocess.check_output(['/usr/bin/llvm-nm','--numeric-sort',str(kernel)],text=True)
names=[]
for line in nm.splitlines():
    parts=line.split()
    if len(parts)==3:
        try:addr=int(parts[0],16)
        except ValueError:continue
        if addr:names.append((addr,parts[2]))
samples={}
for addr in (0xfffffff00bfc7d54,0xfffffff00ba174e8):
    earlier=[n for n in names if n[0]<=addr]
    a,name=max(earlier)
    samples[hex(addr)]={'nearest_symbol':name,'offset':hex(addr-a),'limitation':'Historical timer sample; not a fault or stop PC'}
selected=[(a,n) for a,n in names if n in ('_load_init_program','_native_owner_cache_checkpoint','_native_owner_cache_mount',
    '_native_owner_data_prepare','_native_ram_block_volume_seed','_sheng_boot_watchdog_policy','_venus_boot_gestalt_cache')]
for _,name in selected:
    result=subprocess.run(['/usr/bin/llvm-objdump','--disassemble','--no-show-raw-insn','--disassemble-symbols='+name,str(kernel)],capture_output=True,text=True,check=True)
    (OUT/(name+'.txt')).write_text(result.stdout)
photo=Path('/mnt/g/20261029_083930.JPG')
assert sha(photo)=='1a54ca764fc70d3931447e13b081c12f75e18d31a8443b40014f25b39fcf9f41'
with Image.open(photo) as image:
    w,h=image.size
    for name,box in [('top',(120,95,1510,530)),('bottom',(110,1010,1520,1370))]:
        coords=tuple(round(v*(w/2000 if i%2==0 else h/1500)) for i,v in enumerate(box))
        image.crop(coords).save(OUT/(name+'.png'))
qdir=ROOT/'artifacts/venus-ufs-root/qemu-lockscreen-scale-001'
qemu=load(qdir/'gdb-stop.json')
assert sha(qdir/'gdb-stop.json')==candidate['qemu_systemos_sha256']
assert qemu['kernel_sha256']==candidate['kernel_sha256'] and qemu['owner_cache_mount']['_native_owner_cache_status']==0
report={'device':'venus','image_sha256':candidate['image_sha256'],'kernel_sha256':candidate['kernel_sha256'],
        'photo_sha256':sha(photo),'ram_block_same_as_phone_qualified_data002':same,
        'ram_block_actual_archive_sha256':sha(current),'ufs_actual_archive_sha256':sha(ufsfile),
        'ram_archive_members_old':oldmembers,'ram_archive_members_new':newmembers,
        'ram_archive_members_identical':oldmembers==newmembers,
        'qemu_same_kernel_systemos_passed':True,'qemu_uses_physical_ufs':False,
        'sample_addresses':samples,'boot_symbols':{n:hex(a) for a,n in selected},
        'scope':'Host identity/order checks only; does not identify the runtime deadlock or UFS failure cause'}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(DEVICE/'evidence/lockscreen-scale-stall-host.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
