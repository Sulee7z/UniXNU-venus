#!/usr/bin/env python3
"""Build/sign the iOS17 ARM64 helper and independently verify every CodeDirectory page."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import shutil
import uuid

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
OUT=ROOT/'artifacts/venus-mg-query-probe';OUT.mkdir(exist_ok=True)
CLANG=Path('/root/unixnu-toolchain/llvm/bin/clang')
LD=next((p for p in [Path(shutil.which('ld64.lld') or '/nonexistent'),
                     *Path('/usr/lib').glob('llvm-*/bin/ld64.lld')] if p.is_file()),None)
if LD is None:raise SystemExit('Mach-O lld with TAPI support is required')
SOURCE=DEVICE/'package/MGQueryProbe.c'
def run(argv):
    result=subprocess.run([str(x) for x in argv],capture_output=True,text=True,timeout=120)
    if result.returncode:raise SystemExit(result.stdout+result.stderr)
    return result.stdout+result.stderr
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
# Link-time import list only: functions execute in the device's original libSystem.
# No macOS SDK libraries, synthetic CF/MG implementation, or no-op codesign shim.
symbols=['_dlopen','_dlsym','_dlclose','_printf','_getpid','_getuid','_sysctlbyname','_memcpy','_memset','dyld_stub_binder']
stub=OUT/'libSystem.tbd'
stub.write_text('--- !tapi-tbd\ntbd-version: 4\ntargets: [ arm64-ios ]\ninstall-name: /usr/lib/libSystem.B.dylib\n'
                'exports:\n  - targets: [ arm64-ios ]\n    symbols: [ '+', '.join(symbols)+' ]\n...\n')
obj=OUT/'MGQueryProbe.o';exe=OUT/'venus-mg-query'
compile_cmd=[CLANG,'-target','arm64-apple-ios17.0','-std=c11','-ffreestanding','-fno-stack-protector',
             '-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-c',SOURCE,'-o',obj]
link_cmd=[LD,'-arch','arm64','-platform_version','ios','17.0','17.0','-e','_main','-adhoc_codesign',
          stub,obj,'-o',exe]
(OUT/'compile.log').write_text(run(compile_cmd))
(OUT/'link.log').write_text(run(link_cmd))
blob=exe.read_bytes();magic,cpu,subtype,kind,ncmds,sz,flags,_=struct.unpack_from('<8I',blob)
assert (magic,cpu,subtype,kind)==(0xfeedfacf,0x100000c,0,2)
at=32;signature=None;platform=None;main=False;dylibs=[]
for _ in range(ncmds):
    cmd,size=struct.unpack_from('<II',blob,at);assert size>=8 and at+size<=32+sz
    if cmd==0x1d:signature=struct.unpack_from('<II',blob,at+8)
    if cmd==0x32:platform=struct.unpack_from('<III',blob,at+8)
    if cmd==0x80000028:main=True
    if cmd==0xc:
        offset=struct.unpack_from('<I',blob,at+8)[0]
        dylibs.append(blob[at+offset:at+size].split(b'\0')[0].decode())
    at+=size
assert main and platform and platform[0]==2 and platform[1]==0x110000
assert dylibs==['/usr/lib/libSystem.B.dylib'] and signature
sigoff,siglen=signature;sig=blob[sigoff:sigoff+siglen]
sigmagic,total,count=struct.unpack_from('>III',sig);assert sigmagic==0xfade0cc0 and total<=len(sig)
directories=[]
for i in range(count):
    slot,offset=struct.unpack_from('>II',sig,12+i*8)
    if slot not in (0,0x1000):continue
    cdmagic,length,version,cdflags,hashoff,idoff,special,nslots,limit=struct.unpack_from('>9I',sig,offset)
    cd=sig[offset:offset+length];hashsize,hashtype,_,pageshift=struct.unpack_from('4B',cd,36)
    assert cdmagic==0xfade0c02 and cdflags&2 and hashtype==2 and hashsize==32 and pageshift==12
    assert limit==sigoff and nslots==(limit+4095)//4096 and not special
    for page in range(nslots):
        actual=hashlib.sha256(blob[page*4096:min(limit,(page+1)*4096)]).digest()
        assert cd[hashoff+page*32:hashoff+(page+1)*32]==actual,'CodeDirectory page mismatch'
    directories.append({'slot':slot,'sha256':hashlib.sha256(cd).hexdigest(),'pages':nslots,
                        'identifier':cd[idoff:].split(b'\0')[0].decode()})
assert len(directories)==1
cdhash=directories[0]['sha256'][:40]
original=(ROOT/'artifacts/venus-deployment/original-static-system.bundle').read_bytes()
assert struct.unpack_from('<I',original)[0]==2
oldoffs=struct.unpack_from('<2I',original,4)
module=struct.pack('<I16sI',2,uuid.uuid5(uuid.NAMESPACE_URL,'venus-mg-query:'+cdhash).bytes,1)+bytes.fromhex(cdhash)+bytes([2,0,0,0])
modules=[module,original[oldoffs[0]:oldoffs[1]],original[oldoffs[1]:]]
cursor=16;offsets=[]
for m in modules:offsets.append(cursor);cursor+=len(m)
bundle=struct.pack('<4I',3,*offsets)+b''.join(modules)
(OUT/'probe-and-original.trustcache').write_bytes(bundle)
assert bundle[offsets[1]:offsets[2]]==original[oldoffs[0]:oldoffs[1]] and bundle[offsets[2]:]==original[oldoffs[1]:]
result={'device':'venus','target':'arm64-apple-ios17.0','source_sha256':sha(SOURCE),'executable_sha256':sha(exe),
        'bytes':len(blob),'compile_command':[str(x) for x in compile_cmd],'link_command':[str(x) for x in link_cmd],
        'dylibs':dylibs,'code_directories':directories,'cdhash':cdhash,'signature_pages_verified':True,
        'trustcache_sha256':sha(OUT/'probe-and-original.trustcache'),'original_trust_modules_preserved':True,
        'codesign_shim_used':False,'runtime_measured':False,'phone_image_prepared':False,
        'scope':'Built actual iOS query helper with verified ad-hoc4KiB CodeDirectory. Execution/install/stdout retrieval still require integration and a measured runtime.'}
(OUT/'build.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
