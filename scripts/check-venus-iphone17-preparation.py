#!/usr/bin/env python3
"""Verify the prepared iPhone17 profile, checked inputs and SHNGROOT windows."""
import hashlib
import json
from pathlib import Path
import plistlib
import struct
import sys
import tomllib

ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus'
INPUT=ROOT/'artifacts/venus-iphone17-inputs/21H16';OUT=ROOT/'artifacts/venus-iphone17-root/21H16'
profile=tomllib.loads((DEVICE/'profiles/ios-17.7-21H16/profile.toml').read_text())
inputs=json.loads((INPUT/'report.json').read_text());facts=json.loads((INPUT/'profile-facts.json').read_text())
summary=json.loads((OUT/'root-summary.json').read_text());root_report=json.loads((OUT/'userdata/userdata-root.json').read_text())
manifest=plistlib.loads((ROOT/'artifacts/venus-iphone17-compat/21H16/BuildManifest.plist').read_bytes())
identity=[r for r in manifest['BuildIdentities'] if r['Info']['DeviceClass']=='n841ap' and r['Info']['RestoreBehavior']=='Erase']
assert len(identity)==1
identity=identity[0]
assert int(identity['ApChipID'],16)==profile['ipsw']['chip_id']==0x8020
assert int(identity['ApBoardID'],16)==profile['ipsw']['board_id']==12
assert profile['ipsw']['product']=='iPhone11,8' and profile['ipsw']['version']=='17.7' and profile['ipsw']['build']=='21H16'
assert profile['ipsw']['sha256']['kernelcache.release.iphone11b']==facts['kernel_sha256']
for row in inputs['extracted'].values():
    path=Path(row['path'])
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    assert profile['ipsw']['sha256'][path.name]==row['sha256']
assert facts['adt_identity_properties_hex']['root']['model']==(profile['adt']['root']['string']['model'].encode()+b'\0').hex()
assert facts['adt_identity_properties_hex']['root']['target-type']==(profile['adt']['root']['string']['target-type'].encode()+b'\0').hex()
for key in ('product-name','product-description','artwork-device-idiom','artwork-display-gamut','compatible-device-fallback'):
    assert facts['adt_identity_properties_hex']['product'][key]==(profile['adt']['product']['string'][key].encode()+b'\0').hex()
for key in ('artwork-device-subtype','artwork-scale-factor','thin-bezel'):
    assert facts['adt_identity_properties_hex']['product'][key]==struct.pack('<I',profile['adt']['product']['u32'][key]).hex()
assert profile['adt']['buttons']['u32']['home-button-type']==2 and 'menu' not in profile['adt']['buttons']['strings']['button-names']
assert profile['os']['root_match_volume_uuid']==facts['volumes']['OS']['volume_uuid']==summary['volume_uuid']
image=OUT/'userdata/userdata-root.img'
assert image.stat().st_size==root_report['image_bytes']==summary['root_bytes']==10297016320
with image.open('rb') as whole:assert hashlib.file_digest(whole,'sha256').hexdigest()==root_report['image_sha256']==summary['root_sha256']
with image.open('rb') as stream:
    header=stream.read(4096);assert header[:8]==b'SHNGROOT' and hashlib.sha256(header[:4064]).digest()==header[4064:]
    version,count,total=struct.unpack_from('<IIQ',header,8);assert (version,count,total)==(1,2,root_report['image_bytes'])
    for index,expected in enumerate(root_report['windows']):
        name,offset,size,block,flags,digest,reserved=struct.unpack_from('<32sQQII32s40s',header,24+128*index)
        assert name.rstrip(b'\0').decode()==expected['name'] and offset==expected['offset'] and size==expected['size']
        stream.seek(offset);actual=hashlib.sha256();remaining=size
        while remaining:
            chunk=stream.read(min(8<<20,remaining));assert chunk;actual.update(chunk);remaining-=len(chunk)
        assert actual.digest()==digest and actual.hexdigest()==expected['sha256']
result={'passed':True,'product':'iPhone11,8','version':'17.7','build':'21H16','chip_id':0x8020,'board_id':12,
    'profile_identity_matches_original_adt':True,'inputs_checked':len(inputs['extracted']),
    'root_image':str(image),'root_bytes':root_report['image_bytes'],'root_sha256':root_report['image_sha256'],
    'volume_uuid':summary['volume_uuid'],'kernelcache_arm64e':True,'native_source':'10063.141.1',
    'target_kernel':'10063.142.1.700.5','prelink_arm64e_qualified':False,'native_kernel_built':False,
    'data_seed_created':False,'iphone_userland_booted':False,'phone_operations':False,
    'scope':'Checked target inputs, identity and media only; no native iOS17 prelink, Data seed, boot or userspace result.'}
(OUT/'preparation-check.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: iPhone11,8 iOS17 profile/inputs/root identity and all SHNGROOT windows checked')
