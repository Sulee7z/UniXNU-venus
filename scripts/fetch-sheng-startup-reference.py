#!/usr/bin/env python3
"""Pin requested official sheng startup sources and verify Git blob identities."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[3]
REPO='UniXNU/UniXNU-sheng';PIN='08cde20edc3254ed6f7df8d0f5384fb887786e8f'
OUT=ROOT/'references/sheng-startup'/PIN
def fetch(url):
    request=urllib.request.Request(url,headers={'User-Agent':'UniXNU-venus-startup-review'})
    with urllib.request.urlopen(request,timeout=60) as stream:return stream.read()
commit=json.loads(fetch('https://api.github.com/repos/'+REPO+'/commits/HEAD'))
if commit['sha']!=PIN:raise ValueError('Requested repo HEAD changed; review a new exact pin')
tree=json.loads(fetch('https://api.github.com/repos/'+REPO+'/git/trees/'+PIN+'?recursive=1'))
if tree.get('truncated'):raise ValueError('Incomplete Git tree')
OUT.mkdir(parents=True,exist_ok=False)
(OUT/'commit.json').write_text(json.dumps(commit,indent=2)+'\n',encoding='utf-8')
(OUT/'tree.json').write_text(json.dumps(tree,indent=2)+'\n',encoding='utf-8')
wanted={'AGENTS.md','README.md','board.toml','feeds.toml','.gitmodules','unixnu.lock',
    'configs/sheng_defconfig','scripts/build-boot-progress.py','scripts/build-gop-legacy-display.py',
    'scripts/seed-data-skip-setup.py','scripts/read-sheng-log.py','package/BootWatchdogPolicy.c',
    'package/BootProgress.c','package/LegacyDisplayProbe.cpp','package/BootLog.h','package/BootLog.c','porting.toml'}
files={};submodules={}
for row in tree['tree']:
    path=row['path']
    if row['type']=='commit':submodules[path]=row['sha'];continue
    if row['type']!='blob' or not (path in wanted or path.startswith('patches/xnu/')):continue
    target=OUT/path
    if not target.resolve().is_relative_to(OUT.resolve()):raise ValueError('Unsafe path')
    data=fetch('https://raw.githubusercontent.com/'+REPO+'/'+PIN+'/'+path)
    digest=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    if len(data)!=row['size'] or digest!=row['sha']:raise ValueError('Git blob mismatch: '+path)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    files[path]={'bytes':len(data),'git_blob_sha1':digest,'sha256':hashlib.sha256(data).hexdigest()}
record={'repo':REPO,'revision':PIN,'tree_sha':tree['sha'],'files':files,'submodules':submodules,
        'scope':'Fresh requested-repo HEAD/tree, exact blob identities and startup source snapshot; no board/backend adoption or device operation.'}
(OUT/'receipt.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'revision':PIN,'files':list(files),'submodules':submodules,'receipt':str(OUT/'receipt.json')},indent=2))
