#!/usr/bin/env python3
"""Assemble the Venus iOS26 RAM-boot candidate: ADT, payload FAT and boot image."""
import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path('/root/unixnu-build')
PROJECT = Path('/mnt/g/UniXNU-Port')
DEVICE = PROJECT / 'ports/UniXNU-venus'
OUT = ROOT / 'venus-ios26-phone-v4'
ADT_TOOL = ROOT / 'venus-xnu26-platform/tree/scripts/make-zeta-adt.py'
ADT_FIX = DEVICE / 'scripts/fix-venus-ios26-adt.py'
KERNEL = ROOT / 'venus-ios26-prelink-root-v5/kernel.macho'
TRUST = ROOT / 'venus-ios26-trustcache.bundle'
DATA = ROOT / 'venus-ios26-data.dbr'
FD_SOURCE = PROJECT / 'artifacts/venus-metal-touch-040/phone/SILICIUM_UEFI.fd'
CHIP = 0x1BACB3B1A9B58B23
CHIP_ID = 0x8350
OS_VOLUME = 'B6C635B2-67F6-4034-B5D5-539E4D03D1EC'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command, **kwargs):
    print('RUN', ' '.join(map(str, command)), flush=True)
    result = subprocess.run([str(v) for v in command], **kwargs)
    if result.returncode:
        raise RuntimeError(f'command failed: {command}')
    return result


def main():
    if OUT.exists():
        raise SystemExit(f'{OUT} exists; preserve the candidate')
    OUT.mkdir()
    report = dict(result='preparing', phone_operations=False)
    generated = OUT / 'kernel.macho.generated.adt'
    adt = OUT / 'kernel.macho.adt'
    run([sys.executable, ADT_TOOL, '--output', str(generated), '--dram-size', '0x200000000',
         '--owned-memory-size', '0x40000000', '--unique-chip-id', f'{CHIP:x}', '--chip-id', f'{CHIP_ID:x}',
         '--packed-data-ramdisk', '--persistent-data', '--trust-cache', '--csr-config', '0x2',
         '--root-match-volume-uuid', OS_VOLUME])
    # The generator emits Surface Duo 2 defaults. Rewrite the hardware
    # description to the phone-measured Venus layout before packaging.
    run([sys.executable, ADT_FIX, '--input', str(generated), '--output', str(adt),
         '--report', str(OUT / 'adt-fix.json')])
    payload = OUT / 'payload.img'
    run(['mkfs.vfat', '-n', 'VENUSXNU', '-C', str(payload), str(160 * 1024)])
    for relative in ('EFI', 'EFI/UniXNU', 'EFI/UniXNU/Payloads'):
        run(['mmd', '-i', str(payload), '::/' + relative])
    staged = [('kernel.macho', KERNEL), ('kernel.macho.adt', adt),
              ('kernel.macho.trustcache', TRUST), ('scratch-data.img', DATA)]
    for name, source in staged:
        run(['mcopy', '-o', '-i', str(payload), str(source), '::/EFI/UniXNU/Payloads/' + name])
    # Start from the board's phone-tested arguments instead of an invented
    # list, then drop only those that need components this kernel does not
    # build (legacy GOP display, the iPad profile's HID/AKS probes).
    board = tomllib.loads((DEVICE / 'board.toml').read_text())
    dropped_prefixes = ('offline-legacy-', 'offline-mobile-graphics-', 'offline-key-events',
                        'sheng-vsync', 'sheng-fb-gpu', 'sheng-early-retire', 'sheng-backlight',
                        'sheng-dpu', 'sheng-touch', 'sheng-gpu-power', 'sheng-gpu-metal',
                        'sheng-banner', 'sheng-lite', 'sheng-aks', 'offline-hid-',
                        'venus-st-', 'sheng-touch-hid', 'venus-st-custom-hid',
                        'zeta-gpu-metal', 'sheng-gpu-addon', 'native-dwc3-console')
    args = [value for value in board['payload']['kernel_args']
            if not value.startswith(dropped_prefixes)]
    for required in ('dyld_flags=0x8', 'offline-apfs-load=1'):
        if required not in args:
            args.append(required)
    # One boot CPU until multi-core startup is separately qualified.
    args = [value for value in args if not value.startswith('cpus=')]
    args.append('cpus=1')
    kernel_args = ' '.join(args)
    config = OUT / 'unixnu.toml'
    config.write_text('''version = 1
[boot]
timeout = 5
default = "xnu"
[kits]
autoload = false
[[entry]]
id = "xnu"
title = "Venus iOS 26.5.2 native boot"
type = "xnu"
path = "Payloads/kernel.macho"
initrd = "Payloads/scratch-data.img"
args = "''' + kernel_args + '''"
''')
    report['kernel_args'] = kernel_args
    report['args_from_board'] = True
    run(['mcopy', '-o', '-i', str(payload), str(config), '::/EFI/UniXNU/unixnu.toml'])
    run(['mtype', '-i', str(payload), '::/EFI/UniXNU/Payloads/kernel.macho'], stdout=subprocess.DEVNULL)
    artifacts = OUT / 'uefi-input'
    artifacts.mkdir()
    import shutil
    shutil.copyfile(FD_SOURCE, artifacts / 'SILICIUM_UEFI.fd')
    # The EFI application/driver pair must match the firmware volume that was
    # actually RAM-booted on this phone; reuse that validated set verbatim.
    for name in ('UniXNU.efi', 'UniXNUDxe.efi', 'DarwinBoot.efi'):
        shutil.copyfile(FD_SOURCE.parent / name, artifacts / name)
    run([sys.executable, PROJECT / 'tools/package-venus-uefi.py', '--tree', PROJECT / 'ports/uefi-venus',
         '--workspace', PROJECT, '--artifacts', artifacts, '--payload', payload])
    image = artifacts / 'boot-venus-unixnu.img'
    if not image.exists():
        raise RuntimeError('No boot image produced')
    shutil.copyfile(image, OUT / 'boot-venus-unixnu.img')
    verification = json.loads((artifacts / 'verification.json').read_text())
    report.update(result='candidate-assembled', image=str(OUT / 'boot-venus-unixnu.img'),
                  image_sha256=sha(OUT / 'boot-venus-unixnu.img'), image_bytes=(OUT / 'boot-venus-unixnu.img').stat().st_size,
                  payload_sha256=sha(payload), adt_sha256=sha(adt), kernel_sha256=sha(KERNEL),
                  trust_sha256=sha(TRUST), data_sha256=sha(DATA),
                  firmware_sha256=verification['fd_sha256'], roundtrip_verified=verification['roundtrip_verified'],
                  uefi_memory_conflicts=verification['uefi_memory_conflicts'],
                  volume_uuid=OS_VOLUME, unique_chip_id=f'{CHIP:x}', phone_tested=False)
    (OUT / 'candidate.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
