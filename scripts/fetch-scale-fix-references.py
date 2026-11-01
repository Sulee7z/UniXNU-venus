#!/usr/bin/env python3
"""Pin same21H461 successful port documentation/display fixes for review."""
import hashlib
import json
from pathlib import Path
import re
import urllib.request

ROOT=Path(__file__).resolve().parents[3]
REPOS=[('umi','reAAAq/UniXNU-umi','3eb72578597d2ca16471b172d45eddc096a34a04'),
       ('tb128fu','xVanTuring/UniXNU-tb128fu','a9c3863dedbee6f319bff16d3b609ec6cef409bf')]
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'UniXNU-venus-scale-review'}),timeout=60) as stream:return stream.read()
for name,repo,pin in REPOS:
    tree=json.loads(fetch('https://api.github.com/repos/'+repo+'/git/trees/'+pin+'?recursive=1'))
    if tree.get('truncated'):raise ValueError('Incomplete source tree')
    out=ROOT/'references'/('scale-fix-'+name)/pin;out.mkdir(parents=True,exist_ok=False)
    (out/'tree.json').write_text(json.dumps(tree,indent=2)+'\n',encoding='utf-8');files={}
    for row in tree['tree']:
        path=row['path']
        if row['type']!='blob':continue
        wanted=path in ('README.md','AGENTS.md','board.toml','source-lock.json','docs/validation.json') or (
            path.startswith('docs/') and path.endswith('.md')) or (
            re.search(r'scale|gestalt|LegacyDisplay|DisplayProbe|seed-data|build-os-root',path,re.I) and
            path.endswith(('.py','.c','.cpp','.h','.patch','.json')))
        if not wanted or row['size']>2<<20:continue
        target=out/path
        if not target.resolve().is_relative_to(out.resolve()):raise ValueError('Unsafe source path')
        data=fetch('https://raw.githubusercontent.com/'+repo+'/'+pin+'/'+path)
        identity=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if len(data)!=row['size'] or identity!=row['sha']:raise ValueError('Blob mismatch '+path)
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        files[path]={'bytes':len(data),'git_blob_sha1':identity,'sha256':hashlib.sha256(data).hexdigest()}
    receipt={'repo':repo,'revision':pin,'tree_sha':tree['sha'],'files':files,'scope':'Pinned source/docs, not transferred board or device qualification.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'repo':repo,'revision':pin,'files':list(files),'receipt':str(out/'receipt.json')},indent=2))
