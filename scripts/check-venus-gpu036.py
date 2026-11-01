#!/usr/bin/env python3
"""Verify036's real ABI adapter, boot call, retained input and paired signed addon."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import zlib

ROOT=Path('/mnt/g/UniXNU-Port')
DEVICE=ROOT/'ports/UniXNU-venus'
OUT=ROOT/'artifacts/venus-gpu-036'
KERNEL=ROOT/'artifacts/venus-metal-touch/kernel-link-34'
PHONE=ROOT/'artifacts/venus-metal-touch-036/phone'
ADDON=ROOT/'artifacts/venus-metal13/addon-r2'


def load(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


spec=importlib.util.spec_from_file_location('gpu_audit',DEVICE/'scripts/audit-venus-metal-discovery.py')
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
old=audit.audit(ROOT/'artifacts/venus-metal-touch/kernel-link-33')
new=audit.audit(KERNEL)
assert old['private_gpu_service_present'] and not old['metal_accelerator_allocate_present']
assert new['private_gpu_service_present'] and new['metal_accelerator_allocate_present']
raw=(KERNEL/'kernel.macho').read_bytes()
image=audit.macho(raw)
names={n:a for a,group in audit.exports(raw,image).items() for n in group}
start=names['_sheng_boot_watchdog_policy']
end=min(a for a in names.values() if a>start)
offset=audit.backed_offset(image['segments'],start,end-start,len(raw))
targets=[]
for i in range(0,end-start-3,4):
    word=struct.unpack_from('<I',raw,offset+i)[0]
    if word&0xfc000000==0x94000000:
        immediate=word&0x3ffffff
        if immediate&0x2000000:immediate-=0x4000000
        targets.append(start+i+4*immediate)
assert names['_venus_metal_wait_before_launchd'] in targets,'Missing actual prelaunch wait call'

link=load(KERNEL/'report.json')
baseline=load(ROOT/'artifacts/venus-metal-touch/kernel-link-33/report.json')
assert sha(KERNEL/'libVenusStTouch.a')==baseline['touch_archive_sha256']==link['touch_archive_sha256']
assert link['mainline_hid_object_sha256']==baseline['mainline_hid_object_sha256']
assert link['mod_init_bytes']==baseline['mod_init_bytes']
test=load(OUT/'publication-tests-r2/report.json')
assert test['passed']
for path,digest in test['sources'].items():assert sha(Path(path))==digest

manifest=load(ADDON/'report.json')
addon=subprocess.check_output(['mtype','-i',str(PHONE/'payload.img'),'::/EFI/UniXNU/Payloads/kernel.macho.gpuaddon'])
assert hashlib.sha256(addon).hexdigest()==manifest['addon_sha256']
assert addon[:8]==b'NGPUADD2'
count,_,total=struct.unpack_from('<IIQ',addon,8)
assert count==len(manifest['files'])==5 and total==len(addon)
at=24
decoded={}
for _ in range(count):
    length,mode,size,packed=struct.unpack_from('<IIQQ',addon,at);at+=24
    name=addon[at:at+length];at+=(length+7)&~7
    assert name.endswith(b'\0')
    stream=zlib.decompressobj()
    data=stream.decompress(addon[at:at+packed])+stream.flush();at+=(packed+7)&~7
    assert stream.eof and not stream.unused_data and len(data)==size
    path='/private/var/ngpu/'+name[:-1].decode()
    entry=next(row for row in manifest['files'] if row['path']==path)
    assert mode==int(entry['mode'],8) and hashlib.sha256(data).hexdigest()==entry['sha256']
    decoded[path]=data
assert at==len(addon) and len(decoded)==5
assert decoded['/private/var/ngpu/addons/NativeAdrenoMetal.clients']==b'backboardd\n'

# Reuse the existing independent Mach-O/platform/4K CodeDirectory verifier.
parsed=ast.parse((DEVICE/'scripts/link-venus-metal-plugin.py').read_text())
node=next(n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name=='verify')
namespace={'hashlib':hashlib,'struct':struct}
exec(compile(ast.Module(body=[node],type_ignores=[]),'signature-verifier','exec'),namespace)
verified={}
for name,kind,key in (('NativeAdrenoMetal',8,'plugin'),('libvulkan_freedreno.dylib',6,'turnip')):
    path=ADDON/'NativeAdrenoMetal.bundle'/name
    assert path.read_bytes()==decoded['/private/var/ngpu/addons/NativeAdrenoMetal.bundle/'+name]
    checked=namespace['verify'](path,kind)
    assert checked['sha256']==manifest['binaries'][key]['sha256']
    verified[key]=checked

candidate=load(PHONE.parent/'candidate.json')
assert sha(PHONE/'boot-venus-unixnu.img')==candidate['image_sha256']
assert candidate['kernel_sha256']==new['kernel_sha256']
flags=candidate['args'].split()
for value in ('sheng-gpu-power=9','sheng-gpu-metal=1','zeta-gpu-metal=1','sheng-gpu-addon=1',
              'venus-st-touch=3','sheng-touch-hid=1','venus-st-custom-hid=0','sheng-fb-gpu=0'):
    assert flags.count(value)==1
assert not candidate['qemu_verified'] and not candidate['phone_tested']
report={'passed':True,'old_kernel':old,'new_kernel':new,
    'prelaunch_wait_actual_branch':True,'touch_archive_sha256':link['touch_archive_sha256'],
    'mainline_hid_object_sha256':link['mainline_hid_object_sha256'],
    'automatic_initializer_bytes':link['mod_init_bytes'],'publication_test_report_sha256':sha(OUT/'publication-tests-r2/report.json'),
    'addon_binaries':verified,'addon_fat_files_verified':len(decoded),
    'image_sha256':candidate['image_sha256'],'qemu_verified':False,
    'phone_operations':False,'hardware_rendering_verified':False}
(OUT/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: actual accelerator vtable/imports, compiled prelaunch call, unchanged035 touch, signed5-file addon and image hashes')
