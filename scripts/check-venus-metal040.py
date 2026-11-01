#!/usr/bin/env python3
"""Qualify the actual040 payload, bounded Metal diagnostics and unchanged kernel inputs."""
import ast
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib

ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus'
OUT=ROOT/'artifacts/venus-metal-040'
PHONE=ROOT/'artifacts/venus-metal-touch-040/phone'
CONTROL=ROOT/'artifacts/venus-metal-touch-038/phone'
ADDON=OUT/'addon-r2';ENTRY=OUT/'entry-r4';TEST=Path('/root/unixnu-build/venus-metal-diag-040-tests-r2')
sys.path.insert(0,str(DEVICE/'package/Metal13'))
from venus_trust_bundle import entries
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
load=lambda path:json.loads(Path(path).read_text())
fat=lambda name:subprocess.check_output(['mtype','-i',str(PHONE/'payload.img'),'::/EFI/UniXNU/'+name])


def inflate(record,name):
    packed=fat('Payloads/kernel.macho.gpuaddon');assert packed[:8]==b'NGPUADD2'
    count,_,total=struct.unpack_from('<IIQ',packed,8);assert count==5==len(record['files']) and total==len(packed)
    at=24;decoded={}
    for _ in range(count):
        length,mode,size,compressed=struct.unpack_from('<IIQQ',packed,at);at+=24
        entry=packed[at:at+length];at+=(length+7)&~7
        stream=zlib.decompressobj();data=stream.decompress(packed[at:at+compressed])+stream.flush();at+=(compressed+7)&~7
        assert stream.eof and not stream.unused_data and len(data)==size
        full='/private/var/ngpu/'+entry[:-1].decode()
        expected=next(row for row in record['files'] if row['path']==full)
        assert mode==int(expected['mode'],8) and hashlib.sha256(data).hexdigest()==expected['sha256']
        decoded[full]=data
    assert at==len(packed)
    return decoded


build=load(ENTRY/'report.json')
for path,digest in build['inputs'].items():assert sha(path)==digest
for name,digest in build['objects'].items():assert sha(ENTRY/name)==digest
assert sha(Path(build['frontend']['source']))==build['frontend']['source_sha256']
assert sha(ENTRY/'NativeBridgeMetalFrontend.o')==build['frontend']['object_sha256']
diagnostics=load(TEST/'report.json')
assert diagnostics['passed'] and diagnostics['source_sha256']==sha(DEVICE/'package/Metal13/VenusMetalDiagnostics.h')
assert [event['stage'] for event in diagnostics['events']]==['entry','device']
assert diagnostics['events'][0]['detail']=='quote " slash \\ control \x01'
candidate=load(PHONE.parent/'candidate.json')
assert sha(PHONE/'boot-venus-unixnu.img')==candidate['image_sha256']
assert candidate['kernel_sha256']=='bd312e850bc3741d27c79cf748990f59fadd5f023c9e66ec424507adb2cd3423'
for name in ('kernel.macho','kernel.macho.adt','scratch-data.img'):
    original=subprocess.check_output(['mtype','-i',str(CONTROL/'payload.img'),'::/EFI/UniXNU/Payloads/'+name])
    assert fat('Payloads/'+name)==original,name
record=load(ADDON/'report.json');assert sha(ADDON/'kernel.macho.gpuaddon')==record['addon_sha256']
assert sha(ADDON/'kernel.macho.trustcache')==record['trust_sha256']
decoded=inflate(record,'NativeAdrenoMetal')
plugin=decoded['/private/var/ngpu/addons/NativeAdrenoMetal.bundle/NativeAdrenoMetal']
for word in (b'venus-metal: process=',b'no usable device/cache candidate',b'venus-metal-040/native.jsonl',
             b'Metal device created',b'CA_DISABLE_FRAMEBUFFER_COMPRESSION',b'CAEnableIOSurfaceCompression'):
    assert word in plugin,'Compiled plugin missing: '+str(word)
parsed=ast.parse((DEVICE/'scripts/link-venus-metal-plugin.py').read_text())
node=next(node for node in parsed.body if isinstance(node,ast.FunctionDef) and node.name=='verify')
namespace={'hashlib':hashlib,'struct':struct};exec(compile(ast.Module(body=[node],type_ignores=[]),'signature-verifier','exec'),namespace)
verified={}
for name,kind,key in (('NativeAdrenoMetal',8,'plugin'),('libvulkan_freedreno.dylib',6,'turnip')):
    path=ADDON/'NativeAdrenoMetal.bundle'/name
    assert path.read_bytes()==decoded['/private/var/ngpu/addons/NativeAdrenoMetal.bundle/'+name]
    verified[key]=namespace['verify'](path,kind);assert verified[key]['sha256']==record['binaries'][key]['sha256']
trust=fat('Payloads/kernel.macho.trustcache');assert sha(ADDON/'kernel.macho.trustcache')==hashlib.sha256(trust).hexdigest()
assert struct.unpack_from('<II',trust)==(1,8)
merged=entries(trust)
base=subprocess.check_output(['mtype','-i',str(ROOT/'artifacts/venus-scale-refresh-012/phone/payload.img'),'::/EFI/UniXNU/Payloads/kernel.macho.trustcache'])
original=entries(base)
assert all(merged[key]==attrs for key,attrs in original.items())
assert len(merged)==len(original)+2==2556
for details in verified.values():assert merged[bytes.fromhex(details['directory']['cdhash'])]==bytes([2,0,0,0])
recheck=(DEVICE/'scripts/recheck-data-forensics.py').read_text()
for path in ('/db/venus-metal-040/native.jsonl','/root/Library/Caches/com.apple.backboardd/venus-metal13/native.jsonl'):
    assert path in recheck
report={'passed':True,'image_sha256':candidate['image_sha256'],'kernel_sha256':candidate['kernel_sha256'],
    'kernel_adt_seed_identical_to038':True,'frontend_object_retained':True,
    'diagnostic_paths':['/private/var/db/venus-metal-040/native.jsonl',
        '/private/var/root/Library/Caches/com.apple.backboardd/venus-metal13/native.jsonl',
        '/private/var/mobile/Library/Caches/com.apple.backboardd/venus-metal13/native.jsonl'],
    'diagnostic_writer_tested':True,'diagnostic_events_test':diagnostics['events'],
    'original_trust_entries_preserved':len(original),'static_module_entries':len(merged),
    'plugin_signature':verified['plugin'],'turnip_signature':verified['turnip'],
    'gpu_device_open_verified':False,'gpu_pixels_verified':False,'phone_operations':False,
    'postlaunch_diagnostic_read_verified':False,'qemu_full_systemos_verified':False,
    'scope':'Actual040 FAT/plugin/trust and bounded diagnostic writer; not a Metal discovery or rendering result.'}
(OUT/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS:040 signed plugin+single-static trust+diagnostic writer; kernel/ADT/seed unchanged from038')
