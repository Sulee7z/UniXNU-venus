#!/usr/bin/env python3
"""Package a one-shot MG query launch job via the existing post-Data addon path.

The historical addon API uses the filename org.blu-sharky.adrenoprobed.plist
as its union-view marker. This payload puts the MG query job at that filename,
with its own org.unixnu.venus.mg-query label; it contains no GPU plugin.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess
import sys
import zlib

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
PROBE=ROOT/'artifacts/venus-mg-query-probe'
CONTROL=ROOT/'artifacts/venus-userspace-6g-001'
BASE=Path('/root/unixnu-build/UniXNU-sheng-base')
OUT=ROOT/'artifacts/venus-mg-query-008'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');options=parser.parse_args()
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(path):return json.loads(path.read_text())
def need(ok,why):
    if not ok:raise SystemExit(why)
def run(argv):return subprocess.check_output([str(x) for x in argv],timeout=240)
def fat(image,name):return run(['mtype','-i',image,'::/EFI/UniXNU/'+name])

build=load(PROBE/'build.json');host=load(PROBE/'host-tests/report.json');control=load(CONTROL/'candidate.json')
need(build['signature_pages_verified'] and host['passed'] and
     sha(DEVICE/'package/MGQueryProbe.c')==build['source_sha256']==host['production_source_sha256'], 'Probe source/build/protocol mismatch')
need(sha(PROBE/'venus-mg-query')==build['executable_sha256'] and
     sha(PROBE/'probe-and-original.trustcache')==build['trustcache_sha256'],'Probe binary/trust changed')
need(sha(CONTROL/'phone/boot-venus-unixnu.img')==control['image_sha256'] and
     sha(CONTROL/'phone/payload.img')==control['payload_sha256'],'Original6GiB control changed')
job={'Label':'org.unixnu.venus.mg-query','ProgramArguments':['/private/var/ngpu/bin/venus-mg-query'],
     'RunAtLoad':True,'LaunchOnlyOnce':True,'KeepAlive':False,'UserName':'mobile','GroupName':'mobile',
     'StandardOutPath':'/private/var/tmp/venus-mg-query-008.json',
     'StandardErrorPath':'/private/var/tmp/venus-mg-query-008.stderr'}
files=[('bin/venus-mg-query',0o755,(PROBE/'venus-mg-query').read_bytes()),
       ('daemons/org.blu-sharky.adrenoprobed.plist',0o644,plistlib.dumps(job,fmt=plistlib.FMT_XML))]
body=bytearray();entries=[]
for name,mode,data in files:
    encoded=name.encode()+b'\0';compressed=zlib.compress(data,9)
    need(len(encoded)<=160 and not name.startswith('/') and '..' not in name.split('/'),'Unsafe addon path')
    body+=struct.pack('<IIQQ',len(encoded),mode,len(data),len(compressed))
    body+=encoded+bytes(-len(encoded)%8)+compressed+bytes(-len(compressed)%8)
    entries.append({'path':'/private/var/ngpu/'+name,'mode':oct(mode),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
addon=b'NGPUADD2'+struct.pack('<IIQ',len(files),0,24+len(body))+body
# Independently round-trip the exact wire bytes the existing installer consumes.
at=24;decoded=[]
for _ in files:
    namebytes,mode,size,packed=struct.unpack_from('<IIQQ',addon,at);at+=24
    name=addon[at:at+namebytes];at+=(namebytes+7)&~7
    stream=zlib.decompressobj();data=stream.decompress(addon[at:at+packed])+stream.flush()
    need(stream.eof and not stream.unused_data and len(data)==size,'Addon inflate mismatch')
    at+=(packed+7)&~7;decoded.append((name[:-1].decode(),mode,data))
need(at==len(addon) and decoded==files,'Addon roundtrip mismatch')
spec=importlib.util.spec_from_file_location('codec',DEVICE/'scripts/inject-a660-firmware-adt.py')
codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
oldadt=(CONTROL/'kernel.macho.adt').read_bytes();oldtree=codec.parse(oldadt);chosenprops=dict(codec.find(oldtree,'chosen').props)
sys.path.insert(0,str(BASE/'scripts'))
from unixnu.cli import parser as cli_parser
from unixnu.config import Context
from unixnu.devicetree import generate
ctx=Context(cli_parser().parse_args(['status','-D',str(DEVICE),'--out','/root/unixnu-build/venus-legacy-full']))
board=copy.deepcopy(ctx.board);board['payload']['adt']['owned_memory_size']='0x180000000'
newtree=codec.parse(generate(ROOT/'artifacts/venus-stage-foundation/hardware/hardware.dtb',board,
    unique_chip_id=f"{int.from_bytes(chosenprops['unique-chip-id'],'little'):x}",data=True,trust=True,addon=True))
chosen=codec.find(newtree,'chosen');chosen.props=[(k,chosenprops[k] if k=='random-seed' else v) for k,v in chosen.props]
memorymap=codec.find(chosen,'memory-map')
need(dict(memorymap.props)['GpuAddon']==bytes(16),'GpuAddon placeholder mismatch')
adt=codec.dump(newtree)
memorymap.props=[(k,v) for k,v in memorymap.props if k!='GpuAddon']
chosen.props=[(k,v) for k,v in chosen.props if k not in ('display-scale','display-rotation')]
need(codec.dump(newtree)==oldadt,'ADT changed beyond scale2/rotation0 and addon placeholder')
args=control['args'].split();args=[a for a in args if not a.startswith('sheng-build-tag=')]
need(not any(a.startswith(('sheng-gpu-addon=','venus-gestalt-refresh=','sheng-data-reset=','sheng-autoreset=')) for a in args),'Unexpected reset/cache/addon gate')
args+=['sheng-gpu-addon=1','sheng-build-tag=mg-query-008'];kernelargs=' '.join(args)
phone=OUT/'phone'
if not options.check:
    need(not OUT.exists(),'Preserve completed candidate')
    OUT.mkdir();phone.mkdir();(OUT/'kernel').mkdir();(OUT/'linked-inputs').mkdir()
    for name in ('kernel.macho','kernel.json'):shutil.copy2(CONTROL/'kernel'/name,OUT/'kernel'/name)
    for name in ('payload.img','SILICIUM_UEFI.fd','UniXNU.efi','UniXNUDxe.efi','DarwinBoot.efi'):
        shutil.copy2(CONTROL/'phone'/name,phone/name)
    (OUT/'kernel.macho.adt').write_bytes(adt);(phone/'kernel.macho.gpuaddon').write_bytes(addon)
    config=(CONTROL/'phone/unixnu.toml').read_text();need(config.count(control['args'])==1,'Ambiguous control args')
    config=config.replace(control['args'],kernelargs)
    if 'action = "tools"' not in config:config+='\n[[entry]]\nid = "tools"\ntitle = "Tools"\ntype = "action"\naction = "tools"\n'
    (phone/'unixnu.toml').write_text(config)
    for source,dest in ((OUT/'kernel.macho.adt','Payloads/kernel.macho.adt'),
                        (phone/'kernel.macho.gpuaddon','Payloads/kernel.macho.gpuaddon'),
                        (PROBE/'probe-and-original.trustcache','Payloads/kernel.macho.trustcache'),
                        (phone/'unixnu.toml','unixnu.toml')):
        run(['mcopy','-o','-i',phone/'payload.img',source,'::/EFI/UniXNU/'+dest])
    run(['python3',ROOT/'tools/package-venus-uefi.py','--tree',ROOT/'ports/uefi-venus','--workspace',ROOT,
         '--artifacts',phone,'--payload',phone/'payload.img'])
    for source,name in ((PROBE/'build.json','probe-build.json'),(PROBE/'host-tests/report.json','probe-tests.json'),
                        (DEVICE/'package/MGQueryProbe.c','MGQueryProbe.c'),(DEVICE/'board.toml','board.toml')):
        shutil.copy2(source,OUT/'linked-inputs'/name)
need(fat(phone/'payload.img','Payloads/kernel.macho')==(CONTROL/'kernel/kernel.macho').read_bytes(),'Kernel changed')
need(fat(phone/'payload.img','Payloads/scratch-data.img')==fat(CONTROL/'phone/payload.img','Payloads/scratch-data.img'),'Data seed changed')
need(fat(phone/'payload.img','Payloads/kernel.macho.adt')==adt,'Sidecar changed')
need(fat(phone/'payload.img','Payloads/kernel.macho.gpuaddon')==addon,'Addon FAT mismatch')
need(fat(phone/'payload.img','Payloads/kernel.macho.trustcache')==(PROBE/'probe-and-original.trustcache').read_bytes(),'Trust FAT mismatch')
need(fat(phone/'payload.img','unixnu.toml')==(phone/'unixnu.toml').read_bytes(),'Config FAT mismatch')
v=load(phone/'verification.json')
need(v['roundtrip_verified'] and not v['uefi_memory_conflicts'] and v['efi']==control['efi'] and
     v['fd_sha256']==control['fd_sha256'] and sha(phone/'boot-venus-unixnu.img')==v['sha256'],'Boot/firmware mismatch')
record={'device':'venus','date':'2026-10-29','image':str(phone/'boot-venus-unixnu.img'),'image_sha256':v['sha256'],
        'image_bytes':v['bytes'],'kernel_sha256':control['kernel_sha256'],'adt_sha256':sha(OUT/'kernel.macho.adt'),
        'payload_sha256':sha(phone/'payload.img'),'probe_executable_sha256':build['executable_sha256'],
        'probe_cdhash':build['cdhash'],'args':kernelargs,'addon_sha256':hashlib.sha256(addon).hexdigest(),
        'installed_files':entries,'job':job,'original_seed_unchanged':True,'original_kernel_unchanged':True,
        'original_trust_modules_preserved':build['original_trust_modules_preserved'],
        'fd_sha256':control['fd_sha256'],'efi':v['efi'],'same_kernel_prior_systemos_qemu':control['qemu_systemos_sha256'],
        'qemu_helper_execution_verified':False,'phone_tested':False,
        'integration':'Existing post-Data NGPUADD2 installer and readonly union LaunchDaemons view. Historical adrenoprobed filename marker is used for the MG job, with its own label. No GPU addon binaries, extension or wallpaper files supplied.',
        'expected_extensions_and_wallpaper_status':'Missing sources expected; job-directory mount is independent and must actually reach stage5/status0',
        'measurement':'Read /private/var/tmp/venus-mg-query-008.json after this boot. A missing/incomplete output is not a zero answer or success.',
        'scope':'Local payload prepared for a single MG API measurement. Actual addon install/union visibility/helper launch/output persistence require an exact authorized phone run.'}
if options.check:need(load(OUT/'candidate.json')==record,'Saved candidate differs')
else:
    (OUT/'candidate.json').write_text(json.dumps(record,indent=2)+'\n')
    (DEVICE/'evidence/mg-query-candidate.json').write_text(json.dumps(record,indent=2)+'\n')
os.sync();print(json.dumps({k:record[k] for k in ('image','image_sha256','probe_executable_sha256','scope')},indent=2))
