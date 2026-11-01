"""Prepare an early-C immediate-reset checkpoint; do not operate on a phone."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

root = Path('/mnt/g/UniXNU-Port')
base = root/'artifacts/venus-ufs-root'
source = base/'phone-288m'
out = base/'phone-arm-init-check'
def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()
if out.exists() and ((out/'boot-venus-unixnu.img').exists() or
                     sha(out/'kernel.macho') != sha(base/'kernel/kernel.macho')):
    raise SystemExit('Preserve the existing prepared or modified checkpoint before rebuilding')
out.mkdir(exist_ok=True)
os.environ['UNIXNU_UEFI'] = str(root/'ports/uefi-venus')
for name in ('payload.img','kernel.macho.adt','UniXNU.efi','UniXNUDxe.efi','DarwinBoot.efi','SILICIUM_UEFI.fd'):
    shutil.copyfile(source/name,out/name)
shutil.copyfile(base/'kernel/kernel.macho',out/'kernel.macho')
def run(command):
    result=subprocess.run([str(part) for part in command],capture_output=True,text=True,timeout=120)
    with (out/'prepare.log').open('a') as log: log.write(result.stdout+result.stderr)
    if result.returncode: raise SystemExit('Preparation failed; inspect '+str(out/'prepare.log'))
run(['python3',root/'sources/UniXNU-guide/scripts/patch-xnu-entry-probe.py',out/'kernel.macho',
     '--reset-after','_PE_init_platform','--reset-before','--in','_arm_init'])
run(['mcopy','-o','-i',out/'payload.img',out/'kernel.macho','::/EFI/UniXNU/Payloads/kernel.macho'])
config = (source/'unixnu.toml').read_text()
config = config.replace('native-ufs-root=1','native-ufs-root=0').replace('sheng-data-persist=2','sheng-data-persist=0')
if 'native-ufs-root=1' in config or 'sheng-data-persist=2' in config: raise SystemExit('Unexpected diagnostic arguments')
(out/'unixnu.toml').write_text(config)
run(['mcopy','-o','-i',out/'payload.img',out/'unixnu.toml','::/EFI/UniXNU/unixnu.toml'])
extracted=subprocess.check_output(['mtype','-i',str(out/'payload.img'),'::/EFI/UniXNU/Payloads/kernel.macho'])
if hashlib.sha256(extracted).hexdigest()!=sha(out/'kernel.macho'): raise SystemExit('Patched kernel FAT round-trip failed')
run(['python3',root/'tools/package-venus-uefi.py','--tree',root/'ports/uefi-venus',
     '--workspace',root,'--artifacts',out,'--payload',out/'payload.img'])
boot=json.loads((out/'verification.json').read_text())
report={'image':str(out/'boot-venus-unixnu.img'),'sha256':boot['sha256'],'bytes':boot['bytes'],
        'source_kernel_sha256':sha(base/'kernel/kernel.macho'),'checkpoint_kernel_sha256':sha(out/'kernel.macho'),
        'checkpoint':'immediately before first PE_init_platform call in arm_init',
        'mechanism':'PSCI SYSTEM_RESET SMC, no counter/timer dependency; WFE if firmware returns',
        'owned_memory_bytes':0x12000000,'native_ufs_root_enabled':False,'persistent_data_enabled':False,
        'phone_tested':False,'requires_new_reboot_and_exact_image_authorization':True}
(root/'ports/UniXNU-venus/evidence/arm-init-check-candidate.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
