#!/usr/bin/env python3
"""Read the real iPhone11,8 iOS17 ADT identity and volume sizes from checked inputs."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import struct
import sys

ROOT=Path('/mnt/g/UniXNU-Port');INPUT=ROOT/'artifacts/venus-iphone17-inputs/21H16'
sys.path.insert(0,str(ROOT/'sources/UniXNU-guide/scripts'))
from unixnu.ipsw import im4p_payload
from unixnu import udif
from unixnu.util import lzfse
report=json.loads((INPUT/'report.json').read_text())
for row in report['extracted'].values():
    with Path(row['path']).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256']
adt=im4p_payload(Path(report['extracted']['DeviceTree']['path']).read_bytes())
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
    rows=[]
    for _ in range(children):
        node,at=parse(at);rows.append(node)
    return {'properties':props,'children':rows},at


tree,end=parse(0);assert end==len(adt)
product=next(node for node in tree['children'] if node['properties'].get('name')==b'product\0')
keys=('model','target-type','compatible','product-name','product-description','artwork-device-idiom',
      'artwork-device-subtype','artwork-scale-factor','artwork-display-gamut','compatible-device-fallback','thin-bezel')
identity={}
for node_name,node in (('root',tree),('product',product)):
    identity[node_name]={key:node['properties'][key].hex() for key in keys if key in node['properties']}
volumes={}
for component in ('OS','Cryptex1,SystemOS'):
    image=udif.Image(Path(report['extracted'][component]['path']))
    volumes[component]={'raw_bytes':image.size,'dmg_sha256':report['extracted'][component]['sha256'],
                        'member':report['extracted'][component]['member']}
compat=json.loads((ROOT/'artifacts/venus-iphone17-compat/21H16/report.json').read_text())
result={'product':'iPhone11,8','version':'17.7','build':'21H16','device_class':'n841ap',
    'adt_identity_properties_hex':identity,'volumes':volumes,
    'target_kernel_xnu':'10063.142.1.700.5','original_kernel_arm64e':True,
    'current_native_xnu':'10063.141.1','kernel_sha256':compat['kernelcache_sha256'],
    'decompressed_kernel_sha256':compat['decompressed_kernel_sha256'],
    'phone_operations':False,'native_kernel_built':False,'iphone_userland_booted':False}
(INPUT/'profile-facts.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
