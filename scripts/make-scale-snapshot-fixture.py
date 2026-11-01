#!/usr/bin/env python3
"""Build a bounded QEMU APFS fixture from captured metadata and exact MG data.

All live file-data extents except the MG cache are zeroed. Metadata, allocation
maps and non-file pages remain intact. This is explicitly NOT a usable copy of
the user volume, production seed or device write image.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
sys.path.insert(0,str(DEVICE/'scripts'));import data_store_view as store
RUN=ROOT/'artifacts/venus-data-forensics/read-20261029T074228Z'
OUT=ROOT/'artifacts/venus-scale-refresh-012/snapshot-fixture';OUT.mkdir(parents=True,exist_ok=False)
view,apfs,volume=store.open_volume(RUN,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT)
try:
    excluded=set();seen=set();extent_records=0
    def walk(oid):
        global extent_records
        if oid in seen:raise ValueError('Cyclic tree')
        seen.add(oid)
        physical=volume.container.omap_lookup(volume.omap_root,oid,volume.xid)
        level,entries=volume.container.node(physical)
        for key,value in entries:
            if level:walk(struct.unpack_from('<Q',value)[0]);continue
            if struct.unpack_from('<Q',key)[0]>>60!=apfs.TYPE_FILE_EXTENT:continue
            length,block,crypto=struct.unpack('<QQQ',value);length&=0x00ffffffffffffff
            if crypto or not length or length%4096 or block+length//4096>view.pages:raise ValueError('Unsupported file extent')
            if block:excluded.update(range(block,block+length//4096))
            extent_records+=1
    walk(volume.root_tree)
    path='/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist'
    info=store.file_info(apfs,volume,path);cache=store.read_file(view,apfs,volume,path)
    retained=set()
    for key,value in volume.records(info['private_id'],apfs.TYPE_FILE_EXTENT):
        length,block,crypto=struct.unpack('<QQQ',value);length&=0x00ffffffffffffff
        if crypto:raise ValueError('Encrypted cache extent')
        retained.update(range(block,block+length//4096))
    candidates=set()
    for start,data in view.seed:candidates.update(range(start//4096,(start+len(data))//4096))
    for row in view.index['runs']:candidates.update(range(row['first_page'],row['first_page']+row['blocks']))
    extents=[];total=32
    for page in sorted(candidates):
        if page in excluded and page not in retained:continue
        data=view.page(page)
        if not any(data):continue
        at=page*4096
        if extents and extents[-1][0]+len(extents[-1][1])==at:extents[-1][1].extend(data)
        else:extents.append((at,bytearray(data)));total+=16
        total+=4096
        if total>256<<20:raise ValueError('Fixture exceeds packed loader bound')
    encoded=struct.pack('<8sIIQQ',b'DBRDISK1',1,4096,view.length,len(extents))
    encoded+=b''.join(struct.pack('<QQ',at,len(data)) for at,data in extents)+b''.join(bytes(data) for at,data in extents)
    (OUT/'metadata-and-MG.dbr').write_bytes(encoded)
    codec=store.module(ROOT/'sources/UniXNU-guide/drivers/DarwinBoot/Test/packed_ramdisk.py','fixture_packed')
    description,header=codec.inspect(OUT/'metadata-and-MG.dbr')
    if description['bytes']!=view.length or header[32:36]!=b'NXSB':raise ValueError('Invalid fixture')
    result={'snapshot':str(RUN),'checkpoint_xid':volume.xid,'fixture':str(OUT/'metadata-and-MG.dbr'),
        'fixture_metadata':description,'live_extent_records':extent_records,'excluded_live_file_pages':len(excluded),
        'retained_cache_pages':sorted(retained),'retained_cache_sha256':hashlib.sha256(cache).hexdigest(),
        'scope':'QEMU-only snapshot metadata/allocation + exact MG file data, other live files zeroed. No device/production use; no source snapshot modifications.'}
    (OUT/'report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
finally:view.close()
