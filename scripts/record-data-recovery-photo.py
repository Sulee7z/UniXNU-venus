#!/usr/bin/env python3
"""Bind recovery-run photos to the exact boot record without inventing a result."""
import argparse
import hashlib
import json
from pathlib import Path
import re

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out-name',default='venus-data-read-recovery-001')
parser.add_argument('--photo',required=True,type=Path)
parser.add_argument('--seconds',required=True,type=int)
parser.add_argument('--clock-stalled-confirmed',action='store_true',help='User confirms the photographed clock and stage remain stuck')
mode=parser.add_mutually_exclusive_group(required=True)
mode.add_argument('--line',help='Complete observed DATA CHECK row')
mode.add_argument('--last-stage',help='Observed pre-Data startup stage; no file result yet')
args=parser.parse_args()
assert args.out_name.startswith('venus-data-read-recovery-') and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.out_name)
OUT=ROOT/'artifacts'/args.out_name
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def load(path):return json.loads(path.read_text())
record_name='data-read-recovery-phone.json' if args.out_name=='venus-data-read-recovery-001' else args.out_name.removeprefix('venus-')+'-phone.json'
path=DEVICE/'evidence'/record_name
record=load(path);candidate=load(OUT/'candidate.json')
assert record['image_sha256']==candidate['image_sha256']==sha(OUT/'phone/boot-venus-unixnu.img')
assert record['ram_boot']['attempts_executed']==1 and args.seconds>=0
observed={'input_kind':'manual photograph transcription','photo':str(args.photo),
          'photo_sha256':sha(args.photo),'screen_seconds':args.seconds}
if args.last_stage:
    assert args.last_stage=='SystemOS mount enter','Review other pre-Data checkpoints before recording them'
    observed.update(last_boot_stage=args.last_stage,data_check_row_visible=False,
                    root_accepted=1,processes=1,ufs_reported_failures=0,ufs_reported_integrity_failures=0,
                    clock_progression_confirmed=False,clock_stalled_user_confirmed=args.clock_stalled_confirmed)
    # Absence of the test is not a failed comparison; keep unknown instead of
    # replacing the original pair's real ENOENT with an invented recovery result.
    record.update(file_operation_passed=None,cross_reboot_readback_passed=None,
                  scope='Recovery kernel reaches root acceptance and SystemOS mount entry; Data file qualification not observed',
                  boot_progression_passed=False if args.clock_stalled_confirmed else None,
                  pending='Inspect the SystemOS-mount stall and early restored-disk I/O/lock ordering; no automatic restart' if args.clock_stalled_confirmed else
                          'Confirm whether the2-second clock/stage advance, and obtain a later photograph; do not restart automatically')
else:
    match=re.fullmatch(r'DATA CHECK phase=(\d+) step=(\d+) rc=(-?\d+) match=(\d+) bytes=(\d+) token=([0-9a-f]{8}) store=(\d+)',args.line)
    assert match,'Transcribe the complete fixed result row'
    phase,step,rc,equal,count,token,store=match.groups();plan=candidate['original_marker']
    assert int(phase)==2 and token==plan['token'][:8]
    values={'phase':int(phase),'step':int(step),'rc':int(rc),'match':int(equal),'bytes':int(count),
            'token_prefix':token,'store_state':int(store)}
    passed=values=={'phase':2,'step':11,'rc':0,'match':1,'bytes':53,'token_prefix':token,'store_state':2}
    observed.update(row=args.line,data_check_row_visible=True,**values)
    assert load(DEVICE/'evidence/data-check-write-phone.json')['file_operation_passed']
    assert load(DEVICE/'evidence/data-check-read-phone.json')['manual_restart_confirmed']
    record.update(file_operation_passed=passed,cross_reboot_readback_passed=passed,boot_progression_passed=True,
                  scope='Original53-byte marker matched in recovery after the confirmed restart' if passed else 'Recovery file operation failed',
                  pending=None if passed else 'Inspect the exact recovery failure step; no automatic retry')
record.setdefault('photo_observations',[]).append(observed)
if str(args.photo) not in record['photos']:record['photos'].append(str(args.photo))
record['photo_sha256']=observed['photo_sha256'];record['observed']=observed
path.write_text(json.dumps(record,indent=2)+'\n')
print('Recorded recovery observation:',observed['photo_sha256'])
print('File qualification result:',record['file_operation_passed'])
