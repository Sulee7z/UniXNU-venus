#!/usr/bin/env python3
"""Retain012 native inputs; replace HID probe member and add own ST archive."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus';CONTROL=ROOT/'artifacts/venus-scale-refresh-012/refresh-link-3'
TREE=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root/tree');OBJ=TREE/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837';LINK=OBJ/'mach.development.bcm2837.link'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--attempt',type=int,required=True)
parser.add_argument('--touch-build',type=Path,required=True);parser.add_argument('--strip-touch-stubs',action='store_true')
parser.add_argument('--gpu-build',type=Path,help='Qualified replacement A660 archive with the iOS17 Metal adapter')
parser.add_argument('--smp-build',type=Path,help='Isolated native reset-vector correction')
args=parser.parse_args()
OUT=ROOT/'artifacts/venus-metal-touch'/f'kernel-link-{args.attempt}';OUT.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,'/root/unixnu-build/UniXNU-sheng-base/scripts')
from unixnu.cli import parser as cli_parser
from unixnu.config import Context
from unixnu.kernel import linux_env
ctx=Context(cli_parser().parse_args(['status','-D',str(DEVICE),'--out','/root/unixnu-build/venus-legacy-full']));os.environ['UNIXNU_TOOLCHAIN']='/root/unixnu-toolchain';env={**os.environ,**linux_env(ctx)}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(command,name):
    result=subprocess.run([str(p) for p in command],cwd=OBJ,env=env,capture_output=True,text=True,timeout=300);(OUT/(name+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(result.stdout+result.stderr)
    return result.stdout
build=json.loads((args.touch_build/'report.json').read_text())
for row in build.get('headers',[]):
    assert sha(Path(row['path']))==row['sha256'],'Header changed since compilation'
for row in build['objects']:
    assert sha(Path(row['source']))==row['source_sha256'] and sha(Path(row['object']))==row['object_sha256']
    if 'late_object' in row:assert sha(Path(row['late_object']))==row['late_object_sha256']
for name in ('libBootProgress.a','libNativeLegacyDisplay.late.a'):shutil.copy2(CONTROL/name,OUT/name)
if build.get('startup_report'):
    run(['xcrun','ar','r',OUT/'libBootProgress.a',args.touch_build/'BootWatchdogPolicy.o'],'replace-policy-status-writer')
gpu_build = None
if args.gpu_build:
    gpu_build = json.loads((args.gpu_build/'build-report.json').read_text())
    assert gpu_build['metal_discovery']=='original-IOAcceleratorES-late-adapter'
    for kind in ('input_files','object_files'):
        for name, digest in gpu_build[kind].items():assert sha(Path(name))==digest, 'Changed GPU input: '+name
    assert sha(Path(gpu_build['archive']))==gpu_build['archive_sha256']
    shutil.copy2(gpu_build['archive'],OUT/'libVenusA660.a')
    # Keep the successful035 producer/consumer binary; only the boot ordering
    # adds a bounded wait for GPU initialization before process-local discovery.
    assert build['build_tag']=='touch-035' and build['hid_backend']=='mainline'
    policy=(args.touch_build/'BootWatchdogPolicy.c').read_text()
    marker='    venus_scale012_checkpoint();'
    assert policy.count(marker)==1
    policy='extern void venus_metal_wait_before_launchd(void);\n'+policy.replace(marker,marker+'\n    venus_metal_wait_before_launchd();')
    (OUT/'BootWatchdogPolicy.c').write_text(policy)
    command=json.loads((args.touch_build/'BootWatchdogPolicy.command.json').read_text())
    command=[part.replace(str(args.touch_build/'BootWatchdogPolicy.c'),str(OUT/'BootWatchdogPolicy.c')).replace(str(args.touch_build/'BootWatchdogPolicy.o'),str(OUT/'BootWatchdogPolicy.o')) for part in command]
    recipe=json.loads((OBJ/'bsd/DEVELOPMENT/kern_exec.o.json').read_text().strip().rstrip(','))
    result=subprocess.run(command,cwd=recipe['directory'],env=env,capture_output=True,text=True,timeout=300)
    (OUT/'gpu-policy.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(result.stdout+result.stderr)
    run(['xcrun','ar','r',OUT/'libBootProgress.a',OUT/'BootWatchdogPolicy.o'],'replace-gpu-startup-order')
display=OUT/'libNativeLegacyDisplay.late.a'
replace_stubs=args.strip_touch_stubs or build.get('requires_touch_stub_replacement',False)
if replace_stubs:
    stub=OUT/'DisplayProbeStubs.o'
    with open(stub,'wb') as output:
        subprocess.run(['xcrun','ar','p',str(display),'DisplayProbeStubs.o'],stdout=output,env=env,check=True)
    strip=[]
    for symbol in ('_native_touch_seq','_native_touch_count','_native_touch_hid_reports','_native_touch_xs','_native_touch_ys','_native_touch_ids','_native_touch_set_sink'):
        strip.extend(['--redefine-sym',symbol+'=_stub'+symbol[1:]])
    subprocess.run(['/usr/bin/llvm-objcopy',*strip,str(stub)],env=env,check=True)
    run(['xcrun','ar','d',display,'DisplayProbeStubs.o'],'remove-touch-stubs')
    run(['xcrun','ar','r',display,str(stub)],'replace-touch-stubs')
run(['xcrun','ar','r',display,args.touch_build/'HidInputProbe.o'],'replace-hid')
touch=OUT/'libVenusStTouch.a';shutil.copy2(args.touch_build/'libVenusStTouch.a',touch);assert sha(touch)==build['library_sha256']
arguments=shlex.split((LINK/'mach.development.bcm2837.linkarguments').read_text());archives=shlex.split((LINK/'mach.development.bcm2837.linkarchives').read_text())
archives=[p.replace(str(TREE/'build/boot-progress/libBootProgress.a'),str(OUT/'libBootProgress.a')).replace(str(TREE/'build/native-legacy-display/libNativeLegacyDisplay.late.a'),str(display)) for p in archives]
if gpu_build:
    old_gpu=str(TREE/'build/venus-a660/libVenusA660.a')
    assert sum(old_gpu in p for p in archives)==1
    archives=[p.replace(old_gpu,str(OUT/'libVenusA660.a')) for p in archives]
native=OUT/'native.macho';command=['xcrun','clang','-target','arm64-apple-ios17.0',*arguments,'-Wl,-force_load,'+str(LINK/'mach.development.bcm2837.a'),*archives,
    '-Wl,-force_load,'+str(touch),'-Wl,-alias_list,'+str(LINK/'mach.development.bcm2837.alias.exp'),'-o',str(native)]
if args.smp_build:
    smp=json.loads((args.smp_build/'report.json').read_text())
    assert smp['only_start_object_replaced'] and sha(Path(smp['core_archive']))==smp['core_archive_sha256']
    assert sha(Path(smp['source']))==smp['source_sha256'] and sha(Path(smp['patch']))==smp['patch_sha256']
    assert smp['old_core_archive_sha256']==sha(LINK/'mach.development.bcm2837.a')
    original_core='-Wl,-force_load,'+str(LINK/'mach.development.bcm2837.a')
    assert command.count(original_core)==1
    command=['-Wl,-force_load,'+smp['core_archive'] if part==original_core else part for part in command]
run(command,'native-link')
symbols=run(['/usr/bin/llvm-nm','--defined-only','--extern-only','-j',native],'defined-symbols').splitlines()
if gpu_build:
    for name in ('_venus_metal_publish','_venus_metal_wait_before_launchd','_native_adreno_accelerator_allocate'):
        assert symbols.count(name)==1, 'Metal adapter not uniquely linked: '+name
if replace_stubs:
    for name in ('seq','count','hid_reports','xs','ys','ids','set_sink'):
        assert symbols.count('_native_touch_'+name)==1,'Touch producer not uniquely linked: '+name
    assert symbols.count('_native_hid_input_allocate')==1,'Mainline HID consumer missing or duplicated'
native_hid=ROOT/'artifacts/venus-scale-refresh-012/refresh-link-3/libNativeLegacyDisplay.late.a'
hid_before=subprocess.check_output(['xcrun','ar','p',str(native_hid),'NativeHidInput.late.o'],env=env)
hid_after=subprocess.check_output(['xcrun','ar','p',str(display),'NativeHidInput.late.o'],env=env)
assert hid_before==hid_after,'Retained mainline HID object changed'
if b'_source_corecrypto14_bootstrap\0' in native.read_bytes():run(['python3',TREE/'scripts/seal-source-crypto-kernel.py',native],'crypto-seal')
def mod_init_bytes(path):
    output=subprocess.check_output(['/usr/bin/llvm-objdump','--macho','--section-headers',str(path)],text=True)
    return sum(int(line.split()[2],16) for line in output.splitlines() if '__mod_init_func' in line)
control_init=mod_init_bytes(CONTROL/'native.macho');native_init=mod_init_bytes(native)
if native_init!=control_init:raise SystemExit('Automatic initializer set changed: %d -> %d' % (control_init,native_init))
record={'native_sha256':sha(native),'qemu_only':build.get('qemu_only',False),'startup_report':build.get('startup_report',False),'touch_build':str(args.touch_build),'control_boot_archive_preserved':sha(OUT/'libBootProgress.a')==sha(CONTROL/'libBootProgress.a'),
        'protocol':build.get('protocol'),'hid_backend':build.get('hid_backend'),
        'touch_stubs_replaced':replace_stubs,'mainline_hid_object_sha256':hashlib.sha256(hid_after).hexdigest(),
        'mod_init_bytes':native_init,
        'touch_archive_sha256':sha(touch),'command':[str(p) for p in command],'scope':'New native kernel with own ST/HID code, original012 policy/RamBlock/GPU/display retained. Prelink/default-off qualification next.'}
if gpu_build:
    control_touch=json.loads((ROOT/'artifacts/venus-metal-touch/kernel-link-33/report.json').read_text())
    assert record['touch_archive_sha256']==control_touch['touch_archive_sha256']
    assert record['mainline_hid_object_sha256']==control_touch['mainline_hid_object_sha256']
    record.update(gpu_build=str(args.gpu_build),gpu_archive_sha256=sha(OUT/'libVenusA660.a'),
                  metal_discovery=gpu_build['metal_discovery'],touch_baseline_version='035',
                  touch_baseline_kernel_sha256=gpu_build['accelerator_abi']['kernel_sha256'],
                  boot_policy_sha256=sha(OUT/'BootWatchdogPolicy.c'),
                  scope='035 touch producer/consumer retained byte-for-byte; A660 archive adds the original IOAcceleratorES adapter and bounded prelaunch ordering. Hardware rendering remains unverified.')
if args.smp_build:record.update(smp_build=str(args.smp_build),core_archive_sha256=smp['core_archive_sha256'],smp_reset_affinity_bits=16)
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k!='command'},indent=2))
