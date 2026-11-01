#!/usr/bin/env python3
"""Qualify041 prelaunchd GPU/Metal status, retained035 touch and packaged trust."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib

ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus'
PHONE=ROOT/'artifacts/venus-metal-touch-041/phone'
KERNEL=ROOT/'artifacts/venus-metal-touch/kernel-link-37'
ADDON=ROOT/'artifacts/venus-metal-040/addon'
TOUCH=ROOT/'artifacts/venus-st-touch/production-041-diagnostics'
BASE=ROOT/'artifacts/venus-metal-touch/kernel-link-36'
sys.path.insert(0,str(DEVICE/'package/Metal13'))
from venus_trust_bundle import entries
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
fat=lambda name:subprocess.check_output(['mtype','-i',str(PHONE/'payload.img'),'::/EFI/UniXNU/'+name])
candidate=load(PHONE.parent/'candidate.json');assert sha(PHONE/'boot-venus-unixnu.img')==candidate['image_sha256']
link=load(KERNEL/'report.json');build=load(TOUCH/'report.json');base=load(BASE/'report.json')
assert link['touch_archive_sha256']==build['library_sha256']==base['touch_archive_sha256']
assert link['mainline_hid_object_sha256']==base['mainline_hid_object_sha256']
assert link['gpu_archive_sha256']==base['gpu_archive_sha256']
assert link['boot_policy_sha256']==sha(KERNEL/'BootWatchdogPolicy.c')
assert (TOUCH/'BootMetalReport.h').read_bytes()==(DEVICE/'package/boot-progress/BootMetalReport.h').read_bytes()
kernel=(KERNEL/'kernel.macho').read_bytes()
for marker in (b'/private/var/db/venus-metal-041/startup.json',b'venus-metal: startup report=%d',
               b'"gpu_power_stage"',b'"metal_stage"',b'"kext_status"'):
    assert marker in kernel,'Kernel missing marker: '+str(marker)
control=ROOT/'artifacts/venus-metal-touch-038/phone'
for name in ('kernel.macho.adt','scratch-data.img'):
    expected=subprocess.check_output(['mtype','-i',str(control/'payload.img'),'::/EFI/UniXNU/Payloads/'+name])
    assert fat('Payloads/'+name)==expected,name
# The payload ADT/seed are the same checked038 inputs; the GPU addon is040.
record=load(ADDON/'report.json');packed=fat('Payloads/kernel.macho.gpuaddon')
assert hashlib.sha256(packed).hexdigest()==record['addon_sha256'] and packed[:8]==b'NGPUADD2'
count,_,total=struct.unpack_from('<IIQ',packed,8);assert count==5 and total==len(packed)
at=24;decoded={}
for _ in range(count):
    length,mode,size,compressed=struct.unpack_from('<IIQQ',packed,at);at+=24
    name=packed[at:at+length];at+=(length+7)&~7
    stream=zlib.decompressobj();data=stream.decompress(packed[at:at+compressed])+stream.flush();at+=(compressed+7)&~7
    assert stream.eof and not stream.unused_data and len(data)==size
    decoded['/private/var/ngpu/'+name[:-1].decode()]=data
assert at==len(packed)
plugin=decoded['/private/var/ngpu/addons/NativeAdrenoMetal.bundle/NativeAdrenoMetal']
for marker in (b'venus-metal-040/native.jsonl',b'Metal device created',b'no usable device/cache candidate'):
    assert marker in plugin
trust=fat('Payloads/kernel.macho.trustcache');assert hashlib.sha256(trust).hexdigest()==record['trust_sha256']
merged=entries(trust);assert len(merged)==2556
original=entries(subprocess.check_output(['mtype','-i',str(ROOT/'artifacts/venus-scale-refresh-012/phone/payload.img'),'::/EFI/UniXNU/Payloads/kernel.macho.trustcache']))
assert all(merged[k]==v for k,v in original.items())
report={'passed':True,'image_sha256':candidate['image_sha256'],'kernel_sha256':candidate['kernel_sha256'],
    'touch_archive_sha256':link['touch_archive_sha256'],'mainline_hid_object_sha256':link['mainline_hid_object_sha256'],
    'gpu_archive_sha256':link['gpu_archive_sha256'],'metal_report':'/private/var/db/venus-metal-041/startup.json',
    'metal_report_fields':['gpu_power_stage','addon_stage','addon_status','metal_stage','metal_status','kext_status','gpu_done'],
    'postlaunch_plugin_diagnostic_paths':['/private/var/db/venus-metal-040/native.jsonl',
        '/private/var/root/Library/Caches/com.apple.backboardd/venus-metal13/native.jsonl',
        '/private/var/mobile/Library/Caches/com.apple.backboardd/venus-metal13/native.jsonl'],
    'original_trust_entries_preserved':len(original),'static_module_entries':len(merged),
    'scope':'Pre-launch GPU status and post-launch plugin diagnostics are packaged; neither is observed until a separately authorized boot.',
    'phone_operations':False,'prelaunch_report_read':False,'gpu_pixels_verified':False}
(ROOT/'artifacts/venus-metal-touch-041/qualification.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS:041 prelaunch GPU/Metal report +040 plugin diagnostics packaged;035 touch and trust entries retained')
