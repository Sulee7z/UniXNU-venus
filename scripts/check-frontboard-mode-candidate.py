#!/usr/bin/env python3
"""Bind the targeted mode reader to original metadata, compiled code and the new image."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[1]
WORK = Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
OUT = ROOT / 'artifacts/venus-frontboard-mode-phone'
ANALYSIS = ROOT / 'artifacts/venus-frontboard-failure/frontboard-inspection.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text())


def need(ok, message):
    if not ok:
        raise SystemExit(message)


analysis = load(ANALYSIS)
need(analysis['pc']=='0x19f3d0744' and analysis['identity']['original_pc_is_brk_zero'], 'Trap identity mismatch')
klass = analysis['classes']['FBSDisplayMode']
expected = {'_width':(8,8), '_height':(16,8), '_preferredScale':(24,8), '_scaleOverride':(32,8),
            '_refreshRate':(40,8), '_gamut':(48,8), '_hdr':(56,8), '_rotation':(64,8), '_virtual':(72,1)}
actual = {i['name']:(i['offset'],i['size']) for i in klass['ivars']}
need(actual==expected, 'Original FBSDisplayMode field layout differs from the 80-byte reader')
need(any(m['implementation']=='0x19f3d0500' and m['types']=='@92@0:8Q16Q24Q32d40d48q56q64q72B80q84'
         for m in klass['methods']), 'Initializer signature/entry mismatch')
instructions = {r['pc']:r for r in analysis['instructions']}
need(instructions['0x19f3d0568']['word']=='aa0003f3', 'Initializer no longer retains self in x19')
need(instructions['0x19f3d0700']['reference']['string']=='FBSDisplayMode cannot be configured as requested : %@',
     'Error string does not belong to the trap branch')
need(instructions['0x19f3d0744']['word']=='d4200000', 'Original BRK mismatch')

candidate, previous = load(OUT/'candidate.json'), load(ROOT/'artifacts/venus-hid-phone/candidate.json')
kernel = OUT/'kernel/kernel.macho'
need(sha(kernel)==candidate['kernel_sha256']=='9334d42b3775d7e75e89d3d338d8429c64422b32a1f18a9c9eb659ba04c30a6f',
     'Kernel identity mismatch')
need(sha(OUT/'phone/boot-venus-unixnu.img')==candidate['boot_sha256']==
     'b31baa584619f9b9909103b1c691b2723a6a99be83f60360abeedcc4dd78ed7c', 'Boot image identity mismatch')
for field in ('owned_memory_bytes','unchanged_payload_files','fd_sha256','efi'):
    need(candidate[field]==previous[field], 'Unexpected control change: '+field)
need(candidate['a660_adt']['sha256']==previous['a660_adt']['sha256'], 'ADT changed')
without_tag = lambda args:[a for a in args.split() if not a.startswith('sheng-build-tag=')]
need(without_tag(candidate['args'])==without_tag(previous['args']), 'Functional boot arguments changed')
need('sheng-build-tag=fbs-mode-001' in candidate['args'].split(), 'Wrong build tag')

boot_report = load(WORK/'tree/build/boot-progress/build-report.json')
tests = load(ROOT/'artifacts/venus-exit-fault-checks/report.json')
need(tests['passed'], 'Actual fault/layout regressions did not pass')
for name in ('BootFaultProbe.c','BootFrontBoardMode.h','BootProgress.c','BootProgressLifecycle.h'):
    need(sha(DEVICE/'package/boot-progress'/name)==boot_report['sources'][name]==tests['sources'][name],
         'Source/compile/test mismatch: '+name)
qemu_dir = ROOT/'artifacts/venus-ufs-root/qemu-frontboard-mode-phone'
qemu, services = load(qemu_dir/'gdb-stop.json'), load(qemu_dir/'os-services.json')
need(qemu['kernel_sha256']==candidate['kernel_sha256']==services['kernel_sha256'] and
     qemu['stop_symbol']=='_native_owner_root_accepted_checkpoint' and not qemu['bounded_timeout_interrupted'],
     'Missing same-kernel bounded root checkpoint')
need(services['aks_state_passed'] and services['hid_state_passed'], 'AKS/HID initialization regressed')
need(sha(qemu_dir/'gdb-stop.json')==candidate['qemu_root_sha256'], 'QEMU receipt changed')

snapshots = OUT/'linked-inputs'
snapshots.mkdir(exist_ok=True)
for name in ('BootFaultProbe.c','BootFrontBoardMode.h'):
    shutil.copy2(DEVICE/'package/boot-progress'/name,snapshots/name)
shutil.copy2(WORK/'tree/build/boot-progress/build-report.json',snapshots/'boot-progress-report.json')
shutil.copy2(WORK/'tree/build/boot-progress/libBootProgress.a',snapshots/'libBootProgress.a')
shutil.copy2(ROOT/'artifacts/venus-exit-fault-checks/report.json',snapshots/'fault-test-report.json')
asm = subprocess.check_output(['/usr/bin/llvm-objdump','--disassemble','--no-show-raw-insn',
    '--disassemble-symbols=_boot_progress_exit_fault',str(kernel)],text=True)
need('<_copyin>' in asm and '<_snprintf>' in asm, 'Final recorder lacks actual copy/format calls')
(snapshots/'fault-recorder.disassembly.txt').write_text(asm)
result = {'date':'2026-10-28','device':'venus','kernel_sha256':candidate['kernel_sha256'],
    'boot_sha256':candidate['boot_sha256'],'candidate_sha256':sha(OUT/'candidate.json'),
    'original_inspection_sha256':sha(ANALYSIS),'error_message':'FBSDisplayMode cannot be configured as requested : %@',
    'original_object_layout':actual,'copy_bytes':80,'copy_source':'retained x19 at the exact SpringBoard BRK site',
    'capture_context':'own process ordinary exit; no new user-memory reads in exception handler',
    'host_tests':tests,'qemu_services':services,'qemu_root_passed':True,
    'diagnostic_fields':['width','height','preferredScale','scaleOverride IEEE754 bits','refreshRate IEEE754 bits',
                         'gamut','HDR','rotation','virtual'],
    'failure_behavior':'MODE copyerr=<code>; retain the original crash and bounded backtrace',
    'phone_tested':False,'specific_invalid_mode_field':None,
    'scope':'Targeted read-only diagnostic for the validated display-mode failure; not a display fix or a suppression of BRK'}
(DEVICE/'evidence/frontboard-mode-candidate.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: original field metadata/initializer/error branch, actual recorder regression, source receipts and QEMU control')
print('Candidate:',candidate['boot_sha256'])
