#!/usr/bin/env python3
"""Recompile the real reset vector and replace only start.o in an isolated core archive."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def archive_members(path):
    blob=path.read_bytes()
    assert blob[:8]==b'!<arch>\n'
    at=8; names=b''; result=[]
    while at<len(blob):
        header=blob[at:at+60];assert len(header)==60 and header[58:]==b'`\n'
        length=int(header[48:58]);at+=60
        data=blob[at:at+length];assert len(data)==length
        at+=length+(length&1)
        name=header[:16].decode().strip()
        if name=='//':names=data;continue
        if name.startswith('#1/'):
            count=int(name[3:]);name=data[:count].rstrip(b'\0').decode();data=data[count:]
        elif name.startswith('/') and name[1:].isdigit():
            offset=int(name[1:]);name=names[offset:names.index(b'/\n',offset)].decode()
        else:name=name.rstrip('/')
        if name in ('','___.SYMDEF','__.SYMDEF','__.SYMDEF SORTED','__.SYMDEF_64') or name.startswith('__.SYMDEF'):continue
        result.append((name,hashlib.sha256(data).hexdigest()))
    assert at==len(blob)
    return result

ROOT=Path('/mnt/g/UniXNU-Port')
TREE=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root/tree')
OBJ=TREE/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
CORE=OBJ/'mach.development.bcm2837.link/mach.development.bcm2837.a'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
out=args.output
out.mkdir(parents=True,exist_ok=False)
source=TREE/'.cache/xnu-work/osfmk/arm64/start.s'
work=out/'source'
(work/'osfmk/arm64').mkdir(parents=True)
(work/'osfmk/arm64/start.s').write_bytes(source.read_bytes())
patch=ROOT/'ports/UniXNU-sm8350-common/patches/xnu/sm8350-psci-reset-affinity.patch'
result=subprocess.run(['patch','-p1','--batch','--fuzz=0','-d',str(work),'-i',str(patch)],capture_output=True,text=True)
(out/'patch.log').write_text(result.stdout+result.stderr)
if result.returncode:raise SystemExit(result.stdout+result.stderr)
record=json.loads((OBJ/'osfmk/DEVELOPMENT/start.o.json').read_text().strip().rstrip(','))
command=record['arguments'].copy()
command=[str(work/'osfmk/arm64/start.s') if value==record['file'] else value for value in command]
command[command.index('-o')+1]=str(out/'start.o')
# Clang's -MJ record retains -E for XNU's two-stage assembler recipe.
command=[value for value in command if value not in ('-E','-MD','-MMD','-MP')]
for flag in ('-MF','-MJ','-MT','-MQ'):
    while flag in command:
        index=command.index(flag);del command[index:index+2]
if '-c' not in command:command.append('-c')
result=subprocess.run(command,cwd=record['directory'],capture_output=True,text=True,timeout=120)
(out/'compile.log').write_text(result.stdout+result.stderr)
(out/'compile-command.json').write_text(json.dumps(command,indent=2)+'\n')
if result.returncode:raise SystemExit(result.stdout+result.stderr)
archive=out/'mach.development.bcm2837.a'
shutil.copy2(CORE,archive)
members=subprocess.check_output(['/usr/bin/llvm-ar','t',str(archive)],text=True).splitlines()
assert members.count('start.o')==1
before=subprocess.check_output(['/usr/bin/llvm-ar','p',str(CORE),'start.o'])
(out/'start-before.o').write_bytes(before)
subprocess.run(['/usr/bin/llvm-ar','r',str(archive),str(out/'start.o')],check=True)
assert subprocess.check_output(['/usr/bin/llvm-ar','t',str(archive)],text=True).splitlines()==members
before_members=archive_members(CORE)
after_members=archive_members(archive)
assert [row for row in before_members if row[0]!='start.o']==[row for row in after_members if row[0]!='start.o'],'Other core objects changed'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report={'core_archive':str(archive),'core_archive_sha256':sha(archive),'old_core_archive_sha256':sha(CORE),
    'old_start_object_sha256':hashlib.sha256(before).hexdigest(),'start_object_sha256':sha(out/'start.o'),
    'source':str(source),'source_sha256':sha(source),'patched_source_sha256':sha(work/'osfmk/arm64/start.s'),
    'patch':str(patch),'patch_sha256':sha(patch),'member_count':len(members),
    'only_start_object_replaced':True,'phone_operations':False,'smp_hardware_verified':False}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
