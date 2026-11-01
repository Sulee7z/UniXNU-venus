#!/usr/bin/env python3
"""Inspect exact008 kernel and original cache-loader activation gates, host-only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess

ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'artifacts/venus-mg-query-008/activation-inspection'
OUT.mkdir(exist_ok=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('activation_macho',ROOT/'sources/UniXNU-guide/kits/XnuPrelink/native_prelink.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
kernel=ROOT/'artifacts/venus-mg-query-008/kernel/kernel.macho'
blob=kernel.read_bytes()
if sha(kernel)!='4b1ae1c0bc6ea2b7dbb440099ef5c0a0c413d26aab8bfe304f1fbc8b1a2760be':raise ValueError('Wrong kernel')
image=m.macho(blob);symbols=m.exports(blob,image)
addresses={name:at for at,names in symbols.items() for name in names}
start=addresses['_load_init_program'];end=min(at for at in symbols if at>start)
offset=m.backed_offset(image['segments'],start,end-start,len(blob));code=blob[offset:offset+end-start]
decoded=subprocess.run(['/usr/bin/llvm-mc','--triple=aarch64','--disassemble'],
    input=' '.join(f'0x{x:02x}' for x in code),capture_output=True,text=True,check=True)
lines=[s.strip() for s in decoded.stdout.splitlines() if s.strip() and s.strip()!='.text']
if len(lines)!=len(code)//4:raise ValueError('Kernel disassembly incomplete')
(OUT/'load-init-program.txt').write_text('\n'.join(f'{start+i*4:#x} {line}' for i,line in enumerate(lines))+'\n')
loader=ROOT/'artifacts/venus-mg-query-008/launch-cache-inspection-v2/usr_libexec_launchd_cache_loader'
if sha(loader)!='40fd158dcd8254423ea60d9404f288e0de073f6c1e01b6d6bed334b900d0b940':raise ValueError('Wrong cache loader')
disasm=subprocess.run(['/usr/bin/llvm-objdump','--macho','--disassemble','--no-show-raw-insn',str(loader)],
                     capture_output=True,text=True,check=True)
(OUT/'cache-loader.txt').write_text(disasm.stdout)
record={'kernel_sha256':sha(kernel),'load_init_program':hex(start),'load_init_program_bytes':len(code),
        'offline_air_string_present':b'offline-air-init\0' in blob,
        'air_native_path_present':b'/private/var/tmp/air-native\0' in blob,
        'cache_loader_sha256':sha(loader),'cache_loader_disassembly':str(OUT/'cache-loader.txt'),
        'cache_loader_strings':[s.decode() for s in re.findall(rb'[\x20-\x7e]{5,}',loader.read_bytes())
                                if re.search(rb'boot_arg|unsecure|variant|cache|CodeDirectory|trust',s)]}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
