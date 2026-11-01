#!/usr/bin/env python3
"""Verify the actual039 FAT plugin/trust and retained038 kernel/input payload."""
import ast
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib

ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus'
OUT=ROOT/'artifacts/venus-zeta-audit'
PHONE=ROOT/'artifacts/venus-metal-touch-039/phone'
CONTROL=ROOT/'artifacts/venus-metal-touch-038/phone'
ADDON=OUT/'addon039';ENTRY=OUT/'entry039'
sys.path.insert(0,str(DEVICE/'package/Metal13'))
from venus_trust_bundle import entries
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
load=lambda path:json.loads(path.read_text())


def fat(path):
    return subprocess.check_output(['mtype','-i',str(PHONE/'payload.img'),'::/EFI/UniXNU/'+path])


build=load(ENTRY/'report.json')
for path,digest in build['inputs'].items():assert sha(Path(path))==digest
for name,digest in build['objects'].items():assert sha(ENTRY/name)==digest
assert sha(Path(build['frontend']['source']))==build['frontend']['source_sha256']
assert sha(ENTRY/'NativeBridgeMetalFrontend.o')==build['frontend']['object_sha256']
cache_test=load(Path('/root/unixnu-build/venus-zeta-cache039-tests/report.json'))
assert cache_test['passed'] and cache_test['source_sha256']==sha(DEVICE/'package/Metal13/VenusMetalCache.h')
candidate=load(PHONE.parent/'candidate.json')
assert sha(PHONE/'boot-venus-unixnu.img')==candidate['image_sha256']
old=load(CONTROL.parent/'candidate.json')
assert candidate['kernel_sha256']==old['kernel_sha256']=='bd312e850bc3741d27c79cf748990f59fadd5f023c9e66ec424507adb2cd3423'
for name in ('kernel.macho','kernel.macho.adt','scratch-data.img'):
    original=subprocess.check_output(['mtype','-i',str(CONTROL/'payload.img'),'::/EFI/UniXNU/Payloads/'+name])
    assert fat('Payloads/'+name)==original,name
record=load(ADDON/'report.json')
packed=fat('Payloads/kernel.macho.gpuaddon')
assert hashlib.sha256(packed).hexdigest()==record['addon_sha256']
assert packed[:8]==b'NGPUADD2'
count,_,total=struct.unpack_from('<IIQ',packed,8)
assert count==5==len(record['files']) and total==len(packed)
at=24;decoded={}
for _ in range(count):
    length,mode,size,compressed=struct.unpack_from('<IIQQ',packed,at);at+=24
    name=packed[at:at+length];at+=(length+7)&~7
    assert name.endswith(b'\0')
    stream=zlib.decompressobj();data=stream.decompress(packed[at:at+compressed])+stream.flush();at+=(compressed+7)&~7
    assert stream.eof and not stream.unused_data and len(data)==size
    full='/private/var/ngpu/'+name[:-1].decode()
    expected=next(row for row in record['files'] if row['path']==full)
    assert mode==int(expected['mode'],8) and hashlib.sha256(data).hexdigest()==expected['sha256']
    decoded[full]=data
assert at==len(packed)
plugin=decoded['/private/var/ngpu/addons/NativeAdrenoMetal.bundle/NativeAdrenoMetal']
for word in (b'CA_DISABLE_FRAMEBUFFER_COMPRESSION',b'CAEnableIOSurfaceCompression',b'venus-metal: process=',b'no usable device/cache candidate'):
    assert word in plugin,'Compiled entry missing: '+str(word)
parsed=ast.parse((DEVICE/'scripts/link-venus-metal-plugin.py').read_text())
node=next(node for node in parsed.body if isinstance(node,ast.FunctionDef) and node.name=='verify')
namespace={'hashlib':hashlib,'struct':struct}
exec(compile(ast.Module(body=[node],type_ignores=[]),'signature-verifier','exec'),namespace)
verified={}
for name,kind,key in (('NativeAdrenoMetal',8,'plugin'),('libvulkan_freedreno.dylib',6,'turnip')):
    path=ADDON/'NativeAdrenoMetal.bundle'/name
    assert path.read_bytes()==decoded['/private/var/ngpu/addons/NativeAdrenoMetal.bundle/'+name]
    verified[key]=namespace['verify'](path,kind)
    assert verified[key]['sha256']==record['binaries'][key]['sha256']
trust=fat('Payloads/kernel.macho.trustcache')
assert hashlib.sha256(trust).hexdigest()==record['trust_sha256'] and struct.unpack_from('<II',trust)==(1,8)
merged=entries(trust)
base=subprocess.check_output(['mtype','-i',str(ROOT/'artifacts/venus-scale-refresh-012/phone/payload.img'),'::/EFI/UniXNU/Payloads/kernel.macho.trustcache'])
original=entries(base)
assert all(merged[key]==attrs for key,attrs in original.items())
for details in verified.values():assert merged[bytes.fromhex(details['directory']['cdhash'])]==bytes([2,0,0,0])
assert len(merged)==len(original)+2==2556
reference=load(OUT/'reference/manifest.json')
assert reference['verified'] and reference['file_count']==188
report={'passed':True,'image_sha256':candidate['image_sha256'],'kernel_sha256':candidate['kernel_sha256'],
    'kernel_adt_seed_identical_to038':True,'frontend_object_retained':True,
    'original_trust_entries_preserved':len(original),'static_module_entries':len(merged),
    'plugin_signature':verified['plugin'],'turnip_signature':verified['turnip'],
    'source_pin':reference['revision'],'source_manifest_sha256':sha(OUT/'reference/manifest.json'),
    'cache_tests_report_sha256':sha(Path('/root/unixnu-build/venus-zeta-cache039-tests/report.json')),
    'gpu_device_open_verified':False,'gpu_pixels_verified':False,'iphone_userland_booted':False,
    'phone_operations':False,'qemu_full_systemos_verified':False}
(OUT/'qualification039.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS:039 actual FAT/signed plugin/single static trust, all2554 original entries, and unchanged038 kernel/ADT/seed')
