#!/usr/bin/env python3
"""Check both real phone records, exact images/photos and confirmed restart."""
import hashlib
import json
from pathlib import Path
DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
OUT=ROOT/'artifacts/venus-data-check-002'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def local(p):
    if str(ROOT).startswith('/mnt/g/') and p[:2].upper()=='G:':return Path('/mnt/g/'+p[3:].replace('\\','/'))
    return Path(p)
candidate=load(OUT/'candidate.json');plan=candidate['plan'];records={}
for phase,label in ((1,'write'),(2,'read')):
    path=DEVICE/f'evidence/data-check-002-{label}-phone.json';record=load(path)
    assert record['image_sha256']==candidate['images'][label]['sha256']==sha(OUT/label/'boot-venus-unixnu.img')
    assert record['kernel_sha256']==plan['kernel_sha256']
    assert record['file_path']==plan['file_path'] and record['file_sha256']==plan['file_sha256']
    assert record['file_operation_passed'] and record['ram_boot']['attempts_executed']==1
    assert sha(local(record['photos'][0]))==record['photo_sha256']
    observed=record['observed']
    assert (observed['phase'],observed['step'],observed['rc'],observed['match'],observed['bytes'],observed['store_state'])==(phase,11,0,1,53,2)
    assert observed['token_prefix']==plan['token'][:8] and observed['device_identity_passed']
    assert observed['detail_values']['io'][-1]==0
    auth=load(local(record['authorization']))
    assert auth['sha256']==record['image_sha256'] and auth['file_sha256']==plan['file_sha256']
    assert not auth['automatic_retry'] and not auth['partition_flash_or_erase']
    records[label]=record
write,read=records['write'],records['read']
assert write['observed']['write_sync_evidence_passed']
assert read['manual_restart_confirmed'] and read['cross_reboot_readback_passed']
assert load(local(read['authorization']))['manual_restart_after_write_confirmed']
io=read['observed']['detail_values']['io'];sync=read['observed']['detail_values']['sync']
assert io[0]==io[1] and io[4]==io[5] and sync[:4]==[-1,-1,-1,-1]
assert write['observed']['detail_values']['sync'][5]==sync[4]==sync[5]
assert sha(OUT/'expected-marker.bin')==plan['file_sha256']
result={'device':'venus','date':'2026-10-28','milestone':'Controlled Data file survives the confirmed manual reboot',
        'passed':True,'kernel_sha256':plan['kernel_sha256'],'plan':plan,
        'records':{label:{'reference':f'evidence/data-check-002-{label}-phone.json',
                          'record_sha256':sha(DEVICE/f'evidence/data-check-002-{label}-phone.json'),
                          'image_sha256':r['image_sha256'],'photo_sha256':r['photo_sha256'],
                          'screen_seconds':r['observed']['screen_seconds']} for label,r in records.items()},
        'read_interval_persistent_writes_unchanged':True,'read_sync_steps_not_called':True,
        'scope':'One exclusive53-byte file, Data/parent/file identity, file+directory+full+UFS sync, confirmed restart and exact readback. Full UFS endurance/recovery is not claimed.',
        'next_stage':'CPU display mode, known frame and swap completion; physical input follows'}
(DEVICE/'evidence/data-persistence-qualified.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: exact write/read images and photos, successful file/sync records, confirmed restart and read-only53-byte comparison')
