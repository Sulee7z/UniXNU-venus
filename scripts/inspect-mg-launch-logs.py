#!/usr/bin/env python3
"""Read launchd's plain logs from an existing Data capture, host-only."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import data_store_view as store

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run',type=Path,required=True)
args=parser.parse_args()
args.run=args.run.resolve()
if sys.platform=='win32' and args.run.drive.upper()!='G:':parser.error('Use G:')
if sys.platform!='win32' and not args.run.is_relative_to(Path('/mnt/g')):parser.error('Use G: mount')
view,apfs,volume=store.open_volume(args.run,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT)
try:
    out=args.run/'mg-launch-logs';out.mkdir(exist_ok=False)
    report={'directories':{},'files':{},'scope':'Captured file contents; wall clock alone does not identify a boot.'}
    for directory in ('/log/com.apple.xpc.launchd','/logs/com.apple.xpc.launchd'):
        try:
            entries=store.list_directory(apfs,volume,directory);report['directories'][directory]=entries
            for entry in entries:
                if entry['kind']!='file' or not entry['name'].endswith(('.log','.log.1','.log.2')):continue
                path=directory+'/'+entry['name'];data=store.read_file(view,apfs,volume,path,limit=4<<20)
                filename=path.replace('/','_').lstrip('_');(out/filename).write_bytes(data)
                report['files'][path]={'bytes':len(data),'sha256':store.sha(out/filename),'output':filename}
        except ValueError as error:report['directories'][directory]={'error':str(error)}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
finally:view.close()
