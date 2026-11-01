#!/usr/bin/env python3
"""Package the A660-enabled Venus kernel with Mi 11 GPU firmware in the ADT."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

ROOT = Path('/mnt/g/UniXNU-Port')
WORK = Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
CONTROL = ROOT / 'artifacts/venus-legacy/full-phone'
OUT = ROOT / 'artifacts/venus-a660-delay-phone'
KERNEL_SHA = 'df6864eb893ceb2586734a56fda7b96a87175d2f41d18b0ffc76af5e311543b1'
CONTROL_SHA = '28051b5a09fc7ff875d11202cd179173a0b30f40272a765937e92d0eb0d037f0'
ARGS = ('-v serial=3 cpus=1 debug=0x14e -no_slto_panic sheng-pmgr=2 native-ufs-root=1 '
        'native-ufs-probe=0 sheng-data-persist=2 offline-apfs-load=1 -apfs_shared_datavolume '
        'boot-progress=2 offline-legacy-register=1 offline-legacy-gop=1 offline-legacy-unit-scale=2 '
        'offline-legacy-pm=1 offline-legacy-validate=1 offline-legacy-transfer=1 '
        'offline-legacy-cpu-present=1 offline-legacy-phase=4 offline-mobile-graphics-client=1 '
        'offline-mobile-graphics-load=1 sheng-vsync=120 sheng-fb-gpu=0 sheng-early-retire=1 '
        'sheng-backlight=0 sheng-dpu=0 sheng-touch=0 sheng-gpu-power=9 sheng-gpu-metal=0 '
        'zeta-gpu-publish=1 zeta-gpu-metal=1 zeta-gpu-zap=1 '
        'sheng-banner=0 sheng-lite=1')


def need(value, message):
    if not value:
        raise SystemExit(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text())


def fat(image, name):
    return subprocess.check_output(['mtype', '-i', str(image), '::/' + name], timeout=60)


need(not (OUT / 'candidate.json').exists(), 'A660 candidate record already exists')
need(sha(CONTROL / 'boot-venus-unixnu.img') == CONTROL_SHA, 'Phone control changed')
control = load(CONTROL / 'verification.json')
need(sha(CONTROL / 'payload.img') == control['ramdisk_sha256'], 'Control payload changed')
need(sha(WORK / 'kernel/kernel.macho') == KERNEL_SHA, 'A660 kernel changed')
OUT.mkdir(parents=True, exist_ok=True)
kernel = OUT / 'kernel'
phone = OUT / 'phone'
kernel.mkdir(exist_ok=True)
phone.mkdir(exist_ok=True)
shutil.copy2(WORK / 'kernel/kernel.macho', kernel / 'kernel.macho')
shutil.copy2(WORK / 'kernel/kernel.json', kernel / 'kernel.json')
shutil.copy2(CONTROL / 'payload.img', phone / 'payload.img')
for name in ['SILICIUM_UEFI.fd', 'UniXNU.efi', 'UniXNUX.efi', 'UniXNUDxe.efi', 'DarwinBoot.efi']:
    source = CONTROL / name
    if not source.exists() and name == 'UniXNUX.efi':
        continue
    shutil.copy2(source, phone / name)
control_adt = OUT / 'control-kernel.macho.adt'
control_adt.write_bytes(fat(CONTROL / 'payload.img', 'EFI/UniXNU/Payloads/kernel.macho.adt'))
injection = OUT / 'a660-adt-injection.json'
subprocess.run(['python3', ROOT / 'ports/UniXNU-venus/scripts/inject-a660-firmware-adt.py',
                '--adt', control_adt, '--output', OUT / 'kernel.macho.adt'], check=True, timeout=120)
subprocess.run(['mcopy', '-o', '-i', str(phone / 'payload.img'), str(kernel / 'kernel.macho'),
                '::/EFI/UniXNU/Payloads/kernel.macho'], check=True, timeout=120)
subprocess.run(['mcopy', '-o', '-i', str(phone / 'payload.img'), str(OUT / 'kernel.macho.adt'),
                '::/EFI/UniXNU/Payloads/kernel.macho.adt'], check=True, timeout=120)
need(hashlib.sha256(fat(phone / 'payload.img', 'EFI/UniXNU/Payloads/kernel.macho')).hexdigest() == KERNEL_SHA,
     'Payload kernel does not match the A660 kernel')
need(hashlib.sha256(fat(phone / 'payload.img', 'EFI/UniXNU/Payloads/kernel.macho.adt')).hexdigest() == sha(OUT / 'kernel.macho.adt'),
     'Payload ADT does not match the injected ADT')
toml = f'''version = 1
[boot]
timeout = 5
default = "xnu"
[kits]
autoload = false
[[entry]]
id = "xnu"
title = "Mi 11 XNU platform bring-up"
type = "xnu"
path = "Payloads/kernel.macho"
initrd = "Payloads/scratch-data.img"
args = "{ARGS}"
[[entry]]
id = "reset"
title = "Restart"
type = "action"
action = "reset"
[[entry]]
id = "shutdown"
title = "Power off"
type = "action"
action = "shutdown"
[[entry]]
id = "tools"
title = "Tools"
type = "action"
action = "tools"
'''
(phone / 'unixnu.toml').write_text(toml)
subprocess.run(['mcopy', '-o', '-i', str(phone / 'payload.img'), str(phone / 'unixnu.toml'),
                '::/EFI/UniXNU/unixnu.toml'], check=True, timeout=120)
unchanged = {}
for name in ['EFI/UniXNU/Payloads/scratch-data.img', 'EFI/UniXNU/Payloads/kernel.macho.trustcache']:
    before, after = fat(CONTROL / 'payload.img', name), fat(phone / 'payload.img', name)
    need(before == after, 'Unexpected payload input change: ' + name)
    unchanged[name] = {'bytes': len(after), 'sha256': hashlib.sha256(after).hexdigest()}
    if name.endswith('.trustcache'):
        (phone / 'kernel.macho.trustcache').write_bytes(after)
need(struct.unpack_from('<IQ', fat(phone / 'payload.img', 'EFI/UniXNU/Payloads/kernel.macho.adt'),
                        fat(phone / 'payload.img', 'EFI/UniXNU/Payloads/kernel.macho.adt').index(
                            b'darwinboot-memory-size'.ljust(32, b'\0')) + 32) == (8, 0x40000000),
     'A660 candidate is not 1 GiB')
subprocess.run(['python3', ROOT / 'tools/package-venus-uefi.py', '--tree', ROOT / 'ports/uefi-venus',
                '--workspace', ROOT, '--artifacts', phone, '--payload', phone / 'payload.img'],
               check=True, timeout=180)
verification = load(phone / 'verification.json')
need(verification['fd_sha256'] == control['fd_sha256'] and verification['efi'] == control['efi'],
     'Firmware/loader identities changed')
need(verification['roundtrip_verified'] and not verification['uefi_memory_conflicts'], 'Container checks failed')
need(sha(phone / 'boot-venus-unixnu.img') == verification['sha256'], 'Boot image identity mismatch')
# QEMU root control with the A660 kernel, but the hardware probe disabled: QEMU has no A660.
subprocess.run(['python3', ROOT / 'ports/UniXNU-venus/scripts/test-venus-root-mount.py',
                '--kernel', kernel / 'kernel.macho', '--prelink-report', kernel / 'kernel.json',
                '--owned-memory-size', '0x40000000', '--qemu-memory-mib', '2048',
                '--inspect-memory-budget', '--out-name', 'qemu-a660-delay-phone',
                '--extra-kernel-arg', 'boot-progress=2', '--extra-kernel-arg', 'sheng-gpu-power=0',
                '--extra-kernel-arg', 'offline-legacy-register=1', '--extra-kernel-arg', 'offline-legacy-gop=1',
                '--extra-kernel-arg', 'offline-legacy-unit-scale=2', '--extra-kernel-arg', 'offline-legacy-pm=1',
                '--extra-kernel-arg', 'offline-legacy-validate=1', '--extra-kernel-arg', 'offline-legacy-transfer=1',
                '--extra-kernel-arg', 'offline-legacy-cpu-present=1', '--extra-kernel-arg', 'offline-legacy-phase=4',
                '--extra-kernel-arg', 'offline-mobile-graphics-client=1',
                '--extra-kernel-arg', 'offline-mobile-graphics-load=1', '--extra-kernel-arg', 'sheng-vsync=120',
                '--extra-kernel-arg', 'sheng-fb-gpu=0'], check=True, timeout=600)
qemu = load(ROOT / 'artifacts/venus-ufs-root/qemu-a660-delay-phone/gdb-stop.json')
need(qemu['kernel_sha256'] == KERNEL_SHA and not qemu['bounded_timeout_interrupted'] and
     qemu['stop_symbol'] == '_native_owner_root_accepted_checkpoint', 'A660 QEMU root checkpoint failed')
display = qemu.get('native_legacy_display') or {}
need(display.get('init_result') == 1 and display.get('start_result') == 1 and display.get('probe_match') == 1,
     'Display instance did not initialize/start in QEMU')
report = {
    'device': 'venus', 'serial': '55870427',
    'base_commit': '8d157ee18ae9c4d518aba28cb3040a84e860dcd1',
    'kernel_sha256': KERNEL_SHA,
    'boot_image': str(phone / 'boot-venus-unixnu.img'),
    'boot_sha256': verification['sha256'], 'boot_bytes': verification['bytes'],
    'payload_sha256': sha(phone / 'payload.img'),
    'a660_adt': {'file': str(OUT / 'kernel.macho.adt'), 'sha256': sha(OUT / 'kernel.macho.adt'),
                 'bytes': (OUT / 'kernel.macho.adt').stat().st_size},
    'owned_memory_bytes': 0x40000000, 'owned_memory_mib': 1024,
    'args': ARGS, 'unchanged_payload_files': unchanged,
    'fd_sha256': verification['fd_sha256'], 'efi': verification['efi'],
    'qemu_root': 'G:/UniXNU-Port/artifacts/venus-ufs-root/qemu-a660-delay-phone/gdb-stop.json',
    'qemu_root_sha256': sha(ROOT / 'artifacts/venus-ufs-root/qemu-a660-delay-phone/gdb-stop.json'),
    'display_runtime': display,
    'phone_tested': False,
    'requires_exact_ram_boot_authorization': True,
    'partition_flash_or_android_erase_included': False,
    'scope': 'A660 kernel with Mi 11 GMU/SQE/ZAP firmware in /chosen; QEMU root/display control with GPU probe disabled; real A660 run is phone-only.',
}
(OUT / 'candidate.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
