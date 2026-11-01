#!/usr/bin/env python3
"""Verify requested zeta graphics source blobs, using existing mirror where exact."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[3];PIN='eb489285a1d9153872f00c93ebb519a269b249b5'
OUT=ROOT/'references/zeta-metal'/PIN;OUT.mkdir(parents=True,exist_ok=False)
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'UniXNU-venus-metal-port'}),timeout=60) as f:return f.read()
tree=json.loads(fetch('https://api.github.com/repos/none24smu/UniXNU-zeta/git/trees/'+PIN+'?recursive=1'))
if tree.get('truncated'):raise ValueError('Incomplete Git tree')
(OUT/'tree.json').write_text(json.dumps(tree,indent=2)+'\n',encoding='utf-8');files={}
for row in tree['tree']:
    path=row['path']
    if row['type']!='blob':continue
    selected=path in ('README.md','board.toml','unixnu.lock','GRAPHICS-LIVE-FIXES.md','GRAPHICS-BACKEND-EVALUATION.md','GRAPHICS-WALLPAPER-DIAGNOSIS.md','package/graphics-userland-profile.json') or path.startswith('package/NativeMetal-') or path.startswith('tests/linked-render')
    if not selected or row['size']>2<<20:continue
    local=ROOT/'sources/UniXNU-zeta-none24smu'/path
    data=local.read_bytes() if local.exists() else fetch('https://raw.githubusercontent.com/none24smu/UniXNU-zeta/'+PIN+'/'+path)
    identity=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    if len(data)!=row['size'] or identity!=row['sha']:raise ValueError('Mirror blob mismatch '+path)
    target=OUT/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    files[path]={'bytes':len(data),'git_blob_sha1':identity,'sha256':hashlib.sha256(data).hexdigest()}
record={'repo':'none24smu/UniXNU-zeta','revision':PIN,'tree':tree['sha'],'files':files,
        'native_base':'35c384e84266343991fd14706e8c651f7d2e09ed','native_metal':'ff0c70d7249a04ee381d9854c214069324a34d5c',
        'scope':'Requested source verified; board is A660/SM8350 but OS26 frontend changes require iPadOS17 ABI review.'}
(OUT/'receipt.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'revision':PIN,'files':len(files),'receipt':str(OUT/'receipt.json')},indent=2))
