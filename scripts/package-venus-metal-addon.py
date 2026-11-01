#!/usr/bin/env python3
"""Package verified own plugin/Turnip and extend the exact012 trust bundle."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import uuid
import zlib
import argparse
import sys
ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=ROOT/'artifacts/venus-metal13/addon-r2')
parser.add_argument('--plugin-dir',type=Path,default=ROOT/'artifacts/venus-metal13/plugin/NativeAdrenoMetal.bundle')
parser.add_argument('--single-static',action='store_true',help='Keep all system and owner entries in the first static module')
args=parser.parse_args();OUT=args.output;OUT.mkdir(parents=True,exist_ok=False)
PLUGIN=args.plugin_dir
# Reuse the independently checked verifier, without running the link script.
parsed=ast.parse((DEVICE/'scripts/link-venus-metal-plugin.py').read_text())
node=next(n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name=='verify')
namespace={'hashlib':hashlib,'struct':struct};exec(compile(ast.Module(body=[node],type_ignores=[]),'signature-verifier','exec'),namespace)
verify=namespace['verify']
turnip=ROOT/'artifacts/venus-metal13/turnip-signed/libvulkan_freedreno.dylib'
details={'plugin':verify(PLUGIN/'NativeAdrenoMetal',8),'turnip':verify(turnip,6)}
copy=OUT/'NativeAdrenoMetal.bundle';shutil.copytree(PLUGIN,copy);shutil.copy2(turnip,copy/'libvulkan_freedreno.dylib')
files=[]
for path in sorted(copy.iterdir()):
    files.append(('addons/NativeAdrenoMetal.bundle/'+path.name,0o755 if path.name!='Info.plist' else 0o644,path.read_bytes()))
files+=[('addons/NativeAdrenoMetal.publish',0o644,b'1\n'),('addons/NativeAdrenoMetal.clients',0o644,b'backboardd\n')]
body=bytearray();entries=[]
for name,mode,data in files:
    encoded=name.encode()+b'\0';packed=zlib.compress(data,9)
    body+=struct.pack('<IIQQ',len(encoded),mode,len(data),len(packed))+encoded+bytes(-len(encoded)%8)+packed+bytes(-len(packed)%8)
    entries.append({'path':'/private/var/ngpu/'+name,'mode':oct(mode),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
addon=b'NGPUADD2'+struct.pack('<IIQ',len(files),0,24+len(body))+body;(OUT/'kernel.macho.gpuaddon').write_bytes(addon)
at=24;decoded=[]
for _ in files:
    n,mode,size,packed=struct.unpack_from('<IIQQ',addon,at);at+=24;name=addon[at:at+n];at+=(n+7)&~7
    stream=zlib.decompressobj();data=stream.decompress(addon[at:at+packed])+stream.flush();at+=(packed+7)&~7
    assert stream.eof and not stream.unused_data and len(data)==size;decoded.append((name[:-1].decode(),mode,data))
assert at==len(addon) and decoded==files
original=subprocess.check_output(['mtype','-i',str(ROOT/'artifacts/venus-scale-refresh-012/phone/payload.img'),'::/EFI/UniXNU/Payloads/kernel.macho.trustcache'])
count=struct.unpack_from('<I',original)[0];offsets=list(struct.unpack_from('<'+str(count)+'I',original,4))+[len(original)]
modules=[original[offsets[i]:offsets[i+1]] for i in range(count)]
cdhashes=[details[k]['directory']['cdhash'] for k in ('plugin','turnip')]
new=struct.pack('<I16sI',2,uuid.uuid5(uuid.NAMESPACE_URL,'venus-metal13:'+':'.join(cdhashes)).bytes,2)+b''.join(bytes.fromhex(h)+bytes([2,0,0,0]) for h in sorted(cdhashes))
allmodules=[new,*modules];cursor=4+4*len(allmodules);starts=[]
for module in allmodules:starts.append(cursor);cursor+=len(module)
trust=struct.pack('<I',len(allmodules))+struct.pack('<'+str(len(starts))+'I',*starts)+b''.join(allmodules)
merge_report=None
if args.single_static:
    sys.path.insert(0,str(DEVICE/'package/Metal13'))
    from venus_trust_bundle import merge_static
    trust,merge_report=merge_static(original,[(bytes.fromhex(h),bytes([2,0,0,0])) for h in cdhashes])
(OUT/'kernel.macho.trustcache').write_bytes(trust)
if not args.single_static:assert all(trust[starts[i+1]:starts[i+2] if i+2<len(starts) else len(trust)]==module for i,module in enumerate(modules))
record={'files':entries,'binaries':details,'addon_bytes':len(addon),'addon_sha256':hashlib.sha256(addon).hexdigest(),'trust_sha256':hashlib.sha256(trust).hexdigest(),
        'original_trust_module_count':count,'original_modules_preserved':not args.single_static,
        'trust_layout':'single-static' if args.single_static else 'additive-modules',
        'trust_merge':merge_report,'publish_clients':['backboardd'],
        'scope':'Own signed Metal/Turnip addon wire and additive trust. No new job/seed reset/MG edit; device installer/Metal discovery remain untested.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
