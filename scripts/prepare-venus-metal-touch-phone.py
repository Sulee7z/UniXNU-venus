#!/usr/bin/env python3
"""Prepare separate Metal or own-ST one-shot candidates from welcome012."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus';CONTROL=ROOT/'artifacts/venus-scale-refresh-012'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--kind',choices=('metal','touch','metal-touch'),required=True)
parser.add_argument('--version',default=None);parser.add_argument('--check',action='store_true')
parser.add_argument('--kernel-dir',type=Path,default=ROOT/'artifacts/venus-metal-touch/kernel-link-5')
parser.add_argument('--qemu-name',default='qemu-metal-touch-default-off-r3');parser.add_argument('--skip-qemu',action='store_true');parser.add_argument('--allow-hid-codec-change',action='store_true')
parser.add_argument('--smp-adt',type=Path,help='Hardware-qualified CPU/PSCI-only ADT replacement')
parser.add_argument('--addon-dir',type=Path,default=ROOT/'artifacts/venus-metal13/addon-r2')
args=parser.parse_args()
VERSION=args.version or ('013' if args.kind=='metal' else '014')
metal=args.kind in ('metal','metal-touch');touch=args.kind in ('touch','metal-touch')
if not VERSION.isdigit():parser.error('Version must be numeric')
OUT=ROOT/'artifacts'/('venus-'+args.kind+'-'+VERSION);PHONE=OUT/'phone';KERNEL=args.kernel_dir
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(command):return subprocess.check_output([str(p) for p in command],timeout=300)
def fat(image,name):return run(['mtype','-i',image,'::/EFI/UniXNU/'+name])
control=json.loads((CONTROL/'candidate.json').read_text());assert sha(CONTROL/'phone/boot-venus-unixnu.img')==control['image_sha256']=='38245b0ec67db7766f9ef91ce251569c199872bf94e133b53c81e6b7c17cda11'
build=json.loads((KERNEL/'report.json').read_text());assert not build.get('qemu_only',False),'Never package a QEMU-only producer'
startup_report=touch and bool(build.get('startup_report'))
mainline_hid=build.get('hid_backend')=='mainline' or VERSION in ('027','028','029','030','031','032','033','034')
hid_qemu_reused=False
if not args.skip_qemu:
    qdir=ROOT/'artifacts/venus-ufs-root'/args.qemu_name;q=json.loads((qdir/'os-services.json').read_text());assert q['aks_state_passed'] and q['hid_state_passed'] and q['kernel_sha256']==sha(KERNEL/'kernel.macho')
if startup_report:
    touch_build=json.loads((Path(build['touch_build'])/'report.json').read_text())
    assert touch and build.get('startup_report')
    touch_version=build.get('touch_baseline_version',VERSION)
    assert touch_build.get('build_tag')=='touch-'+touch_version and touch_build.get('report_dir')=='/private/var/db/venus-st-'+touch_version
    assert 'com.apple.iokit.IOHIDEventDriverSafeBoot' in json.loads((KERNEL/'kernel.json').read_text())['codeless_components']
    for row in touch_build['objects']:
        assert sha(Path(row['source']))==row['source_sha256'],'Source changed since compilation'
    for row in touch_build.get('headers',[]):
        assert sha(Path(row['path']))==row['sha256'],'Header changed since compilation'
    if build.get('hid_backend')=='mainline':
        assert build.get('touch_stubs_replaced') and build.get('mainline_hid_object_sha256')
    if not mainline_hid:
        hid=json.loads((ROOT/'artifacts/venus-st-touch/qemu-hid-matching/report.json').read_text())
        tested=json.loads((ROOT/'artifacts/venus-st-touch/hid-test-matching/report.json').read_text())
        hid_qemu_reused=hid['passed'] and all(
            next(row for row in tested['objects'] if Path(row['source']).name==name)['object_sha256']==
            next(row for row in touch_build['objects'] if Path(row['source']).name==name)['object_sha256']
            for name in ('VenusHidTouch.cpp','VenusStProtocol.c'))
        if not args.allow_hid_codec_change:assert hid_qemu_reused,'Changed HID/codec has no matching QEMU qualification'
    if not args.skip_qemu:
        journal=json.loads((ROOT/'artifacts/venus-st-touch/qemu-startup-report/report.json').read_text())
        assert journal['passed']
oldadt=fat(CONTROL/'phone/payload.img','Payloads/kernel.macho.adt');adt=oldadt
flags=[f for f in control['args'].split() if not f.startswith(('sheng-build-tag=','venus-gestalt-refresh=','sheng-gpu-power=','sheng-gpu-metal='))]
flags+=['sheng-gpu-power='+('9' if metal else '0'),'sheng-gpu-metal='+('1' if metal else '0'),
        'venus-st-touch='+('3' if touch else '0'),'sheng-build-tag='+args.kind+'-'+VERSION]
if startup_report:flags+=['venus-st-report=1']
if touch and mainline_hid:flags+=['sheng-touch-hid=1','venus-st-custom-hid=0']
addon=args.addon_dir
if metal:
    flags+=['zeta-gpu-metal=1','sheng-gpu-addon=1']
    spec=importlib.util.spec_from_file_location('adtcodec',DEVICE/'scripts/inject-a660-firmware-adt.py');codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
    tree=codec.parse(oldadt);chosen=codec.find(tree,'chosen');memory=codec.find(chosen,'memory-map')
    assert 'GpuAddon' not in dict(memory.props);memory.props.append(('GpuAddon',bytes(16)));adt=codec.dump(tree)
    memory.props=[(k,v) for k,v in memory.props if k!='GpuAddon'];assert codec.dump(tree)==oldadt
if args.smp_adt:
    assert metal and build.get('smp_build') and VERSION in ('038','039','040','041')
    smp_adt_report=json.loads(args.smp_adt.with_name('report.json').read_text())
    assert sha(args.smp_adt)==smp_adt_report['adt_sha256'] and smp_adt_report['cpu_count']<=smp_adt_report['compiled_max_cpus']==4
    adt=args.smp_adt.read_bytes()
    flags=[flag for flag in flags if not flag.startswith(('cpus=','cpumask='))]
    flags+=['cpus='+str(smp_adt_report['cpu_count']),'sheng-smp=1','armcpu-self-ipi=1']
kernelargs=' '.join(flags);assert len(kernelargs.encode())<1024
if not args.check:
    PHONE.mkdir(parents=True,exist_ok=False)
    for name in ('payload.img','SILICIUM_UEFI.fd','UniXNU.efi','UniXNUDxe.efi','DarwinBoot.efi'):shutil.copy2(CONTROL/'phone'/name,PHONE/name)
    config=(CONTROL/'phone/unixnu.toml').read_text();assert config.count(control['args'])==1;config=config.replace(control['args'],kernelargs)
    (PHONE/'unixnu.toml').write_text(config);(OUT/'kernel.macho.adt').write_bytes(adt)
    files=[(KERNEL/'kernel.macho','Payloads/kernel.macho'),(PHONE/'unixnu.toml','unixnu.toml'),(OUT/'kernel.macho.adt','Payloads/kernel.macho.adt')]
    if metal:files += [(addon/'kernel.macho.gpuaddon','Payloads/kernel.macho.gpuaddon'),(addon/'kernel.macho.trustcache','Payloads/kernel.macho.trustcache')]
    for source,target in files:run(['mcopy','-o','-i',PHONE/'payload.img',source,'::/EFI/UniXNU/'+target])
    run(['python3',ROOT/'tools/package-venus-uefi.py','--tree',ROOT/'ports/uefi-venus','--workspace',ROOT,'--artifacts',PHONE,'--payload',PHONE/'payload.img'])
assert fat(PHONE/'payload.img','Payloads/kernel.macho')==(KERNEL/'kernel.macho').read_bytes()
assert fat(PHONE/'payload.img','Payloads/kernel.macho.adt')==adt
if metal:assert fat(PHONE/'payload.img','Payloads/kernel.macho.gpuaddon')==(addon/'kernel.macho.gpuaddon').read_bytes()
assert fat(PHONE/'payload.img','Payloads/scratch-data.img')==fat(CONTROL/'phone/payload.img','Payloads/scratch-data.img')
trust=addon/'kernel.macho.trustcache' if metal else None
assert fat(PHONE/'payload.img','Payloads/kernel.macho.trustcache')==(trust.read_bytes() if trust else fat(CONTROL/'phone/payload.img','Payloads/kernel.macho.trustcache'))
verification=json.loads((PHONE/'verification.json').read_text());oldv=json.loads((CONTROL/'phone/verification.json').read_text())
assert verification['roundtrip_verified'] and not verification['uefi_memory_conflicts'] and verification['fd_sha256']==oldv['fd_sha256'] and verification['efi']==oldv['efi']
assert sha(PHONE/'boot-venus-unixnu.img')==verification['sha256']
record={'device':'venus','version':VERSION,'kind':args.kind,'image':str(PHONE/'boot-venus-unixnu.img'),'image_sha256':verification['sha256'],'image_bytes':verification['bytes'],
    'kernel_sha256':sha(KERNEL/'kernel.macho'),'args':kernelargs,'welcome012_control_preserved':True,'original_seed_adt_geometry_fd_efi_preserved':True,
    'native_default_off_qemu_systemos_aks_hid_passed':not args.skip_qemu,'qemu_verified':not args.skip_qemu,
    'qemu_skip_reason':('Original OS/SystemOS host raw images are absent after workspace cleanup; no QEMU pass claimed' if args.skip_qemu else None),
    'phone_tested':False,
    'operation_scope':('One A660 mode9/Metal publish RAM boot. Install own signed5file addon under /private/var/ngpu/addons; normal Data/cache writes; additive trust; no new launch job/MG invalidation/reset/flash.' if args.kind=='metal' else
        ('One combined A660 Metal publish plus own ST mode3 RAM boot. Install own signed5file Metal addon and run deferred HID metaclass registration, GPIO154/RPMh LDO2 power, GENI loopback and K2 0x3936/0x3639 identify; normal Data/cache writes; no touch flash/NVM/calibration/lockdown and no reset/flash.' if args.kind=='metal-touch' else
        'One own ST mode3 RAM boot with deferred HID metaclass registration. XO/SE11 clock vote,GPIO48-51 SPI/GPIO23 polling,AVDDsourceGPIO132 high,TPenableGPIO154 high,RPMh ldoc2 1.8V,GPIO22 MCU reset,existing firmware3936/3639 identify,volatileIER+active scan and original17 HID. Normal Data writes; no touch flash/NVM/calibration/lockdown command/reset Data/flash.')),
    'scope':'Prepared separately testable real-source candidates. GPU pixels/Metal discovery or physical touch remain hardware qualification.'}
if build.get('protocol')=='stm-fts-spi':
    record['operation_scope']=('STM FTS SPI candidate: actual reset-low latch, bounded controller-ready polling, '
        'strict little-endian 0x3936 identification, raw A0 00 01 scan with echo verification, '
        '0x87 FIFO and corrected 0x23 motion/0x33 lift, CS held 10us before controller deassertion. '
        'Retained mainline NativeHidInput; normal Data writes; no touch firmware download or NVM operations.')
if startup_report:
    report_dir=touch_build['report_dir']
    record.update(hid_backend='mainline' if mainline_hid else 'custom',
        protocol=build.get('protocol'),hid_matching_root='com.apple.iokit.IOHIDEventDriver' if mainline_hid else 'com.apple.iokit.IOHIDEventDriverSafeBoot',
        hid_qemu_reused=hid_qemu_reused,hid_qemu_reports=3 if hid_qemu_reused else None,
        startup_report=report_dir+'/startup.jsonl',startup_report_phase='prelaunchd only',
        startup_report_host_apfs_verified=not args.skip_qemu)
    if VERSION=='041':
        record.update(metal_report='/private/var/db/venus-metal-041/startup.json',
            metal_report_phase='prelaunchd only',metal_report_fields=['gpu_power_stage','addon_stage','addon_status','metal_stage','metal_status','kext_status','gpu_done'])
    record['operation_scope']+=' Adds original codeless digitizer matching; creates root0700 '+report_dir+' and exclusive0600 startup.jsonl with initial hardware/HID status, syscall readback/file/full/directory/medium sync. Does not overwrite an existing report.'
if build.get('gpu_build'):
    gpu=json.loads((Path(build['gpu_build'])/'build-report.json').read_text())
    assert metal and sha(KERNEL/'libVenusA660.a')==build['gpu_archive_sha256']==gpu['archive_sha256']
    for kind in ('input_files','object_files'):
        for name,digest in gpu[kind].items():assert sha(Path(name))==digest,'GPU inputs changed since compilation: '+name
    assert sha(KERNEL/'BootWatchdogPolicy.c')==build['boot_policy_sha256']
    record.update(metal_discovery=build['metal_discovery'],gpu_archive_sha256=build['gpu_archive_sha256'],
        touch_baseline_version=build['touch_baseline_version'],touch_archive_sha256=build['touch_archive_sha256'],
        mainline_hid_object_sha256=build['mainline_hid_object_sha256'],
        addon_sha256=sha(addon/'kernel.macho.gpuaddon'),gpu_hardware_rendering_verified=False)
    record['operation_scope']='A660 mode9 plus real original-IOAcceleratorES Metal adapter, late IOGPUFamily registration and bounded prelaunchd wait. Existing signed Metal/Turnip addon and additive trust; normal Data/cache writes. Exact successful035 STM producer and mainline HID consumer retained; no touch firmware download, Data reset, flash or erase.'
if args.smp_adt:
    record.update(cpu_count_requested=smp_adt_report['cpu_count'],cpu_affinities=smp_adt_report['cpu_affinities'],psci='smc',
                  smp_reset_affinity_bits=build['smp_reset_affinity_bits'],smp_hardware_verified=False)
    record['operation_scope']+=' Requests '+str(smp_adt_report['cpu_count'])+' measured SM8350 cores through PSCI with corrected Affinity1 reset matching and self-IPI startup; actual multi-core scheduling still needs device verification.'
if metal and addon!=ROOT/'artifacts/venus-metal13/addon-r2':
    addon_report=json.loads((addon/'report.json').read_text())
    assert sha(addon/'kernel.macho.gpuaddon')==addon_report['addon_sha256']
    assert sha(addon/'kernel.macho.trustcache')==addon_report['trust_sha256']
    assert addon_report['trust_layout']=='single-static' and addon_report['trust_merge']['all_original_attributes_preserved']
    record.update(addon_dir=str(addon),trust_layout='single-static',trust_merge=addon_report['trust_merge'],
                  trust_sha256=addon_report['trust_sha256'],plugin_sha256=addon_report['binaries']['plugin']['sha256'])
    record['operation_scope']+=' Updated zeta-aligned iOS17 plugin entry: plain framebuffer/IOSurface constraints, persistent cache selection and initialization failure reasons; merged static trust retains all original entry attributes. Actual GPU/Metal execution remains unverified.'
if args.check:assert json.loads((OUT/'candidate.json').read_text())==record
else:(OUT/'candidate.json').write_text(json.dumps(record,indent=2)+'\n');(DEVICE/'evidence'/(args.kind+VERSION+'-candidate.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:record[k] for k in ('image','image_sha256','image_bytes','kernel_sha256','operation_scope')},indent=2))
