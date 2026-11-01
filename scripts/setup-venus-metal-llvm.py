#!/usr/bin/env python3
"""Extract SHA-bound LLVM21 tools into an isolated G-backed prefix."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

ROOT=Path('/mnt/g/UniXNU-Port');OUT=ROOT/'artifacts/venus-metal-development/llvm21';OUT.mkdir(exist_ok=True)
PREFIX=Path('/root/unixnu-build/venus-metal-tools/llvm21');PREFIX.mkdir(exist_ok=True)
BASE='https://apt.llvm.org/noble/'
def fetch(url):
    with urllib.request.urlopen(url,timeout=120) as f:return f.read()
release=fetch(BASE+'dists/llvm-toolchain-noble-21/Release');(OUT/'Release').write_bytes(release)
path='main/binary-amd64/Packages.gz'
rows=[line.split() for line in release.decode().split('SHA256:\n',1)[1].splitlines()]
expected=next(parts[0] for parts in rows if len(parts)==3 and parts[2]==path)
data=fetch(BASE+'dists/llvm-toolchain-noble-21/'+path)
if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Package index SHA mismatch')
(OUT/'Packages.gz').write_bytes(data);packages={}
for block in gzip.decompress(data).decode().split('\n\n'):
    fields={}
    for line in block.splitlines():
        if line and not line[0].isspace() and ': ' in line:
            key,value=line.split(': ',1);fields[key]=value
    if 'Package' in fields:packages[fields['Package']]=fields
records=[]
for name in ('libllvm21','llvm-21','llvm-21-runtime','llvm-21-tools','lld-21'):
    row=packages[name];archive=OUT/row['Filename'].rsplit('/',1)[1]
    if not archive.exists():archive.write_bytes(fetch(BASE+row['Filename']))
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=row['SHA256']:raise ValueError('Package SHA mismatch')
    subprocess.run(['dpkg-deb','--extract',str(archive),str(PREFIX)],check=True)
    records.append({'package':name,'version':row['Version'],'sha256':row['SHA256'],'url':BASE+row['Filename']})
env={**os.environ,'LD_LIBRARY_PATH':str(PREFIX/'usr/lib/x86_64-linux-gnu')}
record={'prefix':str(PREFIX),'packages':records,'llvm_as':subprocess.check_output([str(PREFIX/'usr/lib/llvm-21/bin/llvm-as'),'--version'],env=env,text=True).strip()}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
