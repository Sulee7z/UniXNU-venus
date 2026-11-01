#!/usr/bin/env python3
"""Build the restored-before-publication RamBlock against the selected XNU ABI.

Called by the root archive recipe after it checks/copies the original support.
The qualified root/UFS inputs and their historical receipts are not overwritten.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

DEVICE=Path('/mnt/g/UniXNU-Port/ports/UniXNU-venus')
ROOT=DEVICE.parents[1]
RAM=ROOT/'sources/UniXNU-guide/drivers/RamBlock'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tree',required=True,type=Path)
parser.add_argument('--support',required=True,type=Path)
args=parser.parse_args()
tree=args.tree.resolve();support=args.support.resolve()
out=tree/'build/venus-ram-block';out.mkdir(parents=True,exist_ok=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text())
def run(command,name,cwd=None):
    result=subprocess.run([str(x) for x in command],cwd=cwd,capture_output=True,text=True,timeout=180)
    (out/(name+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(name+' failed: '+result.stdout+result.stderr)
    return result.stdout
host_check=DEVICE/'evidence/data-deferred-publication-host.json'
check=load(host_check)
patch=DEVICE/'patches/ram-block/publish-restored-view.patch'
deferred_patch=DEVICE/'patches/ram-block/publish-at-data-mount.patch'
if check['source_sha256']!=sha(RAM/'NativeRamBlock.cpp') or any(check['patches'][p.name]!=sha(p) for p in (patch,deferred_patch)):
    raise SystemExit('Run check-deferred-data-publication.py for these exact source/patch inputs first')
source=out/'source';source.mkdir(exist_ok=True)
inputs={}
for name in ('NativeRamBlock.cpp','DirectDisk.h','PersistOverlay.h','SparseDisk.h','SeedDisk.h'):
    inputs[name]=sha(RAM/name);shutil.copy2(RAM/name,source/name)
run(['git','apply','--check',patch],'patch-check',source)
run(['git','apply',patch],'patch-apply',source)
run(['git','apply','--check',deferred_patch],'deferred-patch-check',source)
run(['git','apply',deferred_patch],'deferred-patch-apply',source)
if sha(source/'NativeRamBlock.cpp')!=check['patched_source_sha256']:
    raise SystemExit('Patched source differs from the publication regression')
receipt=tree/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'
record=json.loads(receipt.read_text().strip().rstrip(','))
command=[];i=0;original=record['arguments'];obj=out/'NativeRamBlock.o'
while i<len(original):
    value=original[i]
    if value==record['file']:command.append(str(source/'NativeRamBlock.cpp'))
    elif value=='-o':command+=['-o',str(obj)];i+=1
    elif value in ('-MF','-MJ','-MT','-MQ'):i+=1
    elif value=='-Xclang' and original[i+1].startswith('-W'):i+=1
    elif value not in ('-MD','-MMD','-MP') and not value.startswith('-W'):command.append(value)
    i+=1
# Storage audit headers belong to the original qualified support build; use its
# exact header directory, recorded in the UFS compilation command.
ufs_command=load(support.parent/'compile-command.json')
abi=[Path(ufs_command[i+1]) for i,v in enumerate(ufs_command[:-1])
     if v=='-I' and ufs_command[i+1].endswith('/build/storage-abi/include')]
if len(abi)!=1 or not abi[0].is_dir():raise SystemExit('Qualified storage ABI headers unavailable')
audit=abi[0].parent/'interface-audit.json'
if sha(audit)!=load(support.parent/'venus-build.json')['storage_interface_audit_sha256']:
    raise SystemExit('Original qualified storage ABI audit changed')
audit_target=tree/'build/storage-abi/interface-audit.json'
audit_target.parent.mkdir(parents=True,exist_ok=True)
if audit_target.exists() and sha(audit_target)!=sha(audit):
    raise SystemExit('Build tree has a different storage ABI audit')
shutil.copy2(audit,audit_target)
command+=['-I',str(abi[0]),'-I',str(tree/'.cache/xnu-work/osfmk'),'-mgeneral-regs-only',
          '-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-c99-designator',
          '-Wno-reorder-init-list','-Wno-deprecated-enum-enum-conversion','-Wno-unnecessary-virtual-specifier']
(out/'compile-command.json').write_text(json.dumps(command,indent=2)+'\n')
run(command,'compile',record['directory'])
run(['python3',tree/'scripts/build-virtio-mmio-bindings.py','--component','RamBlock','--directory',out],
    'bindings',tree)
bindings=load(out/'bindings.json');old=load(support/'RamBlock/bindings.json')
if bindings['bindings']!=old['bindings'] or bindings['virtual_methods_checked']!=190 or bindings['unresolved_original_imports']:
    raise SystemExit('Changed RamBlock does not match the original 190-slot storage ABI')
archive=out/'libRamBlock.a';archive.unlink(missing_ok=True)
run(['xcrun','ar','rcs',archive,obj,support/'storage-bindings.o'],'archive')
target=tree/'build/ram-block';target.mkdir(exist_ok=True)
for name in ('NativeRamBlock.o','libRamBlock.a','bindings.json'):shutil.copy2(out/name,target/name)
shutil.copy2(obj,target/'RamBlock.o')
# The shared alias addresses stay identical; refresh only the copied build's
# consumer-object receipt so the final linker can audit the actual new object.
virtual_path=tree/'build/virtio-mmio-block/bindings.json'
virtual=load(virtual_path)
virtual['shared_alias_consumers']['RamBlock']=bindings['compiled_object_sha256']
virtual_path.write_text(json.dumps(virtual,indent=2)+'\n')
report={'component':'RamBlock','device':'venus','inputs':inputs,'patch_sha256':sha(patch),
        'deferred_patch_sha256':sha(deferred_patch),'publication_phase':'original Data selection after SystemOS',
        'patched_source_sha256':sha(source/'NativeRamBlock.cpp'),'object_sha256':sha(obj),
        'archive_sha256':sha(archive),'bindings':bindings,'compile_receipt_sha256':sha(receipt),
        'storage_interface_audit_sha256':sha(audit),
        'shared_aliases_unchanged':True,'host_publication_test_sha256':sha(host_check),
        'host_publication_test_reference':'evidence/data-deferred-publication-host.json',
        'phone_tested':False}
(out/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: post-SystemOS restored-before-publication RamBlock compiled; 190-slot ABI and shared aliases match; installed',sha(obj))
