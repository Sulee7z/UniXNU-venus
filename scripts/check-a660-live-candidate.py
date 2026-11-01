#!/usr/bin/env python3
"""Bind the saved live-diagnostic candidate to source, link and QEMU evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[1]
WORK = Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
TREE = WORK / 'tree'
OUT = ROOT / 'artifacts/venus-a660-live-phone'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text())


def need(value, message):
    if not value:
        raise SystemExit(message)


candidate = load(OUT / 'candidate.json')
kernel = OUT / 'kernel/kernel.macho'
need(sha(kernel) == candidate['kernel_sha256'], 'Saved kernel identity changed')
need(sha(OUT / 'phone/boot-venus-unixnu.img') == candidate['boot_sha256'], 'Saved boot image identity changed')
need(sha(WORK / 'kernel/kernel.macho') == candidate['kernel_sha256'], 'Build tree no longer belongs to this candidate')
screen = load(ROOT / 'artifacts/venus-a660-live-checks/screen-report.json')
boot = load(TREE / 'build/boot-progress/build-report.json')
gpu = load(TREE / 'build/venus-a660/build-report.json')
display = load(TREE / 'build/native-legacy-display/build-report.json')
need(screen['passed'], 'Host screen regression did not pass')
for name, digest in screen['source_sha256'].items():
    need(sha(DEVICE / 'package/boot-progress' / name) == digest == boot['sources'][name],
         'Screen test and compiled source differ: ' + name)
for name, digest in gpu['board_sources'].items():
    need(sha(DEVICE / 'package/Adreno660' / name) == digest, 'A660 compiled source differs: ' + name)
need(not gpu['missing_required_providers'], 'Required A660 closure provider missing')
need('sheng_gpu_power_probe' not in display['board_probe_stubs'], 'Display report still lists the old GPU stub')
need(candidate['owned_memory_bytes'] == 0x40000000, 'Expected 1 GiB owned memory')
for arg in ('sheng-gpu-power=9', 'sheng-fb-gpu=0', 'sheng-build-tag=a660-live'):
    need(arg in candidate['args'].split(), 'Unexpected candidate arguments: ' + arg)
qemu_path = ROOT / 'artifacts/venus-ufs-root/qemu-a660-live-phone/gdb-stop.json'
qemu = load(qemu_path)
need(sha(qemu_path) == candidate['qemu_root_sha256'] and qemu['kernel_sha256'] == candidate['kernel_sha256'],
     'QEMU evidence identity mismatch')
need(qemu['stop_symbol'] == '_native_owner_root_accepted_checkpoint' and not qemu['bounded_timeout_interrupted'],
     'No bounded owner-root checkpoint')

sys.path.insert(0, str(TREE / 'kits/XnuPrelink'))
from native_prelink import macho, backed_offset, exports
blob = kernel.read_bytes()
image = macho(blob)
names = {name: address for address, group in exports(blob, image).items() for name in group}
required = ['_native_gpu_diagnostic_row', '_native_gpu_power_stage', '_native_legacy_gpu_probe_calls',
            '_sheng_gpu_power_probe', '_native_legacy_display_late_probe', '_native_adreno_publish']
need(all(names.get(name) for name in required), 'Final kernel is missing the real diagnostic/probe providers')
symbols = subprocess.check_output(['/usr/bin/llvm-nm', str(kernel)], text=True)
trace = [line.split() for line in symbols.splitlines() if line.endswith('gTraceWordsE')]
need(len(trace) == 1, 'Expected unique owned trace buffer')
trace_address = int(trace[0][0], 16)
sections = [section for segment in image['segments'] for section in segment['sections']]
need(any(s['name'] == '__bss' and s['va'] <= trace_address and trace_address + 8192 <= s['va'] + s['size']
         for s in sections), 'Trace buffer is not fully in kernel BSS')

plan = load(OUT / 'kernel/kernel.json')
hid = next(e for e in plan['extents'] if e['module'] == 'com.apple.iokit.IOHIDFamily' and e['segment'] == '__TEXT_EXEC')
at = backed_offset(image['segments'], hid['va'], hid['size'], len(blob))
hid_sha = hashlib.sha256(blob[at:at + hid['size']]).hexdigest()

spec = importlib.util.spec_from_file_location('venus_adt', DEVICE / 'scripts/inject-a660-firmware-adt.py')
adt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adt)
tree = adt.parse((OUT / 'kernel.macho.adt').read_bytes())
chosen = dict(adt.find(tree, 'chosen').props)
product = dict(adt.find(tree, 'product').props)
profile_path = ROOT / 'sources/UniXNU-guide/profiles/os/ipados-17.7.11-21H461/profile.toml'
profile = tomllib.loads(profile_path.read_text())
fixups = chosen['text-fixups'].rstrip(b'\0').decode().split('\0')
need(fixups == profile['payload']['text_fixups'], 'Existing text fixups differ from selected OS profile')

retained = OUT / 'linked-inputs'
retained.mkdir(exist_ok=True)
receipts = {}
for directory, archive in [('boot-progress', 'libBootProgress.a'), ('venus-a660', 'libVenusA660.a'),
                           ('native-legacy-display', 'libNativeLegacyDisplay.late.a')]:
    folder = TREE / 'build' / directory
    report = load(folder / 'build-report.json')
    need(sha(folder / archive) == report['archive_sha256'], 'Archive differs from build receipt: ' + archive)
    shutil.copy2(folder / archive, retained / archive)
    shutil.copy2(folder / 'build-report.json', retained / (directory + '-report.json'))
    receipts[archive] = report['archive_sha256']
for path in [DEVICE / 'package/boot-progress/BootProgress.c', DEVICE / 'package/Adreno660/GpuPowerProbe.cpp',
             DEVICE / 'package/LegacyDisplayProbe.cpp', DEVICE / 'package/DisplayProbeStubs.c']:
    shutil.copy2(path, retained / path.name)

report = {
    'date': '2026-10-28', 'device': 'venus', 'os_profile': 'ipados-17.7.11-21H461',
    'kernel_sha256': candidate['kernel_sha256'], 'boot_sha256': candidate['boot_sha256'],
    'boot_image': str(OUT / 'phone/boot-venus-unixnu.img'), 'candidate_sha256': sha(OUT / 'candidate.json'),
    'screen_regression': screen, 'kernel_symbols': {name: hex(names[name]) for name in required},
    'trace_buffer': {'address': hex(trace_address), 'bytes': 8192, 'section': '__bss', 'cross_boot_persistence': False},
    'archives': receipts, 'qemu_report_sha256': sha(qemu_path),
    'qemu_root_checkpoint_passed': True, 'qemu_gpu_mode': 0,
    'reference_comparison': {
        'hid_original_text_sha256': hid_sha,
        'hid_text_matches_sheng': hid_sha == '7e4c5104814f2e773d5be13d092dec53ee44ba5a61a81264b229780406e86b72',
        'hid_dispatch_runtime_qualified': False,
        'profile_text_fixups_match': True, 'text_fixups_runtime_application_verified': False,
        'candidate_gamut': product['artwork-display-gamut'].rstrip(b'\0').decode(),
        'candidate_has_buttons': adt.find(tree, 'buttons') is not None,
        'candidate_has_thin_bezel': 'thin-bezel' in product,
        'dram_base': hex(int.from_bytes(chosen['dram-base'], 'little')),
        'dram_size': hex(int.from_bytes(chosen['dram-size'], 'little')),
    },
    'phone_tested': False, 'hardware_gpu_result': None, 'metal_or_desktop_verified': False,
    'superseded_photo_interpretation': 'Old row47 stage/calls zero are stale pixels, not runtime zero values.',
}
destination = DEVICE / 'evidence/a660-live-candidate.json'
destination.write_text(json.dumps(report, indent=2) + '\n')
print('PASS: source receipts, real providers, owned trace BSS, package identities and QEMU root checkpoint')
print('IOHIDFamily text matches sheng:', report['reference_comparison']['hid_text_matches_sheng'])
print('Evidence:', destination)
