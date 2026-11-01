#!/usr/bin/env python3
"""Link the real iOS17 frontend/runtime and verify its ad-hoc4K code signature."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import struct
import subprocess
import argparse

ROOT=Path('/mnt/g/UniXNU-Port');WORK=Path('/root/unixnu-build/venus-metal-work-r5');TOOLS=Path('/root/unixnu-build/venus-metal-tools')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=ROOT/'artifacts/venus-metal13/plugin')
parser.add_argument('--frontend-dir',type=Path,default=WORK/'frontend-build')
parser.add_argument('--version',default='13')
args=parser.parse_args()
OUT=args.output;BUNDLE=OUT/'NativeAdrenoMetal.bundle';BUNDLE.mkdir(parents=True,exist_ok=False)
SDK=TOOLS/'sdks/iPhoneOS16.5.sdk';EXE=BUNDLE/'NativeAdrenoMetal';FRONT=WORK/'frontend-build';BRIDGE=WORK/'cargo-target/aarch64-apple-ios/release/libvenus_native_metal_bridge.a'
FRONT=args.frontend_dir
classes=['_MTLDevice','_MTLResource','_MTLCommandQueue','_MTLCommandBuffer','_MTLCommandEncoder','_MTLComputePipelineState','_MTLRenderPipelineState','_MTLSamplerState','_MTLDepthStencilState']
undefined=[f'-Wl,-U,_OBJC_{kind}_$_{name}' for name in classes for kind in ('CLASS','METACLASS')]
command=['/usr/bin/clang++-18','-target','arm64-apple-ios17.0','-isysroot',str(SDK),'-mlinker-version=953',
    '-fuse-ld='+str(TOOLS/'llvm21/usr/lib/llvm-21/bin/ld64.lld'),'-bundle',str(FRONT/'NativeBridgeMetalFrontend.o'),str(FRONT/'VenusMetalPlugin.o'),str(BRIDGE),
    '-Wl,-dead_strip,-S,-x,-adhoc_codesign',*undefined,'-lobjc','-framework','Foundation','-framework','Metal','-framework','IOSurface','-o',str(EXE)]
env={**os.environ,'LD_LIBRARY_PATH':str(TOOLS/'llvm21/usr/lib/x86_64-linux-gnu')}
result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=300);(OUT/'link.log').write_text(result.stdout+result.stderr)
if result.returncode:print('FAILED; read',OUT/'link.log');raise SystemExit(result.returncode)
def verify(path,kind):
    blob=path.read_bytes();magic,cpu,subtype,filetype,ncmds,sz,_,_=struct.unpack_from('<8I',blob)
    assert (magic,cpu,subtype,filetype)==(0xfeedfacf,0x100000c,0,kind)
    at=32;signature=None;platform=None;dylibs=[]
    for _ in range(ncmds):
        cmd,size=struct.unpack_from('<II',blob,at);assert size>=8 and at+size<=32+sz
        if cmd==0x1d:signature=struct.unpack_from('<II',blob,at+8)
        if cmd==0x32:platform=struct.unpack_from('<III',blob,at+8)
        if cmd==0xc:
            offset=struct.unpack_from('<I',blob,at+8)[0];dylibs.append(blob[at+offset:at+size].split(b'\0')[0].decode())
        at+=size
    assert platform and platform[0]==2 and platform[1]==0x110000 and signature
    sigoff,siglen=signature;sig=blob[sigoff:sigoff+siglen];sigmagic,total,count=struct.unpack_from('>III',sig);assert sigmagic==0xfade0cc0 and total<=len(sig)
    directories=[]
    for i in range(count):
        slot,offset=struct.unpack_from('>II',sig,12+i*8)
        if slot not in (0,0x1000):continue
        cdmagic,length,_,flags,hashoff,idoff,special,nslots,limit=struct.unpack_from('>9I',sig,offset)
        cd=sig[offset:offset+length];hashsize,hashtype,_,pageshift=struct.unpack_from('4B',cd,36)
        assert cdmagic==0xfade0c02 and flags&2 and hashtype==2 and hashsize==32 and pageshift==12 and not special
        assert limit==sigoff and nslots==(limit+4095)//4096
        for page in range(nslots):assert cd[hashoff+page*32:hashoff+(page+1)*32]==hashlib.sha256(blob[page*4096:min(limit,(page+1)*4096)]).digest()
        directories.append({'cdhash':hashlib.sha256(cd).hexdigest()[:40],'pages':nslots,'identifier':cd[idoff:].split(b'\0')[0].decode()})
    assert len(directories)==1
    return {'sha256':hashlib.sha256(blob).hexdigest(),'bytes':len(blob),'directory':directories[0],'dylibs':dylibs}
(BUNDLE/'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'org.unixnu.venus.NativeAdrenoMetal','CFBundleExecutable':'NativeAdrenoMetal',
    'CFBundlePackageType':'BNDL','CFBundleVersion':args.version,'NSPrincipalClass':'NativeAdrenoMetalDevice','MinimumOSVersion':'17.0'}))
record={'plugin':verify(EXE,8),'command':command,'scope':'Real linked17 plugin with independently verified4K CodeDirectory; Turnip packaging/trust/device qualification follow.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
