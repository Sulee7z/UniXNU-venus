#!/usr/bin/env python3
"""Compile own ST backend/HID plus shared GENI with the real iOS17 XNU recipes."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import subprocess
ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus'
TREE=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root/tree')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--hid-test',action='store_true',help='QEMU-only substitute input; never package for phone')
parser.add_argument('--startup-report',action='store_true',help='Build bounded prelaunchd status writer')
parser.add_argument('--build-tag',default=None);parser.add_argument('--report-dir',default=None)
args=parser.parse_args()
defines=[]
if args.build_tag:defines.append('-DVENUS_ST_REPORT_BUILD="'+args.build_tag+'"')
if args.report_dir:defines.append('-DVENUS_ST_REPORT_DIRECTORY="'+args.report_dir+'"')
OBJ=TREE/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837';OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=False)
INCLUDE=[DEVICE/'package/VenusStTouch',ROOT/'sources/UniXNU-guide/drivers/QcomGeniSpi',TREE/'build/sheng-hid-input',TREE/'.cache/xnu-work/osfmk']
os.environ.setdefault('CCC_OVERRIDE_OPTIONS','# +-Wno-missing-designated-field-initializers +-Wno-unused-but-set-global')
cpp=json.loads((OBJ/'iokit/DEVELOPMENT/IOPlatformExpert.cpo.json').read_text().strip().rstrip(','))
c=json.loads((OBJ/'bsd/DEVELOPMENT/kern_exec.o.json').read_text().strip().rstrip(','))
units=[DEVICE/'package/VenusStTouch/VenusStProtocol.c',DEVICE/'package/VenusStTouch/VenusStGeniTransport.c',ROOT/'sources/UniXNU-guide/drivers/QcomGeniSpi/GeniSpi.c',
       DEVICE/'package/VenusStTouch/VenusStTouch.cpp',DEVICE/'package/VenusStTouch/VenusHidTouch.cpp',DEVICE/'package/HidInputProbe.cpp']
if args.hid_test:
    units=[p for p in units if p.stem not in ('GeniSpi','VenusStTouch','VenusStGeniTransport')]+[DEVICE/'tests/VenusStQemuProducer.cpp']
if args.startup_report:
    if args.hid_test:parser.error('Startup report requires the real backend')
    control=ROOT/'artifacts/venus-scale-refresh-012/refresh-link-3'
    source=(control/'BootWatchdogPolicy.c').read_text()
    assert source.count('    venus_scale012_checkpoint();')==1
    source=source.replace('#include "BootScaleRefresh012.h"','#include "BootScaleRefresh012.h"\n#include "BootStTouchReport.h"\n#include "BootMetalReport.h"')
    source=source.replace('    venus_scale012_checkpoint();','    venus_scale012_checkpoint();\n    venus_st_report_after_policy((proc_t)process,scratch);\n    venus_metal_report_after_policy((proc_t)process,scratch);')
    (OUT/'BootWatchdogPolicy.c').write_text(source)
    for header in ('BootDataCheck.h','BootDataCheckCore.h','BootScaleRefresh012.h','BootGestaltCache.h'):
        (OUT/header).write_bytes((control/header).read_bytes())
    (OUT/'BootStTouchReport.h').write_bytes((DEVICE/'package/boot-progress/BootStTouchReport.h').read_bytes())
    (OUT/'BootMetalReport.h').write_bytes((DEVICE/'package/boot-progress/BootMetalReport.h').read_bytes())
    INCLUDE.append(OUT);units.append(OUT/'BootWatchdogPolicy.c')
snapshots=OUT/'sources';snapshots.mkdir()
for source in units:(snapshots/source.name).write_bytes(source.read_bytes())
header_records=[]
for header in sorted((DEVICE/'package/VenusStTouch').glob('*.h')):
    (snapshots/header.name).write_bytes(header.read_bytes())
    header_records.append({'path':str(header),'sha256':hashlib.sha256(header.read_bytes()).hexdigest()})
records=[];objects=[]
for source in units:
    recipe=cpp if source.suffix=='.cpp' else c;target=OUT/(source.stem+'.o');parts=recipe['arguments'];command=[];i=0
    while i<len(parts):
        item=parts[i]
        if item==recipe['file']:command.append(str(source))
        elif item=='-o':command.extend(['-o',str(target)]);i+=1
        elif item in ('-MF','-MJ','-MT','-MQ'):i+=1
        elif item=='-Xclang' and parts[i+1].startswith('-W'):i+=1
        elif item not in ('-MD','-MMD','-MP') and not item.startswith('-W'):command.append(item)
        i+=1
    command+=['-mgeneral-regs-only','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-deprecated-declarations','-Wno-misleading-indentation',
              '-Wno-deprecated-enum-enum-conversion','-Wno-c99-designator','-Wno-reorder-init-list','-Wno-unnecessary-virtual-specifier',*defines]
    for path in INCLUDE:command+=['-I',str(path)]
    result=subprocess.run(command,cwd=recipe['directory'],capture_output=True,text=True,timeout=300)
    (OUT/(source.stem+'.log')).write_text(result.stdout+result.stderr);(OUT/(source.stem+'.command.json')).write_text(json.dumps(command,indent=2)+'\n')
    if result.returncode:print('FAILED; read',OUT/(source.stem+'.log'));raise SystemExit(result.returncode)
    if source.stem in ('VenusHidTouch','NativeHidInput'):
        late=OUT/(source.stem+'.late.o');initializer='__GLOBAL__sub_I_'+source.name
        result=subprocess.run(['python3',str(TREE/'scripts/macho-late-init.py'),str(target),str(late),
            '--initializer',initializer],capture_output=True,text=True,timeout=120)
        (OUT/(source.stem+'.late.log')).write_text(result.stdout+result.stderr)
        if result.returncode:print('FAILED; read',OUT/(source.stem+'.late.log'));raise SystemExit(result.returncode)
        headers=subprocess.check_output(['/usr/bin/llvm-objdump','--macho','--section-headers',str(late)],text=True)
        if '__mod_init_func' in headers:raise SystemExit('Late HID object still has an automatic initializer')
        objects.append(late)
        records.append({'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'object':str(target),'object_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'late_object':str(late),'late_object_sha256':hashlib.sha256(late.read_bytes()).hexdigest(),
            'deferred_initializer':initializer})
        continue
    if source.stem not in ('HidInputProbe','BootWatchdogPolicy'):objects.append(target)
    records.append({'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'object':str(target),'object_sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
library=OUT/'libVenusStTouch.a';library.unlink(missing_ok=True)
subprocess.run(['/usr/bin/llvm-ar','rcs',str(library),*[str(p) for p in objects]],check=True)
record={'device':'venus','os':'ipados-17.7.11-21H461','qemu_only':args.hid_test,'startup_report':args.startup_report,
        'protocol':'stm-fts-spi','hid_backend':'custom' if args.hid_test else 'mainline',
        'requires_touch_stub_replacement':not args.hid_test,'headers':header_records,
        'build_tag':args.build_tag,'report_dir':args.report_dir,'objects':records,'library_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),
        'hid_abi_header_sha256':hashlib.sha256((TREE/'build/sheng-hid-input/OriginalHidDeviceABI.h').read_bytes()).hexdigest(),
        'scope':'Actual XNU/IOKit compile, not linked or hardware-qualified touch. New HidInputProbe object replaces only its member in an isolated candidate archive.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
