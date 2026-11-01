#!/usr/bin/env python3
"""Inspect a real iOS17 iPhone kernel against the retained native XNU prelink interface."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import struct
import sys
import urllib.request
import zipfile

ROOT=Path('/mnt/g/UniXNU-Port')
TREE=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root/tree')
sys.path.insert(0,str(ROOT/'sources/UniXNU-guide/scripts'))
sys.path.insert(0,str(TREE/'kits/XnuPrelink'))
from unixnu.ipsw import RangeFile,kernelcache
from native_prelink import macho

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
with urllib.request.urlopen('https://api.ipsw.me/v4/device/iPhone11,8?type=ipsw',timeout=60) as response:
    metadata=json.load(response)
choices=[row for row in metadata['firmwares'] if re.fullmatch(r'17(?:\.[0-9]+)+',row['version'])]
assert choices,'No stable iOS17 iPhone XR record'
selected=max(choices,key=lambda row:tuple(int(value) for value in row['version'].split('.')))
version_number=selected['version'];build=selected['buildid']
out=args.output/build;out.mkdir(parents=True,exist_ok=True)
url=selected['url'];assert url.startswith('https://updates.cdn-apple.com/')
print('Selected actual iPhone XR target:',version_number,build,flush=True)
with RangeFile(url) as remote,zipfile.ZipFile(remote) as archive:
    manifest_bytes=archive.read('BuildManifest.plist');manifest=plistlib.loads(manifest_bytes)
    assert manifest['ProductVersion']==version_number and manifest['ProductBuildVersion']==build
    assert 'iPhone11,8' in manifest['SupportedProductTypes']
    identities=[row for row in manifest['BuildIdentities'] if row['Info']['DeviceClass']=='n841ap' and row['Info']['RestoreBehavior']=='Erase']
    assert len(identities)==1
    identity=identities[0]
    member=identity['Manifest']['KernelCache']['Info']['Path']
    destination=out/Path(member).name
    digest=hashlib.sha256();size=0
    if destination.exists():
        receipt=json.loads(destination.with_suffix('.json').read_text())
        assert receipt['source']==url and receipt['member']==member
        with destination.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==receipt['sha256']
    else:
        temporary=destination.with_suffix('.partial');assert not temporary.exists()
        with archive.open(member) as source,temporary.open('xb') as target:
            while chunk:=source.read(8<<20):target.write(chunk);digest.update(chunk);size+=len(chunk)
        assert size==archive.getinfo(member).file_size
        temporary.rename(destination)
        receipt={'source':url,'member':member,'bytes':size,'sha256':digest.hexdigest(),'zip_crc_verified':True}
        destination.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (out/'BuildManifest.plist').write_bytes(manifest_bytes)


class Context:
    board={'kernel':{'prelink':{}}}


class Source:
    cache=out
    @staticmethod
    def read(name):
        assert name=='KernelCache'
        return destination.read_bytes()


kernel=kernelcache(Context(),Source());raw=kernel.read_bytes()
magic,cpu,subtype=struct.unpack_from('<III',raw)
assert magic==0xfeedfacf and cpu==0x100000c
version=re.search(rb'Darwin Kernel Version [^\0]{1,300}',raw)
assert version
accepted=False;failure=None
try:macho(raw);accepted=True
except ValueError as error:failure=str(error)
report={'product':'iPhone11,8','version':version_number,'build':build,'device_class':'n841ap',
    'source':url,'kernel_member':member,'kernelcache_sha256':receipt['sha256'],
    'decompressed_kernel_sha256':hashlib.sha256(raw).hexdigest(),
    'original_kernel_version':version[0].decode(),'cpu_subtype':subtype,
    'native_xnu_retained_version':'10063.141.1','current_prelink_accepts_kernel':accepted,
    'prelink_refusal':failure,'root_or_systemos_downloaded':False,'phone_operations':False,
    'scope':'Real iOS17 target kernel architecture/version check; not a native/Apple component ABI or userspace boot qualification.'}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
