#!/usr/bin/env python3
"""Build actual ARM64 task shim and verify its own CodeDirectory/trust entry."""
import hashlib
import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess
import uuid

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--revision',type=int,default=2);args=parser.parse_args()
if args.revision!=2:parser.error('Use revision2')
OUT=ROOT/'artifacts/venus-mg-query-009/task-wrapper-r2';OUT.mkdir(exist_ok=False)
CLANG='/root/unixnu-toolchain/llvm/bin/clang'
LD=shutil.which('ld64.lld') or str(next(Path('/usr/lib').glob('llvm-*/bin/ld64.lld')))
symbols=['_open','_close','_fcntl','_dprintf','_getpid','_fork','_execve','_getuid','_sleep',
         '_setgroups','_setgid','_setuid','_dup2','_fsync','_waitpid','_kill','___error','__exit','_environ','dyld_stub_binder']
stub=OUT/'libSystem.tbd';stub.write_text('--- !tapi-tbd\ntbd-version: 4\ntargets: [ arm64-ios ]\ninstall-name: /usr/lib/libSystem.B.dylib\n'
    'exports:\n  - targets: [ arm64-ios ]\n    symbols: [ '+', '.join(symbols)+' ]\n...\n')
source=DEVICE/'package/MGTaskLaunch.c';obj=OUT/'MGTaskLaunch.o';exe=OUT/'prng_seedctl'
commands=[[CLANG,'-target','arm64-apple-ios17.0','-std=c11','-ffreestanding','-fno-stack-protector','-O2',
           '-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-c',str(source),'-o',str(obj)],
          [LD,'-arch','arm64','-platform_version','ios','17.0','17.0','-e','_main','-adhoc_codesign',str(stub),str(obj),'-o',str(exe)]]
for i,command in enumerate(commands):
    result=subprocess.run(command,capture_output=True,text=True,timeout=120)
    (OUT/f'build-{i}.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(result.stdout+result.stderr)
blob=exe.read_bytes();magic,cpu,subtype,kind,count,cmdsize=struct.unpack_from('<6I',blob)
assert (magic,cpu,subtype,kind)==(0xfeedfacf,0x100000c,0,2)
at=32;signature=None;dylibs=[]
for _ in range(count):
    cmd,size=struct.unpack_from('<II',blob,at);assert size>=8 and at+size<=32+cmdsize
    if cmd==0x1d:signature=struct.unpack_from('<II',blob,at+8)
    if cmd==0xc:
        begin=struct.unpack_from('<I',blob,at+8)[0];dylibs.append(blob[at+begin:at+size].split(b'\0')[0].decode())
    at+=size
assert signature and dylibs==['/usr/lib/libSystem.B.dylib']
sigoff,siglen=signature;sig=blob[sigoff:sigoff+siglen]
magic,length,count=struct.unpack_from('>III',sig);assert magic==0xfade0cc0 and count==1 and length<=siglen
slot,offset=struct.unpack_from('>II',sig,12);assert slot==0
magic,length,version,flags,hashoff,idoff,special,pages,limit=struct.unpack_from('>9I',sig,offset)
cd=sig[offset:offset+length];hashsize,hashtype,_,shift=struct.unpack_from('4B',cd,36)
assert magic==0xfade0c02 and flags&2 and not special and (hashsize,hashtype,shift)==(32,2,12) and limit==sigoff
assert pages==(limit+4095)//4096
for page in range(pages):assert cd[hashoff+page*32:hashoff+(page+1)*32]==hashlib.sha256(blob[page*4096:min(limit,(page+1)*4096)]).digest()
cdhash=hashlib.sha256(cd).hexdigest()[:40]
old=(ROOT/'artifacts/venus-mg-query-probe/probe-and-original.trustcache').read_bytes()
oldcount=struct.unpack_from('<I',old)[0];assert oldcount==3
offsets=struct.unpack_from('<3I',old,4);modules=[old[offsets[i]:(offsets[i+1] if i+1<3 else len(old))] for i in range(3)]
modules.insert(0,struct.pack('<I16sI',2,uuid.uuid5(uuid.NAMESPACE_URL,'venus-mg-task:'+cdhash).bytes,1)+bytes.fromhex(cdhash)+bytes([2,0,0,0]))
cursor=20;new=[]
for module in modules:new.append(cursor);cursor+=len(module)
trust=struct.pack('<5I',4,*new)+b''.join(modules);(OUT/'task-probe-original.trustcache').write_bytes(trust)
assert all(trust[new[i+1]:(new[i+2] if i+2<4 else len(trust))]==old[offsets[i]:(offsets[i+1] if i+1<3 else len(old))] for i in range(3))
record={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'bytes':len(blob),'pages':pages,
        'executable_sha256':hashlib.sha256(blob).hexdigest(),'cdhash':cdhash,'signature_pages_verified':True,
        'trustcache_sha256':hashlib.sha256(trust).hexdigest(),'old_query_and_original_modules_preserved':True,
        'commands':commands,'device_execution_verified':False}
(OUT/'build.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
