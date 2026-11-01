#!/usr/bin/env python3
"""Record a manually transcribed normal-boot photo against its one-shot image."""
import argparse
import hashlib
import json
from pathlib import Path
DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--photo',required=True,type=Path)
parser.add_argument('--seconds',required=True,type=int)
parser.add_argument('--processes',required=True,type=int)
parser.add_argument('--last-stage',required=True)
parser.add_argument('--signature-accepted',action='store_true')
parser.add_argument('--swaps',required=True,type=int)
parser.add_argument('--copies',required=True,type=int)
parser.add_argument('--failed-exits',required=True,type=int)
parser.add_argument('--ufs-failures',required=True,type=int)
parser.add_argument('--integrity-failures',required=True,type=int)
parser.add_argument('--failure',action='append',default=[],help='Verbatim visible process failure row')
parser.add_argument('--free-pages',type=int)
parser.add_argument('--ufs-verified-blocks',type=int)
parser.add_argument('--stalled-confirmed',action='store_true',help='User confirms this remained the final unchanged screen')
args=parser.parse_args()
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
path=DEVICE/'evidence/userspace-phone.json'
record=json.loads(path.read_text(encoding='utf-8'))
candidate=json.loads((ROOT/'artifacts/venus-userspace-001/candidate.json').read_text(encoding='utf-8'))
assert record['image_sha256']==candidate['image_sha256']==sha(ROOT/'artifacts/venus-userspace-001/phone/boot-venus-unixnu.img')
assert record['ram_boot']['attempts_executed']==1
assert min(args.seconds,args.processes,args.swaps,args.copies,args.failed_exits,args.ufs_failures,args.integrity_failures)>=0
observed={'input_kind':'manual photograph transcription','photo':str(args.photo),'photo_sha256':sha(args.photo),
          'screen_seconds':args.seconds,'process_count':args.processes,'last_boot_stage':args.last_stage,
          'launchd_exec_signature_accepted':True if args.signature_accepted else None,'swap_calls':args.swaps,'copy_calls':args.copies,
          'failed_exits':args.failed_exits,'ufs_failures':args.ufs_failures,'ufs_integrity_failures':args.integrity_failures,
          'visible_failure_rows':args.failure,'free_4k_pages':args.free_pages,'ufs_verified_4k_blocks':args.ufs_verified_blocks,
          'spawned_system_services_observed':args.processes>1,
          'screen_stalled_user_confirmed':args.stalled_confirmed,
          'lock_screen_or_desktop_visible':False,'continuing_progress_from_single_photo_confirmed':False}
if str(args.photo) not in record['photos']:record['photos'].append(str(args.photo))
record.setdefault('photo_observations',[]).append(observed)
record.update(observed=observed,photo_sha256=observed['photo_sha256'],
              launchd_progression_observed=bool(record.get('launchd_progression_observed') or args.signature_accepted or args.processes>1),
              lock_screen_or_desktop_observed=False,
              scope=('System-service process spawning observed; usable UI and CPU presentation not yet established' if args.processes>1 else
                     'Launchd exec signature acceptance and early diagnostic state observed; launchd main/service spawning and usable UI not yet established'),
              pending='Compare a later photo for clock, process count, storage activity and frame/swap progression; no automatic restart')
if args.stalled_confirmed:
    record.update(screen_stalled_user_confirmed=True,normal_boot_completed=False,
                  scope='Normal boot spawned system services but the user confirms the87s page stayed frozen; no usable UI',
                  pending='Investigate the stopped screen/boot with targeted host controls; do not keep waiting or automatically reboot')
path.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print('Recorded early userspace photo:',observed['photo_sha256'])
