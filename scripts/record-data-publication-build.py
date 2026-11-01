#!/usr/bin/env python3
"""Bind the corrected RamBlock build and real root QEMU control to saved inputs."""
import hashlib
import argparse
import json
from pathlib import Path
import shutil
import subprocess
DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
WORK=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--deferred',action='store_true',help='Record the post-SystemOS publication build separately')
args=parser.parse_args()
OUT=ROOT/('artifacts/venus-data-deferred-publication' if args.deferred else 'artifacts/venus-data-publication')
host_reference='data-deferred-publication-host.json' if args.deferred else 'data-publication-host.json'
def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def load(p):return json.loads(p.read_text())
build=WORK/'tree/build/venus-ram-block';report=load(build/'build-report.json')
assert sha(build/'NativeRamBlock.o')==report['object_sha256']==sha(WORK/'tree/build/ram-block/RamBlock.o')
assert sha(build/'libRamBlock.a')==report['archive_sha256']==sha(WORK/'tree/build/ram-block/libRamBlock.a')
assert sha(DEVICE/'patches/ram-block/publish-restored-view.patch')==report['patch_sha256']
assert sha(DEVICE/'evidence'/host_reference)==report['host_publication_test_sha256']
qemu_dir=ROOT/('artifacts/venus-ufs-root/qemu-data-deferred-systemos' if args.deferred else 'artifacts/venus-ufs-root/qemu-data-publication')
qemu=load(qemu_dir/'gdb-stop.json');services=load(qemu_dir/'os-services.json')
digest=sha(WORK/'kernel/kernel.macho')
assert digest==qemu['kernel_sha256']==services['kernel_sha256']
assert qemu['stop_symbol']==('_native_owner_cache_checkpoint' if args.deferred else '_native_owner_root_accepted_checkpoint') and not qemu['bounded_timeout_interrupted']
assert services['aks_state_passed'] and services['hid_state_passed']
symbols=subprocess.check_output(['/usr/bin/llvm-nm',str(WORK/'kernel/kernel.macho')],text=True)
assert '__ZN14NativeRamBlock5startEP9IOService' in symbols
kernel=WORK/'kernel/kernel.macho'
assert b'NativeRamBlock: store unavailable before publication' in kernel.read_bytes()
saved=OUT/'linked-inputs';saved.mkdir(exist_ok=True)
for name in ('NativeRamBlock.o','libRamBlock.a','bindings.json','build-report.json','compile-command.json'):
    shutil.copy2(build/name,saved/name)
for name in ('kernel.macho','kernel.json'):shutil.copy2(WORK/'kernel'/name,OUT/name)
shutil.copy2(DEVICE/'patches/ram-block/publish-restored-view.patch',saved/'publish-restored-view.patch')
if args.deferred:
    assert sha(DEVICE/'patches/ram-block/publish-at-data-mount.patch')==report['deferred_patch_sha256']
    shutil.copy2(DEVICE/'patches/ram-block/publish-at-data-mount.patch',saved/'publish-at-data-mount.patch')
shutil.copy2(qemu_dir/'gdb-stop.json',saved/'qemu-root.json')
shutil.copy2(qemu_dir/'os-services.json',saved/'qemu-services.json')
result={'device':'venus','date':'2026-10-28','kernel_sha256':digest,'ram_block':report,
        'qemu_systemos_passed':args.deferred,
        'final_kernel_contains_corrected_provider':True,'qemu_root_passed':True,'qemu_services':services,
        'files':{str(p.relative_to(OUT)):sha(p) for p in saved.iterdir() if p.is_file()},
        'phone_tested':False,'phone_image_prepared':False,'data_file_reboot_test_passed':False,
        'scope':'Corrected provider build/ABI plus real read-only QEMU root and OS service control; QEMU has no UFS and did not exercise the Data file mount'}
(DEVICE/'evidence'/('data-deferred-publication-build.json' if args.deferred else 'data-publication-build.json')).write_text(json.dumps(result,indent=2)+'\n')
print('PASS: compiled RamBlock, final kernel and QEMU controls bound:',digest)
