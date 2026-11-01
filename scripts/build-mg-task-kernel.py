#!/usr/bin/env python3
"""Replay native link with retained baseline libraries; replace only policy member.

Standalone output; original worktree objects and historical archives are not edited.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
TREE=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root/tree')
OBJ=TREE/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
LINK=OBJ/'mach.development.bcm2837.link';OUT=ROOT/'artifacts/venus-mg-query-009'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--baseline',action='store_true')
parser.add_argument('--scale-refresh',action='store_true',help='Build documented cache invalidation after original policy, without a task mount')
parser.add_argument('--scale-version',choices=('011','012'),default='011')
parser.add_argument('--attempt',type=int,default=1);args=parser.parse_args()
if not 1<=args.attempt<=9:parser.error('Invalid attempt')
if args.scale_refresh:OUT=ROOT/'artifacts'/('venus-scale-refresh-'+args.scale_version)
kind='baseline-link' if args.baseline else 'refresh-link' if args.scale_refresh else 'activation-link'
OUT.mkdir(exist_ok=True);work=OUT/(kind+f'-{args.attempt}');work.mkdir(exist_ok=False)
def sha(p):
    with Path(p).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
sys.path.insert(0,'/root/unixnu-build/UniXNU-sheng-base/scripts')
from unixnu.cli import parser as cli_parser
from unixnu.config import Context
from unixnu.kernel import linux_env
ctx=Context(cli_parser().parse_args(['status','-D',str(DEVICE),'--out','/root/unixnu-build/venus-legacy-full']))
os.environ['UNIXNU_TOOLCHAIN']='/root/unixnu-toolchain'
env={**os.environ,**linux_env(ctx)}
def run(command,name):
    result=subprocess.run([str(x) for x in command],env=env,cwd=OBJ,capture_output=True,text=True,timeout=240)
    (work/(name+'.log')).write_text(result.stdout+result.stderr)
    (work/(name+'-command.json')).write_text(json.dumps([str(x) for x in command],indent=2)+'\n')
    if result.returncode:raise SystemExit(result.stdout+result.stderr)
old=ROOT/'artifacts/venus-data-check-002/linked-inputs'
original=old/'libBootProgress.a'
if sha(original)!='47b2f9b66867efcd093d4f5a6e408d170c3919a50cb7de7a43b07f6a26d4c3de':raise ValueError('Retained boot archive changed')
boot=work/'libBootProgress.a';shutil.copy2(original,boot)
if not args.baseline:
    source=(old/'BootWatchdogPolicy.c').read_text()
    if hashlib.sha256(source.encode()).hexdigest()!='e46b0645daf8fa574b047879d27234d0c9e3072b39556892ec42030c42e2926a':raise ValueError('Original policy changed')
    if source.count('venus_boot_data_check(p,scratch);')!=1:raise ValueError('Policy hook ambiguous')
    if args.scale_refresh:
        header='BootScaleRefresh'+args.scale_version+'.h'
        source=source.replace('#include "BootDataCheck.h"','#include "BootDataCheck.h"\n#include "'+header+'"')
        if source.count('int sheng_boot_watchdog_policy(')!=1:raise ValueError('Original policy entry ambiguous')
        source=source.replace('int sheng_boot_watchdog_policy(','static int venus_original_watchdog_policy(')
        source+='\nint sheng_boot_watchdog_policy(void *process,uint64_t scratch) {\n  int result=venus_original_watchdog_policy(process,scratch);\n  if(!result) {\n    venus_scale'+args.scale_version+'_refresh_after_policy((proc_t)process,scratch);\n    venus_scale'+args.scale_version+'_checkpoint();\n  }\n  return result;\n}\n'
    else:
        source=source.replace('#include "BootDataCheck.h"','#include "BootDataCheck.h"\n#include "MGTaskMount.h"')
        source=source.replace('venus_boot_data_check(p,scratch);','venus_boot_data_check(p,scratch);\n  venus_mg_task_mount(p,scratch);')
    policy=work/'BootWatchdogPolicy.c';policy.write_text(source)
    for name in ('BootDataCheck.h','BootDataCheckCore.h'):shutil.copy2(old/name,work/name)
    if args.scale_refresh:
        for name in ('BootScaleRefresh'+args.scale_version+'.h','BootGestaltCache.h'):
            shutil.copy2(DEVICE/'package/boot-progress'/name,work/name)
    else:shutil.copy2(DEVICE/'package/MGTaskMount.h',work/'MGTaskMount.h')
    record=json.loads((OBJ/'bsd/DEVELOPMENT/kern_exec.o.json').read_text().strip().rstrip(','))
    command=[];arguments=record['arguments'];i=0
    while i<len(arguments):
        value=arguments[i]
        if value==record['file']:command.append(str(policy))
        elif value=='-o':command+=['-o',str(work/'BootWatchdogPolicy.o')];i+=1
        elif value in ('-MF','-MJ','-MT','-MQ'):i+=1
        elif value=='-Xclang' and arguments[i+1].startswith('-W'):i+=1
        elif value not in ('-MD','-MMD','-MP') and not value.startswith('-W'):command.append(value)
        i+=1
    command+=['-mgeneral-regs-only','-I',str(work),'-I',str(OBJ.parents[3]/'.cache/xnu-work/osfmk'),
              '-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-missing-designated-field-initializers']
    # Compile-record paths are absolute; preserve its compilation directory.
    result=subprocess.run(command,cwd=record['directory'],env=env,capture_output=True,text=True,timeout=180)
    (work/'policy-compile.log').write_text(result.stdout+result.stderr)
    (work/'policy-compile-command.json').write_text(json.dumps(command,indent=2)+'\n')
    if result.returncode:raise SystemExit(result.stdout+result.stderr)
    run(['xcrun','ar','r',boot,work/'BootWatchdogPolicy.o'],'archive')
arguments=shlex.split((LINK/'mach.development.bcm2837.linkarguments').read_text())
archives=shlex.split((LINK/'mach.development.bcm2837.linkarchives').read_text())
old_display=ROOT/'artifacts/venus-a660-live-phone/linked-inputs/libNativeLegacyDisplay.late.a'
display=work/'libNativeLegacyDisplay.late.a'
shutil.copy2(TREE/'build/native-legacy-display/libNativeLegacyDisplay.late.a',display)
# Retain the later HID/AKS members; remove only the subsequent DT-mirror probe.
probe=subprocess.check_output(['xcrun','ar','p',str(old_display),'LegacyDisplayProbe.o'],env=env,timeout=60)
(work/'LegacyDisplayProbe.o').write_bytes(probe)
run(['xcrun','ar','r',display,work/'LegacyDisplayProbe.o'],'display-archive')
archives=[value.replace(str(TREE/'build/boot-progress/libBootProgress.a'),str(boot)).replace(
    str(TREE/'build/native-legacy-display/libNativeLegacyDisplay.late.a'),str(display)) for value in archives]
native=work/'native.macho'
run(['xcrun','clang','-target','arm64-apple-ios17.0',*arguments,
     '-Wl,-force_load,'+str(LINK/'mach.development.bcm2837.a'),*archives,
     '-Wl,-alias_list,'+str(LINK/'mach.development.bcm2837.alias.exp'),
     '-o',native],'link')
crypto_source=b'_source_corecrypto14_bootstrap\0' in native.read_bytes()
if crypto_source:run(['python3',TREE/'scripts/seal-source-crypto-kernel.py',native],'crypto-seal')
result={'native_sha256':sha(native),'baseline':args.baseline,'boot_archive_sha256':sha(boot),
        'retained_display_archive_sha256':sha(display),'kernel_objects_archive_sha256':sha(LINK/'mach.development.bcm2837.a'),
        'source_hook_sha256':None if args.baseline else sha(work/('BootScaleRefresh'+args.scale_version+'.h' if args.scale_refresh else 'MGTaskMount.h')),
        'crypto_mode':'source' if crypto_source else 'prelinked',
        'scope':'Standalone native link; underlying kernel object archive preserved. Baseline identity must be established before packaging.'}
(work/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
