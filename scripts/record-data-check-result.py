#!/usr/bin/env python3
"""Bind a manually transcribed fixed Data result row to its existing boot record."""
import argparse
import hashlib
import json
from pathlib import Path
import re

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out-name',default='venus-data-check-001')
parser.add_argument('--phase',type=int,choices=(1,2),required=True)
parser.add_argument('--photo',type=Path,required=True)
parser.add_argument('--seconds',type=int,required=True)
parser.add_argument('--line',required=True)
parser.add_argument('--detail',action='append',default=[],help='Complete DATA DEV/IO/SYNC line; contract2 requires all three')
args = parser.parse_args()
assert args.out_name.startswith('venus-data-check-') and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.out_name)
OUT=ROOT/'artifacts'/args.out_name


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


plan = json.loads((OUT/'plan.json').read_text())
label = 'write' if args.phase==1 else 'read'
prefix='data-check' if args.out_name=='venus-data-check-001' else args.out_name.removeprefix('venus-')
path = DEVICE/f'evidence/{prefix}-{label}-phone.json'
record = json.loads(path.read_text())
candidate = json.loads((OUT/'candidate.json').read_text())
assert sha(OUT/label/'boot-venus-unixnu.img')==record['image_sha256']==candidate['images'][label]['sha256']
match = re.fullmatch(r'DATA CHECK phase=(\d+) step=(\d+) rc=(-?\d+) match=(\d+) bytes=(\d+) token=([0-9a-f]{8}) store=(\d+)',args.line)
assert match, 'Transcribe the complete fixed result row'
phase,step,rc,equal,count,token,store = match.groups()
values = {'phase':int(phase),'step':int(step),'rc':int(rc),'match':int(equal),'bytes':int(count),
          'token_prefix':token,'store_state':int(store)}
assert values['phase']==args.phase and token==plan['token'][:8], 'Wrong phase or marker token'
passed = (values['step']==11 and values['rc']==0 and values['match']==1 and values['bytes']==plan['file_bytes'] and
          values['store_state'] in ((2,3) if args.phase==1 else (2,)))
record.update(photos=[str(args.photo)],photo_sha256=sha(args.photo),
              observed={'input_kind':'manual photograph transcription','screen_seconds':args.seconds,
                         'row':args.line,**values},file_operation_passed=passed)
if plan.get('sync_contract')==2:
    patterns={
      'device':r'DATA DEV mount=([0-9a-f]+) data=([0-9a-f]+) parent=([0-9a-f]+) file=([0-9a-f]+) stage=(-?\d+) rc=(-?\d+) ro=(-?\d+)',
      'io':r'DATA IO w=(\d+)>(\d+) fs=(\d+) full=(\d+) runs=(\d+)>(\d+) err=(\d+)',
      'sync':r'DATA SYNC file=(-?\d+) dir=(-?\d+) full=(-?\d+) ufs=(-?\d+) present=(\d+)>(\d+) v=2'}
    detail={}
    for name,pattern in patterns.items():
        matches=[re.fullmatch(pattern,line) for line in args.detail]
        matches=[m for m in matches if m]
        assert len(matches)==1,'Provide exactly one complete '+name+' detail line'
        detail[name]=[int(v,16 if name=='device' and i<4 else 10) for i,v in enumerate(matches[0].groups())]
    device_ok=detail['device'][1]==detail['device'][2]==detail['device'][3] and detail['device'][1]!=0xffffffff and detail['device'][4:]==[4,0,0]
    io_ok=detail['io'][6]==0
    write_ok=args.phase!=1 or (detail['io'][1]>detail['io'][0] and detail['sync'][:4]==[0,0,0,0])
    record['observed']['detail_rows']=args.detail
    record['observed']['detail_values']=detail
    record['observed']['device_identity_passed']=device_ok
    record['observed']['write_sync_evidence_passed']=write_ok if args.phase==1 else None
    passed=passed and device_ok and io_ok and write_ok
    record['file_operation_passed']=passed
if args.phase==1:
    record['pending']=('Confirm the manual restart and authorize the exact read image to finish cross-reboot verification.' if passed else
                       'Inspect the exact write/sync failure; do not repeat or proceed to read qualification automatically.')
    record['scope']=('Exclusive create/file+directory+full+medium sync and same-boot comparison passed' if plan.get('sync_contract')==2 else
                     'Exclusive file creation/write/fsync/close/reopen and same-boot comparison passed') if passed else 'Write-round file verification failed'
    record['cross_reboot_readback_passed']=False
else:
    first = json.loads((DEVICE/f'evidence/{prefix}-write-phone.json').read_text())
    assert first.get('file_operation_passed') and record.get('manual_restart_confirmed'), 'Missing first-round/restart evidence'
    record['cross_reboot_readback_passed']=passed
    record['pending']=None if passed else 'Inspect the exact failure step; do not repeat automatically'
    record['scope']='Known 53-byte marker matched after the confirmed restart with a resumed store' if passed else 'Post-restart readback failed'
record['limits']=['The result row is manually transcribed; the marker comparison is performed by the tested kernel code.',
                  'The kernel monitor/timers continue after the qualification pauses before launchd; a stable result row is expected.',
                  'This is one bounded file test, not complete UFS endurance/error-recovery qualification.']
path.write_text(json.dumps(record,indent=2)+'\n')
print('Recorded',label,'phase; passed:',passed,'photo SHA:',sha(args.photo))
