#!/usr/bin/env python3
"""Install hash-verified isolated Rust1.98 host/iOS tools in the G-backed distro."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tomllib
import urllib.request

ROOT=Path('/mnt/g/UniXNU-Port');OUT=ROOT/'artifacts/venus-metal-development/toolchain'
PREFIX=Path('/root/unixnu-build/venus-metal-tools/rust-1.98')
OUT.mkdir(parents=True,exist_ok=True);PREFIX.parent.mkdir(parents=True,exist_ok=True)
def download(url):
    request=urllib.request.Request(url,headers={'User-Agent':'UniXNU-venus-metal-build'})
    with urllib.request.urlopen(request,timeout=120) as stream:return stream.read()
manifest_bytes=download('https://static.rust-lang.org/dist/channel-rust-1.98.0.toml')
(OUT/'channel-rust-1.98.0.toml').write_bytes(manifest_bytes);manifest=tomllib.loads(manifest_bytes.decode())
components=[('rustc','x86_64-unknown-linux-gnu'),('cargo','x86_64-unknown-linux-gnu'),
            ('rust-std','x86_64-unknown-linux-gnu'),('rust-std','aarch64-apple-ios')]
records=[]
for name,target in components:
    item=manifest['pkg'][name]['target'][target]
    if not item['available']:raise ValueError('Missing component '+name+'/'+target)
    url=item['xz_url'];expected=item['xz_hash'];archive=OUT/url.rsplit('/',1)[1]
    if not archive.exists():archive.write_bytes(download(url))
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise ValueError('Distribution SHA mismatch')
    directory=OUT/(name+'-'+target)
    if not directory.exists():
        directory.mkdir()
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if not (directory/member.name).resolve().is_relative_to(directory.resolve()):raise ValueError('Unsafe distribution member')
            tar.extractall(directory,filter='data')
    installs=list(directory.glob('*/install.sh'))
    if len(installs)!=1:raise ValueError('Missing installer')
    result=subprocess.run(['bash',str(installs[0]),'--prefix='+str(PREFIX),'--disable-ldconfig'],capture_output=True,text=True,timeout=300)
    (OUT/(name+'-'+target+'-install.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(result.stdout+result.stderr)
    records.append({'component':name,'target':target,'url':url,'sha256':expected})
record={'prefix':str(PREFIX),'manifest_sha256':hashlib.sha256(manifest_bytes).hexdigest(),
        'components':records,'rustc':subprocess.check_output([str(PREFIX/'bin/rustc'),'--version'],text=True).strip(),
        'cargo':subprocess.check_output([str(PREFIX/'bin/cargo'),'--version'],text=True).strip()}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
