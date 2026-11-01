#!/usr/bin/env python3
"""Bind the AKS candidate to its kernel link, component source and QEMU control."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('/mnt/g/UniXNU-Port')
DEVICE = ROOT / 'ports/UniXNU-venus'
WORK = Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
OUT = ROOT / 'artifacts/venus-aks-phone'
QEMU = ROOT / 'artifacts/venus-ufs-root/qemu-aks-phone/gdb-stop.json'
EXPECTED_KERNEL = '068e4ad10dfbfe5bdb233e696ddb1c0f20b745ce7c954727c437f0eba35bbc61'
EXPECTED_BOOT = '998bc56ec42e32ec7c161b0a704ee417d111ddf6886a0641fbc1a1ad9f5a989c'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def need(value, message):
    if not value:
        raise SystemExit(message)


candidate = json.loads((OUT / 'candidate.json').read_text())
kernel = OUT / 'kernel/kernel.macho'
need(sha(kernel) == candidate['kernel_sha256'] == EXPECTED_KERNEL, 'Kernel identity changed')
need(sha(OUT / 'phone/boot-venus-unixnu.img') == candidate['boot_sha256'] == EXPECTED_BOOT, 'Boot identity changed')
need(sha(WORK / 'kernel/kernel.macho') == EXPECTED_KERNEL, 'Build tree kernel differs from candidate')
args = candidate['args'].split()
for arg in ('offline-key-events=1', 'sheng-aks=1', 'sheng-build-tag=aks-001'):
    need(arg in args, 'Missing AKS argument: ' + arg)
need(candidate['owned_memory_bytes'] == 0x40000000, 'Expected 1 GiB owned memory')
need(candidate.get('key_store_state') == 'offline-key-events=1 sheng-aks=1', 'Candidate did not record AKS state')

symbols = subprocess.check_output(['/usr/bin/llvm-nm', str(kernel)], text=True)
table = {}
for line in symbols.splitlines():
    parts = line.split()
    if len(parts) == 3:
        table[parts[2]] = int(parts[0], 16)
required = ['_native_keystore_probe', '_native_aks_state_enabled', '_native_aks_lock_state', '_native_aks_call',
            '_native_aks_opened', '_native_aks_encode_state', '_native_keyevents_allocate',
            '__GLOBAL__sub_I_NativeKeyStoreEvents.cpp', '__ZN13AppleKeyStore10gMetaClassE',
            '__ZTV13AppleKeyStore', '_native_legacy_display_late_probe']
need(all(name in table for name in required), 'Kernel is missing an AKS symbol')
disassembly = subprocess.check_output(
    ['/usr/bin/llvm-objdump', '--disassemble', '--no-show-raw-insn',
     '--disassemble-symbols=_native_legacy_display_late_probe', str(kernel)], text=True)
target = table['_native_keystore_probe']
need(f'bl\t0x{target:x} <_native_keystore_probe>' in disassembly,
     'Late probe does not call the real key-store probe')
need('_native_keystore_probe' in disassembly, 'Late probe disassembly lacks the key-store call')

archive = WORK / 'tree/build/native-legacy-display/libNativeLegacyDisplay.late.a'
members = subprocess.check_output(['/usr/bin/llvm-ar', 't', str(archive)], text=True).split()
for member in ('KeyStoreProbe.o', 'NativeKeyStoreEvents.late.o'):
    need(member in members, 'Late archive lacks ' + member)
report = json.loads((WORK / 'tree/build/native-legacy-display/build-report.json').read_text())
need(report.get('key_store_state', {}).get('late_initializer') == '__GLOBAL__sub_I_NativeKeyStoreEvents.cpp',
     'Build report lacks the deferred key-store initializer')
need('native_keystore_probe' not in report.get('board_probe_stubs', []), 'Stub list still claims the key store probe')
need(report['source_sha256']['kits/venus/KeyStoreProbe.cpp'] == sha(DEVICE / 'package/KeyStoreProbe.cpp'),
     'KeyStoreProbe.cpp source changed after the build')
need(report['source_sha256']['drivers/AppleKeyStoreState/NativeKeyStoreEvents.cpp'] ==
     sha(WORK / 'tree/drivers/AppleKeyStoreState/NativeKeyStoreEvents.cpp'),
     'NativeKeyStoreEvents.cpp source changed after the build')

qemu = json.loads(QEMU.read_text())
need(sha(QEMU) == candidate['qemu_root_sha256'], 'QEMU evidence changed')
need(qemu['kernel_sha256'] == EXPECTED_KERNEL and qemu['stop_symbol'] == '_native_owner_root_accepted_checkpoint' and
     not qemu['bounded_timeout_interrupted'], 'QEMU did not reach the bounded owner-root checkpoint')
display = qemu.get('native_legacy_display') or {}
need(display.get('init_result') == 1 and display.get('start_result') == 1 and display.get('probe_match') == 1,
     'QEMU display instance did not start')

result = {
    'date': '2026-10-28', 'device': 'venus', 'os_profile': 'ipados-17.7.11-21H461',
    'kernel_sha256': EXPECTED_KERNEL, 'boot_sha256': EXPECTED_BOOT,
    'boot_image': str(OUT / 'phone/boot-venus-unixnu.img'),
    'candidate_sha256': sha(OUT / 'candidate.json'),
    'args': candidate['args'],
    'key_store_state': 'offline-key-events=1 sheng-aks=1',
    'capability': 'ephemeral/offline AppleKeyStore state and notification service; no keys, keybag, passcode or data protection',
    'kernel_symbols': {name: hex(table[name]) for name in required},
    'late_probe_calls_real_probe': True,
    'late_archive_members': members, 'late_archive_sha256': report['archive_sha256'],
    'sources': {
        'KeyStoreProbe.cpp': sha(DEVICE / 'package/KeyStoreProbe.cpp'),
        'NativeKeyStoreEvents.cpp': sha(WORK / 'tree/drivers/AppleKeyStoreState/NativeKeyStoreEvents.cpp'),
    },
    'component': {'id': 'AppleKeyStoreState', 'copy_in_build_tree': str(WORK / 'tree/drivers/AppleKeyStoreState')},
    'qemu_report_sha256': sha(QEMU), 'qemu_root_checkpoint_passed': True, 'qemu_gpu_mode': 0,
    'reference_basis': {
        'qemu_board': 'offline-key-events=1 sheng-aks=1; without it MKBEventsRegister fails, liveactivitiesd crashes, chronod waits and SpringBoard never takes the display',
        'tb128fu_board': 'the key store stand-in is required or SpringBoard waits on chronod forever; CPU-rendered iPadOS 17 home screen reached without Metal',
        'lock_screen_without_metal': ['qemu', 'tb128fu', 'negroni', 'sm-t733', 'pong', 'pandora'],
    },
    'phone_tested': False,
    'expected_observation': 'liveactivitiesd should stop crashing; chronod/SpringBoard should progress; display swaps and CPU-rendered frames may begin',
    'not_claimed': ['key storage', 'Metal', 'desktop', 'hardware result of this candidate'],
    'requires_exact_ram_boot_authorization': True,
}
destination = DEVICE / 'evidence/aks-candidate.json'
destination.write_text(json.dumps(result, indent=2) + '\n')
print('PASS: AKS symbols, real late-probe call, archive members, sources and QEMU root/display control')
print('Candidate:', OUT / 'phone/boot-venus-unixnu.img')
print('Evidence:', destination)
