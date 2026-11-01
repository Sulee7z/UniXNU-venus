#!/usr/bin/env python3
"""Export the tested fault-screen build, replace one payload file, and check root in QEMU."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

ROOT = Path('/mnt/g/UniXNU-Port')
DEVICE = ROOT / 'ports/UniXNU-venus'
WORK = Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
CONTROL = ROOT / 'artifacts/venus-legacy/full-phone'
OUT = ROOT / 'artifacts/venus-exit-fault'
SOURCE = DEVICE / 'package/boot-progress'
KERNEL_SHA = 'f103ee3b85f4eaa482ca18102e7e65b069d183621a6ff91c73096fa8f10f4a83'
CONTROL_SHA = '28051b5a09fc7ff875d11202cd179173a0b30f40272a765937e92d0eb0d037f0'


def need(condition, message):
    if not condition:
        raise SystemExit(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text())


def fat(image, path):
    return subprocess.check_output(['mtype', '-i', str(image), '::/' + path], timeout=60)


def windows(path):
    return str(path).replace('/mnt/g/', 'G:/', 1)


need(not (OUT / 'candidate.json').exists(), 'Completed candidate already exists; preserve its identity')
need(sha(CONTROL / 'boot-venus-unixnu.img') == CONTROL_SHA, 'Phone control image changed')
control = load(CONTROL / 'verification.json')
need(sha(CONTROL / 'payload.img') == control['ramdisk_sha256'], 'Phone control payload changed')
need(sha(WORK / 'kernel/kernel.macho') == KERNEL_SHA, 'Unexpected newly built kernel')
build_report_path = WORK / 'tree/build/boot-progress/build-report.json'
build_report = load(build_report_path)
checks_path = ROOT / 'artifacts/venus-exit-fault-checks/report.json'
checks = load(checks_path)
need(checks['passed'], 'Fault-screen sanitizer checks did not pass')
for name, expected in checks['sources'].items():
    need(sha(SOURCE / name) == expected == build_report['sources'][name],
         'Tested, compiled and current source differ: ' + name)
need(sha(WORK / 'tree/build/boot-progress/libBootProgress.a') == build_report['archive_sha256'],
     'Compiled BootProgress archive changed')
data = (WORK / 'kernel/kernel.macho').read_bytes()
need(b'CRASH %u/4 ' in data and b'sig%u src=%s PC' in data, 'New formatters absent from final kernel')
sys.path.insert(0, str(WORK / 'tree/kits/XnuPrelink'))
from native_prelink import macho, backed_offset
image = macho(data)
symbols = subprocess.check_output(['/usr/bin/llvm-nm', str(WORK / 'kernel/kernel.macho')], text=True)
addresses = {}
for symbol in ['_boot_progress_user_breakpoint', '_boot_progress_user_abort',
               '_boot_progress_exit_fault', '_boot_progress_exit',
               '_native_owner_root_accepted_checkpoint']:
    # llvm-nm calls __TEXT_EXEC symbols S, so verify their actual Mach-O segment
    # permissions and __text extent instead of treating the display letter as ABI.
    found = re.findall(r'^([0-9a-fA-F]+)\s+([TtSs])\s+' + re.escape(symbol) + r'$', symbols, re.M)
    need(len(found) == 1 and int(found[0][0], 16) != 0, 'Missing executable diagnostic/root symbol: ' + symbol)
    address = int(found[0][0], 16)
    need(any(segment['initprot'] & 4 and any(
        section['name'] == '__text' and section['va'] <= address and address + 4 <= section['va'] + section['size']
        for section in segment['sections']) for segment in image['segments']),
        'Diagnostic/root symbol is not in executable text: ' + symbol)
    backed_offset(image['segments'], address, 4, len(data))
    addresses[symbol] = '0x' + found[0][0]

kernel, phone = OUT / 'kernel', OUT / 'phone'
kernel.mkdir(parents=True, exist_ok=True)
phone.mkdir(exist_ok=True)
for name in ['kernel.macho', 'kernel.json']:
    shutil.copy2(WORK / 'kernel' / name, kernel / name)
shutil.copy2(build_report_path, kernel / 'boot-progress-build-report.json')
shutil.copy2(WORK / 'tree/build/boot-progress/libBootProgress.a', kernel / 'libBootProgress.a')
shutil.copy2(checks_path, OUT / 'host-checks.json')
shutil.copytree(SOURCE, OUT / 'sources', dirs_exist_ok=True)
shutil.copy2(WORK / '.config', OUT / 'kernel.config')
shutil.copy2(CONTROL / 'payload.img', phone / 'payload.img')
for name in ['SILICIUM_UEFI.fd', 'UniXNU.efi', 'UniXNUDxe.efi', 'DarwinBoot.efi']:
    shutil.copy2(CONTROL / name, phone / name)
subprocess.run(['mcopy', '-o', '-i', str(phone / 'payload.img'), str(kernel / 'kernel.macho'),
                '::/EFI/UniXNU/Payloads/kernel.macho'], check=True, timeout=120)
need(hashlib.sha256(fat(phone / 'payload.img', 'EFI/UniXNU/Payloads/kernel.macho')).hexdigest() == KERNEL_SHA,
     'Payload kernel does not match exported kernel')
unchanged = {}
for name in ['EFI/UniXNU/unixnu.toml', 'EFI/UniXNU/Payloads/kernel.macho.adt',
             'EFI/UniXNU/Payloads/scratch-data.img', 'EFI/UniXNU/Payloads/kernel.macho.trustcache']:
    before, after = fat(CONTROL / 'payload.img', name), fat(phone / 'payload.img', name)
    need(before == after, 'Unexpected payload input change: ' + name)
    unchanged[name] = {'bytes': len(after), 'sha256': hashlib.sha256(after).hexdigest()}
    if name.endswith('.adt'):
        marker = b'darwinboot-memory-size'.ljust(32, b'\0')
        need(after.count(marker) == 1, 'Ambiguous owned-memory property')
        at = after.index(marker) + 32
        need(struct.unpack_from('<IQ', after, at) == (8, 0x40000000), 'Candidate is not a 1 GiB payload')
        (phone / 'kernel.macho.adt').write_bytes(after)
    if name.endswith('.toml'):
        need(b'boot-progress=2' in after and b'native-ufs-root=1' in after, 'Root/diagnostic arguments missing')
        (phone / 'unixnu.toml').write_bytes(after)
subprocess.run(['python3', ROOT / 'tools/package-venus-uefi.py',
                '--tree', ROOT / 'ports/uefi-venus', '--workspace', ROOT,
                '--artifacts', phone, '--payload', phone / 'payload.img'], check=True, timeout=180)
verification = load(phone / 'verification.json')
need(verification['fd_sha256'] == control['fd_sha256'] and verification['efi'] == control['efi'],
     'Firmware/loader identities changed')
need(verification['roundtrip_verified'] and not verification['uefi_memory_conflicts'], 'Container checks failed')
need(sha(phone / 'boot-venus-unixnu.img') == verification['sha256'], 'Boot image identity mismatch')
need(sha(CONTROL / 'boot-venus-unixnu.img') == CONTROL_SHA, 'Control image was modified')

# The simulation uses read-only OS/SystemOS images and synthetic QEMU hardware;
# it tests the exact new kernel, not physical UFS, phone ADT or a desktop.
qemu_name = 'qemu-exit-fault-1g'
subprocess.run(['python3', DEVICE / 'scripts/test-venus-root-mount.py',
                '--kernel', kernel / 'kernel.macho', '--prelink-report', kernel / 'kernel.json',
                '--owned-memory-size', '0x40000000', '--qemu-memory-mib', '2048',
                '--inspect-memory-budget', '--out-name', qemu_name,
                '--extra-kernel-arg', 'boot-progress=2'], check=True, timeout=360)
qemu_path = ROOT / 'artifacts/venus-ufs-root' / qemu_name / 'gdb-stop.json'
qemu = load(qemu_path)
need(qemu['kernel_sha256'] == KERNEL_SHA and not qemu['bounded_timeout_interrupted'] and
     qemu['stop_symbol'] == '_native_owner_root_accepted_checkpoint', 'Actual root checkpoint not reached')
report = {
    'device': 'venus', 'serial': '55870427',
    'base_commit': '8d157ee18ae9c4d518aba28cb3040a84e860dcd1',
    'base_has_local_changes': True, 'defconfig': 'venus_ufs_root_defconfig',
    'control_boot_sha256': CONTROL_SHA,
    'kernel_sha256': KERNEL_SHA,
    'kernel_bytes': (kernel / 'kernel.macho').stat().st_size,
    'boot_image': windows(phone / 'boot-venus-unixnu.img'),
    'boot_sha256': verification['sha256'], 'boot_bytes': verification['bytes'],
    'payload_sha256': sha(phone / 'payload.img'),
    'owned_memory_bytes': 0x40000000, 'owned_memory_mib': 1024,
    'unchanged_payload_files': unchanged,
    'fd_sha256': verification['fd_sha256'],
    'compiled_source_sha256': checks['sources'], 'executable_symbols': addresses,
    'host_checks': windows(OUT / 'host-checks.json'),
    'qemu_root_report': windows(qemu_path), 'qemu_root_report_sha256': sha(qemu_path),
    'qemu_root_checkpoint_reached': True,
    'scope': 'Ordinary BootProgress rows 12-15 show the latest retained crash, with EL0/EXIT context, registers, cache slide and bounded backtrace. No display/GPU backend added.',
    'phone_tested': False, 'requires_exact_ram_boot_authorization': True,
    'partition_flash_or_android_erase_included': False,
    'runtime_existing_unixnu_data_writes_possible': True,
    'limits': ['Host API/pixel substitutes are not phone tests',
               'QEMU uses synthetic hardware/read-only host disks and stops before full userspace',
               'Exception records can be overwritten; EXIT registers need not be the faulting thread',
               'This adds observability, not a SpringBoard crash fix'],
}
(OUT / 'candidate.json').write_text(json.dumps(report, indent=2) + '\n')
os.sync()
print(json.dumps(report, indent=2))
