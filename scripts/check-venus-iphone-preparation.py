#!/usr/bin/env python3
"""Check the staged phone identity, source pin and actual SHNGROOT window hashes."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tomllib

ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus'
INPUT=ROOT/'artifacts/venus-iphone-inputs/20H392'
OUT=ROOT/'artifacts/venus-iphone-root/20H392'
profile=tomllib.loads((DEVICE/'profiles/ios-16.7.16-20H392/profile.toml').read_text())
facts=json.loads((INPUT/'profile-facts.json').read_text())
inputs=json.loads((INPUT/'report.json').read_text())
assert profile['ipsw']['product']==facts['target_product']=='iPhone10,3'
assert profile['ipsw']['version']==facts['target_version']=='16.7.16'
assert profile['ipsw']['build']==facts['target_build']=='20H392'
assert profile['kernel']['prelink']['kernelcache_sha256']==facts['kernel_sha256']
revision=subprocess.check_output(['git','-C','/root/unixnu-build/venus-iphone-xnu-8796.141.3','rev-parse','HEAD'],text=True).strip()
assert revision==profile['os']['xnu_revision']
identity=facts['adt_identity_properties_hex']
for key,value in profile['adt']['root']['string'].items():assert (value.encode()+b'\0').hex()==identity['root'][key]
for key in ('product-name','product-description','artwork-device-idiom','compatible-device-fallback'):
    assert (profile['adt']['product']['string'][key].encode()+b'\0').hex()==identity['product'][key]
for key,value in profile['adt']['product']['u32'].items():assert struct.pack('<I',value).hex()==identity['product'][key]
assert profile['adt']['buttons']['u32']['home-button-type']==2
assert 'menu' not in profile['adt']['buttons']['strings']['button-names']
for row in inputs['extracted'].values():
    assert profile['ipsw']['sha256'][Path(row['member']).name]==row['sha256']
image=OUT/'userdata/userdata-root.img'
report=json.loads(image.with_suffix('.json').read_text())
assert image.stat().st_size==report['image_bytes']<=68719476736
with image.open('rb') as stream:
    header=stream.read(4096)
    assert header[:8]==b'SHNGROOT' and hashlib.sha256(header[:4064]).digest()==header[4064:]
    version,count,total=struct.unpack_from('<IIQ',header,8)
    assert (version,count,total)==(1,2,report['image_bytes'])
    for index,expected in enumerate(report['windows']):
        name,offset,size,block,flags,digest,reserved=struct.unpack_from('<32sQQII32s40s',header,24+128*index)
        assert name.rstrip(b'\0').decode()==expected['name'] and offset==expected['offset'] and size==expected['size']
        assert block==512 and flags==1 and not any(reserved)
        stream.seek(offset);actual=hashlib.sha256();remaining=size
        while remaining:
            chunk=stream.read(min(8<<20,remaining));assert chunk
            actual.update(chunk);remaining-=len(chunk)
        assert actual.digest()==digest and actual.hexdigest()==expected['sha256']
with image.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==report['image_sha256']
result={'prepared_inputs_verified':True,'phone_identity_verified_against_original_adt':True,
    'root_manifest_and_all_window_hashes_verified':True,'root_bytes':report['image_bytes'],
    'root_sha256':report['image_sha256'],'profile_sha256':hashlib.sha256((DEVICE/'profiles/ios-16.7.16-20H392/profile.toml').read_bytes()).hexdigest(),
    'source_xnu_revision':revision,'original_kernel_version':facts['kernel_version_string'],
    'native_kernel_built':False,'ios16_driver_abi_verified':False,'matching_data_seed_created':False,
    'boot_candidate_ready':False,'phone_operations':False,
    'remaining_requirements':['iOS16-versioned native kernel/OS patches and prelink closure',
        'iOS16 storage/display/HID/Metal ABI bindings instead of the currently linked iOS17 imports',
        'A Data seed matched to the new iOS16 root and independent persistence identity']}
(OUT/'preparation-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
