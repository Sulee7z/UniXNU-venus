#!/usr/bin/env python3
"""Record actual011 evidence without interpreting a cleaned temporary journal."""
from collections import Counter
import json
from pathlib import Path
import re
import struct
import sys

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
sys.path.insert(0,str(DEVICE/'scripts'));import data_store_view as store
RUN=ROOT/'artifacts/venus-data-forensics/read-20261029T074228Z'
OLD=ROOT/'artifacts/venus-data-forensics/read-20261029T063818Z'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
index=load(RUN/'index.json');candidate=load(DEVICE/'evidence/scale-refresh011-candidate.json')
view,apfs,volume=store.open_volume(RUN,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT)
try:
    if not index['complete'] or (RUN/'metadata.bin').read_bytes()!=(RUN/'metadata-after.bin').read_bytes():raise ValueError('Unstable capture')
    reports=load(RUN/'forensics-v2/report.json');previous=load(OLD/'forensics-v2/report.json')
    path=candidate['cache_paths'][0];current=reports['files'][path];old=previous['files'][path]
    same=current['sha256']==old['sha256'] and current['info']['inode']==old['info']['inode'] and current['info']['private_id']==old['info']['private_id']
    inode_value=volume.records(current['info']['inode'],apfs.TYPE_INODE)[0][1]
    cache_uid,cache_gid=struct.unpack_from('<II',inode_value,72)
    log=RUN/'mg-launch-logs/log_com.apple.xpc.launchd_launchd.log';lines=log.read_text(encoding='utf-8',errors='replace').splitlines()
    if re.findall(r'boot-args = (.*)','\n'.join(lines))!=[candidate['args']]:raise ValueError('Not the011 log')
    exits=[{'line':i,'text':line} for i,line in enumerate(lines,1) if 'com.apple.SpringBoard [' in line and 'exited due to SIGTRAP' in line]
    config=load(ROOT/'artifacts/venus-mg-query-008/launch-cache-inspection-v2/cache-summary.json')
    cleaner=config['config_sections'][0]['plist']['Boot']['dirs_cleaner']
    record={'schema_version':1,'device':'venus','date':'2026-10-29','image_sha256':candidate['image_sha256'],
        'capture':{'run':str(RUN),'pages':index['present_pages'],'runs':len(index['runs']),
            'page_bytes':index['present_pages']*4096,'metadata_sha256':index['metadata_sha256'],'stable_and_hash_verified':True,
            'checkpoint_xid':volume.xid,'phone_written':False,'phone_rebooted':False},
        'photo':{'path':'G:/20261029_154011.JPG','sha256':store.sha(Path('G:/20261029_154011.JPG')),'user_ui_observed':False},
        'cache':{'path':path,'bytes':current['bytes'],'sha256':current['sha256'],'inode':current['info']['inode'],
            'private_id':current['info']['private_id'],'uid':cache_uid,'gid':cache_gid,'mode':oct(current['info']['mode']),
            'same_content_and_inode_as010':same},
        'backup_states':{p:row for p,row in reports['files'].items() if '.venus-scale-011.bak' in p},
        'journal':reports['files']['/tmp/venus-scale-011.jsonl'],
        'launchd':{'args_match011':True,'early_boot_complete':any('Early boot complete.' in s for s in lines),
            'log_sha256':store.sha(log),'first_line':lines[0],'last_line':lines[-1],'sigtrap_exits':exits},
        'original_dirs_cleaner':cleaner,
        'finding':'011 starts normal launchd, but original cache869/content unchanged and backups/journal absent. No completed invalidation evidence.',
        'instrumentation_defect':'Pre-launchd journal in /private/var/tmp lies under the /tmp early dirs_cleaner target. Missing journal cannot diagnose the operation; move it out of temporary storage.',
        'exact_cache_sync_failure_stage':None,'actual_mg_api_result':None,
        'next_action':'Protected db journal/backups, per-step sync results and canonical cache rename durability independent of extra FULLFSYNC telemetry.'}
finally:view.close()
(DEVICE/'evidence/scale-refresh011-readback.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
phone=load(DEVICE/'evidence/scale-refresh011-phone.json')
phone.update(photo_sha256=record['photo']['sha256'],readback_evidence='evidence/scale-refresh011-readback.json',
    journal_verified=False,cache_backup_verified=False,cache_regenerated=False,
    pending='011 cache unchanged; temporary journal unreliable.012 fixes exact shared-cache UID-2/mode0 guard and protected journal/backups, with actual APFS rename verified; new device operation pending.')
(DEVICE/'evidence/scale-refresh011-phone.json').write_text(json.dumps(phone,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'same_cache_inode_and_bytes':same,'journal_state':record['journal']['state'],
    'springboard_sigtrap_exits':len(exits),'dirs_cleaner':cleaner,'evidence':'evidence/scale-refresh011-readback.json'},indent=2))
