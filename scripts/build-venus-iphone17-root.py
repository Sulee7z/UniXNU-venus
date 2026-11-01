#!/usr/bin/env python3
"""Build the iPhone11,8 iOS17 SHNGROOT image from checked DMGs, with read-only APFS identity."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import uuid

ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus'
INPUT=ROOT/'artifacts/venus-iphone17-inputs/21H16';OUT=ROOT/'artifacts/venus-iphone17-root/21H16'
sys.path.insert(0,str(ROOT/'sources/UniXNU-guide/scripts'))
from unixnu import userdata
from unixnu.udif import Image

metadata=json.loads((INPUT/'report.json').read_text());facts=json.loads((INPUT/'profile-facts.json').read_text())
for component in ('OS','Cryptex1,SystemOS'):
    row=metadata['extracted'][component]
    with Path(row['path']).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256']

# Decode only the OS disk for read-only APFS identity. Keep this large scratch
# outside G:; the root builder reads the checked DMGs independently.
scratch=Path('/root/unixnu-build/venus-iphone17-os.raw')
if not scratch.exists():
    image=Image(Path(metadata['extracted']['OS']['path']))
    temporary=scratch.with_suffix('.partial');digest=hashlib.sha256();done=0
    with temporary.open('wb') as target:
        for data in image.blocks():target.write(data);digest.update(data);done+=len(data)
        target.flush();os.fsync(target.fileno())
    assert done==image.size,temporary
    temporary.replace(scratch)
with scratch.open('rb') as stream:
    first=stream.read(4096)
    if first[32:36]==b'NXSB':container_offset=0
    elif first[512:520]==b'EFI PART':
        entries_lba,count,width=struct.unpack_from('<QII',first,512+72)
        assert width==128 and 0<count<=4096
        stream.seek(entries_lba*512);entries=stream.read(count*width)
        found=[]
        for index in range(count):
            entry=entries[index*128:(index+1)*128]
            if entry[:16]==uuid.UUID('7C3457EF-0000-11AA-AA11-00306543ECAC').bytes_le:
                start,end=struct.unpack_from('<QQ',entry,32);found.append((start*512,(end-start+1)*512))
        assert len(found)==1,found;container_offset=found[0][0]
    else:raise SystemExit('OS disk is neither APFS nor GPT')
    module_path=ROOT/'sources/UniXNU-zeta-reference/scripts/zeta_apfs_image.py'
    spec=importlib.util.spec_from_file_location('apfs_readonly',module_path);apfs=importlib.util.module_from_spec(spec);spec.loader.exec_module(apfs)
    container=apfs.Container(stream,container_offset);volumes=list(container.volumes())
    assert len(volumes)==1,'OS identity requires one volume'
    volume_uuid=str(uuid.UUID(bytes=volumes[0].superblock[0xf0:0x100])).upper()
    volume_info={'volume_uuid':volume_uuid,'volume_name':volumes[0].name,'xid':volumes[0].xid,
                 'fs_flags':volumes[0].fs_flags,'container_offset':container_offset,
                 'apfs_reader_source_sha256':hashlib.sha256(module_path.read_bytes()).hexdigest()}
facts['volumes']['OS']['volume_uuid']=volume_uuid;facts['volumes']['OS']['container_offset']=container_offset
(INPUT/'profile-facts.json').write_text(json.dumps(facts,indent=2)+'\n')

class PreparedIpsw:
    remote=True
    def __init__(self,ctx):pass
    def extract(self,component):return Path(metadata['extracted'][component]['path'])

class Context:
    work=OUT
    board={'userdata':{'partition':'unixnu','geometry_verified':True,
        'first_lba':44881664,'last_lba':61658879,'lba_bytes':4096,
        'windows':[{'name':'OS','component':'OS'},{'name':'SystemOS','component':'Cryptex1,SystemOS'}]}}

assert not (OUT/'userdata/userdata-root.img').exists(),'Preserve an existing iPhone17 root build'
userdata.Ipsw=PreparedIpsw
image=userdata.build(Context())
report=json.loads(image.with_suffix('.json').read_text())
assert report['image_bytes']==image.stat().st_size
with image.open('rb') as stream:
    header=stream.read(4096);assert header[:8]==b'SHNGROOT' and hashlib.sha256(header[:4064]).digest()==header[4064:]
    version,count,total=struct.unpack_from('<IIQ',header,8);assert (version,count,total)==(1,2,report['image_bytes'])
with image.open('rb') as whole:assert hashlib.file_digest(whole,'sha256').hexdigest()==report['image_sha256']
summary={'product':'iPhone11,8','version':'17.7','build':'21H16','root_image':str(image),
    'root_bytes':report['image_bytes'],'root_sha256':report['image_sha256'],'volume_uuid':volume_uuid,
    'volume_info':volume_info,'target_kernel_xnu':'10063.142.1.700.5','current_native_xnu':'10063.141.1',
    'source_report':str(INPUT/'report.json'),'native_kernel_built':False,'prelink_arm64e_qualified':False,
    'data_seed_created':False,'phone_operations':False,'iphone_userland_booted':False}
(OUT/'root-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ('root_image','root_bytes','root_sha256','volume_uuid')},indent=2))
