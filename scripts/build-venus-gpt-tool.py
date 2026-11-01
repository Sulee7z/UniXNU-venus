#!/usr/bin/env python3
"""Build a plan-bound EFI GPT application; never execute it on a phone here."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

root = Path('/mnt/g/UniXNU-Port')
device = root / 'ports/UniXNU-venus'
upstream = root / 'sources/UniXNU-guide'
sys.path.insert(0, str(upstream / 'scripts'))
from dual_sys.gpt import GPT
from unixnu.payload import write_volume
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apply', action='store_true', help='Build the separately authorized writing variant')
args = parser.parse_args()
source = root / 'artifacts/venus-deployment'
out = source / ('gpt-apply-label' if args.apply else 'gpt-preview-label')
out.mkdir(exist_ok=True)
plan = json.loads((source / 'partition-preview.json').read_text())
if (plan['serial'] != '55870427' or plan['unixnu_bytes'] != 64 << 30 or
        plan['userdata_index'] != 34 or plan['unixnu_index'] != 35 or plan['sector_bytes'] != 4096):
    raise SystemExit('Wrong device or target plan')
before = GPT((source/'gpt-primary.before').read_bytes(), (source/'gpt-backup.before').read_bytes(), 4096, plan['disk_bytes']//4096)
after = GPT((source/'gpt-primary.preview').read_bytes(), (source/'gpt-backup.preview').read_bytes(), 4096, before.total)
old_user = next(e for e in before.entries if e['name'] == 'userdata')
new_user = next(e for e in after.entries if e['name'] == 'userdata')
unixnu = next(e for e in after.entries if e['name'] == 'unixnu')
if (unixnu['start'] != plan['unixnu_start'] or unixnu['end'] != plan['unixnu_end'] or
        new_user['end'] + 1 != unixnu['start'] or len(after.entries) != len(before.entries) + 1):
    raise SystemExit('Preview geometry differs')
for key in ('start','guid','flags','index'):
    if old_user[key] != new_user[key]: raise SystemExit('Android userdata identity changed')
for entry in before.entries:
    if entry['name'] != 'userdata' and entry not in after.entries: raise SystemExit('Unrelated GPT entry changed')
previous = json.loads((device/'evidence/dual-readonly.json').read_text())
for data, name in ((before.primary,'gpt-primary.bin'),(before.backup,'gpt-backup.bin')):
    if hashlib.sha256(data).hexdigest() != previous['files'][name]: raise SystemExit('Original GPT differs')
header = f'// Generated from the exact retained Venus GPT; apply={int(args.apply)}.\n#define VG_APPLY {int(args.apply)}\n'
header += f'#define VG_LAST_LBA {before.total-1}ULL\n#define VG_BACKUP_LBA {before.total-5}ULL\n'
header += f'#define VG_UNIXNU_FIRST {unixnu["start"]}ULL\n#define VG_UNIXNU_LAST {unixnu["end"]}ULL\n'
for name, data in [('VgPrimaryBefore',before.primary),('VgBackupBefore',before.backup),
                   ('VgPrimaryAfter',after.primary),('VgBackupAfter',after.backup)]:
    header += f'static const unsigned char {name}[] = {{\n'
    header += ''.join('  '+','.join(f'0x{x:02x}' for x in data[i:i+16])+',\n' for i in range(0,len(data),16)) + '};\n'
(out/'GeneratedPlan.h').write_text(header)
application = root/'ports/uefi-venus/Platforms/Xiaomi/venusPkg/Applications/VenusPartition'
shutil.copy2(out/'GeneratedPlan.h', application/'GeneratedPlan.h')
shutil.copy2(device/'package/VenusGptTransaction.h', application/'GeneratedTransaction.h')
test = out/'transaction-test'
subprocess.run(['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                '-I',out,'-I',device/'package',device/'tests/gpt_transaction.cpp','-o',test],check=True)
test_output = subprocess.check_output([test],text=True)
env = dict(os.environ, VENUS_ARTIFACTS=str(out), VENUS_UNIXNU_SOURCE=str(upstream),
           VENUS_GUIDE_LOGGING='TRUE', VENUS_GPT_TOOL='TRUE')
env.pop('VENUS_PAYLOAD',None)
subprocess.run(['bash',root/'tools/build-venus-uefi.sh'],env=env,check=True)
stage = out/'esp'; entries = stage/'EFI/UniXNU/Payloads'; entries.mkdir(parents=True,exist_ok=True)
shutil.copy2(out/'VenusPartition.efi', entries/'VenusPartition.efi')
mode = 'Apply 64GiB unixnu GPT plan' if args.apply else 'Verify 64GiB unixnu GPT preview'
config = ('version = 1\n[boot]\ntimeout = 5\ndefault = "partition"\n[kits]\nautoload = false\n'
          '[[entry]]\nid = "partition"\ntype = "efi"\npath = "Payloads/VenusPartition.efi"\n'
          f'title = "{mode}"\n'
          '[[entry]]\nid = "reset"\ntype = "action"\naction = "reset"\ntitle = "Restart"\n')
(stage/'EFI/UniXNU/unixnu.toml').write_text(config)
fat = out/'payload.img'; write_volume(stage,fat,'VENUSXNU',64)
fat_test = out/'fat-recognizer-test'
fat_source = root/'ports/uefi-venus/Platforms/Xiaomi/venusPkg/Drivers/VenusPayloadDxe'
subprocess.run(['cc','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                '-I',fat_source,device/'tests/gpt_payload.c','-o',fat_test],check=True)
old_payload = source/'gpt-apply/payload.img'
fat_result = subprocess.check_output([fat_test,fat,*([old_payload] if old_payload.exists() else [])],text=True)
subprocess.run(['python3',root/'tools/package-venus-uefi.py','--tree','/root/unixnu-build/uefi-venus',
                '--workspace',root,'--artifacts',out,'--payload',fat],check=True)
subprocess.run(['python3',root/'tools/check-venus-layout.py','--artifacts',out],check=True)
def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
record = {'mode':'apply' if args.apply else 'preview','plan':plan,'efi_sha256':sha(out/'VenusPartition.efi'),
          'payload_sha256':sha(fat),'image_sha256':sha(out/'boot-venus-unixnu.img'),
          'image_bytes':(out/'boot-venus-unixnu.img').stat().st_size,
          'core_sha256':sha(device/'package/VenusGptTransaction.h'),
          'source_sha256':sha(application/'VenusPartition.c'), 'generated_plan_sha256':sha(out/'GeneratedPlan.h'),
          'host_test':test_output.strip(),'fat_recognizer_test':fat_result.strip(),
          'fat_label':'VENUSXNU','phone_run':False,'device_write_authorized':False}
(out/'gpt-tool.json').write_text(json.dumps(record,indent=2)+'\n')
os.sync()
print(json.dumps(record,indent=2))
