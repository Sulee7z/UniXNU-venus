#!/usr/bin/env python3
"""Derive the phone profile's exact kernel and ADT facts from the documented IPSW."""
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import subprocess

ROOT=Path('/mnt/g/UniXNU-Port')
sys.path.insert(0,str(ROOT/'sources/UniXNU-guide/scripts'))
from unixnu.ipsw import kernelcache,im4p_payload
from unixnu import udif
from unixnu.util import lzfse
INPUT=ROOT/'artifacts/venus-iphone-inputs/20H392'
report=json.loads((INPUT/'report.json').read_text())
for row in report['extracted'].values():
    path=Path(row['path'])
    with path.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256']


class Context:
    board={'kernel':{'prelink':{}}}


class Source:
    cache=INPUT
    @staticmethod
    def read(name):return Path(report['extracted'][name]['path']).read_bytes()


kernel=kernelcache(Context(),Source())
raw=kernel.read_bytes()
assert struct.unpack_from('<III',raw)==(0xfeedfacf,0x100000c,0),'Target kernel must be ordinary ARM64'
version=re.search(rb'Darwin Kernel Version [^\0]{1,300}',raw)
assert version
text=version[0].decode()
xnu=re.search(r'xnu-([0-9.]+)',text).group(1)
adt=im4p_payload(Source.read('DeviceTree'))
if adt[:4] in (b'bvx2',b'bvxn'):
    packed=INPUT/'DeviceTree.lzfse';decoded=INPUT/'DeviceTree.decompressed'
    packed.write_bytes(adt)
    subprocess.run([lzfse(),'-decode','-i',str(packed),'-o',str(decoded)],check=True)
    adt=decoded.read_bytes()


def parse(at):
    count,children=struct.unpack_from('<II',adt,at);at+=8
    props={}
    for _ in range(count):
        name,length=struct.unpack_from('<32sI',adt,at);at+=36;length&=0x7fffffff
        name=name.split(b'\0')[0].decode();props[name]=adt[at:at+length];at+=(length+3)&~3
    sub=[]
    for _ in range(children):
        node,at=parse(at);sub.append(node)
    return {'properties':props,'children':sub},at


tree,end=parse(0)
assert end==len(adt)
product=next(node for node in tree['children'] if node['properties'].get('name')==b'product\0')
identity={}
for table,properties in (('root',tree['properties']),('product',product['properties'])):
    wanted=['model','target-type'] if table=='root' else ['product-name','product-description','artwork-device-idiom',
        'artwork-device-subtype','artwork-scale-factor','artwork-display-gamut','compatible-device-fallback','thin-bezel']
    identity[table]={}
    for key in wanted:
        value=properties.get(key)
        if value is not None:identity[table][key]=value.hex()
volumes={}
for name in ('OS','Cryptex1,SystemOS'):
    image=udif.Image(Path(report['extracted'][name]['path']))
    volumes[name]={'raw_bytes':image.size,'dmg_sha256':report['extracted'][name]['sha256']}
result={'target_product':'iPhone10,3','target_version':'16.7.16','target_build':'20H392',
        'kernel_version_string':text,'xnu_version':xnu,'kernel_sha256':hashlib.sha256(raw).hexdigest(),
        'cpu_subtype':0,'adt_identity_properties_hex':identity,'volumes':volumes,
        'phone_operations':False,'native_kernel_built':False,'driver_abi_verified':False}
(INPUT/'profile-facts.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
