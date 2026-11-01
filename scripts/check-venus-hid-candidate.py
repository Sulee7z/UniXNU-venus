#!/usr/bin/env python3
"""Verify the saved HID candidate, callable hooks and real QEMU service controls."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[1]
WORK = Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
TREE = WORK / 'tree'
OUT = ROOT / 'artifacts/venus-hid-phone'
EXPECTED_KERNEL = '7a3f0b0952b04d68481af31a2c6821826c1cf9cc4b9f189ea44435a7fa640f79'
EXPECTED_BOOT = '96a2c7476da6946261e08993014d96ab866e7e602644a76ad76049afaef5c456'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text())


def need(ok, message):
    if not ok:
        raise SystemExit(message)


candidate = load(OUT / 'candidate.json')
kernel = OUT / 'kernel/kernel.macho'
need(sha(kernel) == candidate['kernel_sha256'] == EXPECTED_KERNEL, 'Saved kernel changed')
need(sha(OUT / 'phone/boot-venus-unixnu.img') == candidate['boot_sha256'] == EXPECTED_BOOT, 'Saved image changed')
need(sha(WORK / 'kernel/kernel.macho') == EXPECTED_KERNEL, 'Build tree no longer matches this candidate')
args = set(candidate['args'].split())
need({'offline-key-events=1','sheng-aks=1','offline-hid-input=1','offline-hid-home=1',
      'sheng-touch=0','sheng-fb-gpu=0','sheng-build-tag=hid-001'} <= args, 'Unexpected candidate gates')
need(not any(a.startswith(('sheng-touch-hid=', 'offline-hid-auto-home=', 'sheng-log=')) for a in args),
     'Unexpected touch, scripted input or log-write gate')
need(candidate['owned_memory_bytes'] == 0x40000000, 'Unexpected memory window')

sys.path.insert(0, str(TREE / 'kits/XnuPrelink'))
from native_prelink import macho, backed_offset, exports
blob = kernel.read_bytes()
image = macho(blob)
names = {name: address for address, group in exports(blob, image).items() for name in group}
required = ['_native_hid_input_probe','_native_hid_input_allocate','_native_keystore_probe',
            '__GLOBAL__sub_I_NativeHidInput.cpp','__GLOBAL__sub_I_NativeKeyStoreEvents.cpp',
            '_native_touch_set_sink','_native_buttons_set_sink']
need(all(names.get(name) for name in required), 'Missing real HID/AKS provider or callback')
for name in ('_native_touch_set_sink','_native_buttons_set_sink'):
    at = backed_offset(image['segments'], names[name], 4, len(blob))
    need(blob[at:at+4] == bytes.fromhex('c0035fd6'), name + ' must only return (no producer installed)')
storage = {'_native_touch_seq':4, '_native_touch_count':4, '_native_touch_hid_reports':4,
           '_native_touch_ids':48, '_native_touch_xs':48, '_native_touch_ys':48,
           '_native_hid_input_events':32, '_native_hid_input_results':32}
for name, size in storage.items():
    address = names.get(name, 0)
    need(address and any(seg['name']=='__DATA' and s['va'] <= address and address+size <= s['va']+s['size']
                        for seg in image['segments'] for s in seg['sections']),
         name + ' does not resolve to writable kernel storage')
calls = subprocess.check_output(['/usr/bin/llvm-objdump','--disassemble','--no-show-raw-insn',
    '--disassemble-symbols=_native_legacy_display_late_probe',str(kernel)], text=True)
for name in ('_native_keystore_probe','_native_hid_input_probe'):
    need(re.search(r'\bbl\s+0x'+f'{names[name]:x}'+r'\s+<'+re.escape(name)+r'>', calls),
         'Late probe does not call '+name)

build = load(TREE / 'build/native-legacy-display/build-report.json')
boot = load(TREE / 'build/boot-progress/build-report.json')
hid = load(TREE / 'build/sheng-hid-input/abi-audit.json')
for relative, digest in build['source_sha256'].items():
    need(sha(TREE / relative) == digest, 'Display input changed: '+relative)
need(hid['original_slots']==207 and hid['original_instance_size']==208 and
     hid['owned_slots']==[0,1,7,14,86,87,111,171,173,180], 'HID dispatch audit mismatch')
need(sha(TREE / 'drivers/ShengHidInput/NativeHidInput.cpp') == hid['source_sha256'], 'HID source changed')
screen = load(ROOT / 'artifacts/venus-a660-live-checks/screen-report.json')
need(screen['passed'], 'Screen regression failed')
for name, digest in screen['source_sha256'].items():
    need(digest == boot['sources'][name] == sha(DEVICE / 'package/boot-progress' / name),
         'Screen test, compile receipt and source differ: '+name)

runtime = {}
for variant in ('hid-phone', 'hid-disabled'):
    folder = ROOT / 'artifacts/venus-ufs-root' / ('qemu-'+variant)
    stop, services = load(folder / 'gdb-stop.json'), load(folder / 'os-services.json')
    need(stop['kernel_sha256']==services['kernel_sha256']==EXPECTED_KERNEL and
         stop['stop_symbol']=='_native_owner_root_accepted_checkpoint' and not stop['bounded_timeout_interrupted'],
         'Missing actual QEMU root checkpoint: '+variant)
    need(services['aks_state_passed'] and services['hid_state_passed'], 'Service control failed: '+variant)
    need(services['aks_enabled']==services['hid_enabled']==(variant=='hid-phone'), 'Gate control mismatch')
    runtime[variant] = {'report':services, 'stop_sha256':sha(folder / 'gdb-stop.json'),
                        'service_report_sha256':sha(folder / 'os-services.json')}
need(runtime['hid-phone']['stop_sha256']==candidate['qemu_root_sha256'], 'Candidate QEMU identity differs')

snapshots = OUT / 'linked-inputs'
snapshots.mkdir(exist_ok=True)
archives = {}
for directory, archive, receipt in [('boot-progress','libBootProgress.a','build-report.json'),
    ('native-legacy-display','libNativeLegacyDisplay.late.a','build-report.json'),
    ('sheng-hid-input','libShengHidInput.a','abi-audit.json'), ('venus-a660','libVenusA660.a','build-report.json')]:
    folder = TREE / 'build' / directory
    need(sha(folder / archive)==load(folder / receipt)['archive_sha256'], 'Archive changed: '+archive)
    shutil.copy2(folder / archive, snapshots / archive)
    shutil.copy2(folder / receipt, snapshots / (directory+'-report.json'))
    archives[archive] = sha(folder / archive)
for relative in ('package/DisplayProbeStubs.c','package/HidInputProbe.cpp','package/KeyStoreProbe.cpp',
                 'package/boot-progress/BootProgress.c','package/boot-progress/BootProgressAbsent.S',
                 'scripts/build-sheng-hid-input.py','scripts/build-gop-legacy-display.py'):
    shutil.copy2(DEVICE / relative, snapshots / Path(relative).name)

result = {'device':'venus', 'date':'2026-10-28', 'kernel_sha256':EXPECTED_KERNEL, 'boot_sha256':EXPECTED_BOOT,
    'candidate_sha256':sha(OUT / 'candidate.json'), 'kernel_symbols':{n:hex(names[n]) for n in required},
    'readable_touch_storage':{n:hex(names[n]) for n in storage}, 'hid_abi':hid,
    'compiled_archives':archives, 'qemu_controls':runtime, 'screen_regression':screen,
    'service_telemetry_row':39, 'scope':'Offline keyboard/Home HID initialization; no Venus touch or button producer',
    'phone_tested':False, 'springboard_failure_cause_confirmed':False,
    'correction':'The actual bsd_autoconf/late probe precedes root acceptance; QEMU now verifies real AKS/HID initialization.'}
(DEVICE / 'evidence/hid-candidate.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: callable hooks, real state storage, final call targets, 207-slot HID ABI, source receipts and QEMU on/off controls')
print('Candidate:', OUT / 'phone/boot-venus-unixnu.img', EXPECTED_BOOT)
