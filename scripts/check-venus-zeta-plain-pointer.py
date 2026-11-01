#!/usr/bin/env python3
"""Execute zeta's ordinary-pointer results; keep original-opcode trap tests separate."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path('/mnt/g/UniXNU-Port');REFERENCE=ROOT/'sources/UniXNU-zeta-none24smu/scripts'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
import sys
sys.path.insert(0,str(REFERENCE))
spec=importlib.util.spec_from_file_location('zeta_plain_probe',REFERENCE/'check-zeta-pauth.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
compiler=shutil.which('clang');linker=shutil.which('ld.lld');qemu=shutil.which('qemu-system-aarch64')
assert compiler and linker and qemu
(out/'blank.bin').write_bytes(bytes(4096))
(out/'link.ld').write_text('ENTRY(_start)\nSECTIONS { . = 0x40200000; .text : { *(.text.entry) *(.text*) } .bss : { *(.bss*) } }\n')
cases=[]
for name,original in probe.CASES.items():
    lower=probe.lower_word(original);assert lower and lower[0]==name
    directory=out/name;directory.mkdir()
    source=directory/'entry.S';source.write_text(probe.assembly(name,lower[1],False))
    obj=directory/'entry.o';elf=directory/'guest.elf'
    subprocess.run([compiler,'--target=aarch64-none-elf','-c',str(source),'-o',str(obj)],check=True,capture_output=True)
    subprocess.run([linker,'-T',str(out/'link.ld'),str(obj),'-o',str(elf)],check=True,capture_output=True)
    command=[qemu,'-machine','virt,virtualization=off,secure=off','-cpu','cortex-a55','-m','128M',
             '-display','none','-monitor','none','-serial','none','-semihosting-config','enable=on,target=native',
             '-kernel',str(out/'blank.bin'),'-device',f'loader,file={elf},cpu-num=0']
    result=subprocess.run(command,capture_output=True,text=True,timeout=10)
    text=result.stdout+result.stderr;(directory/'qemu.log').write_text(text)
    assert result.returncode==0 and 'PASS_PLAIN_POINTER' in text,(name,text)
    cases.append({'name':name,'original_word':hex(original),'ordinary_word':hex(lower[1]),
                  'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest(),'passed':True})
report={'passed':True,'executed_ordinary_cases':len(cases),'cases':cases,
        'source_revision':'eb489285a1d9153872f00c93ebb519a269b249b5','qemu_model':'cortex-a55',
        'scope':'Synthetic EL1 ordinary-pointer behavior, including NZCV/register/SP/link preservation. Not PAC emulation, Apple userland execution or Venus hardware proof.',
        'original_opcode_trap_suite_passed':False,
        'original_suite_issue':'Separate pinned reference run stopped at retab/original with FAIL on this QEMU; no negative-suite pass is claimed.',
        'phone_operations':False,'iphone_userland_booted':False}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS:',len(cases),'ordinary-pointer EL1 cases; original-opcode trap suite remains unqualified')
