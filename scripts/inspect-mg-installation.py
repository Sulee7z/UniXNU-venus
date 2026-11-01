#!/usr/bin/env python3
"""Diagnose missing008 query output from the captured Data disk, host-only."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import sys

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
sys.path.insert(0,str(Path(__file__).resolve().parent))
import data_store_view as store

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run',type=Path,required=True)
parser.add_argument('--candidate',type=Path,default=DEVICE/'evidence/mg-query-candidate.json')
args=parser.parse_args()
OUT=args.run/'mg-installation';OUT.mkdir(exist_ok=False)
candidate=json.loads(args.candidate.read_text())
view,apfs,volume=store.open_volume(args.run,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT)
result={'run':str(args.run),'files':{},'directories':{},'capture_verified':view.index.get('complete',False)}
try:
    paths=[row['path'] for row in candidate['installed_files']]+[
        '/private/var/db/com.apple.xpc.launchd/disabled.plist',
        '/private/var/db/diagnostics/logd.0.log','/private/var/db/diagnostics/logd_helper.0.log']
    expected={row['path']:row for row in candidate['installed_files']}
    for path in paths:
        try:
            data=store.read_file(view,apfs,volume,path,limit=1<<20)
            name=path.lstrip('/').replace('/','_')
            (OUT/name).write_bytes(data)
            info=store.file_info(apfs,volume,path)
            row={'state':'extracted','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                 'output':name,'info':info,'verified_mode':oct(info['mode']&0o7777)}
            if path in expected:
                row['matches_payload']=len(data)==expected[path]['bytes'] and row['sha256']==expected[path]['sha256']
            if name.endswith('.plist'):
                row['plist']=plistlib.loads(data)
            result['files'][path]=row
        except ValueError as error:
            result['files'][path]={'state':'absent' if 'has 0 directory records' in str(error) else 'error','detail':str(error)}
    for path in ('/ngpu','/ngpu/bin','/ngpu/daemons','/ngpu/boot','/ngpu/original','/tmp'):
        try:result['directories'][path]=store.list_directory(apfs,volume,path)
        except ValueError as error:result['directories'][path]={'error':str(error)}
    (OUT/'report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for path,row in result['files'].items():
        print(path,row['state'],row.get('matches_payload',''),row.get('detail',''))
    print('Saved:',OUT/'report.json')
finally:view.close()
