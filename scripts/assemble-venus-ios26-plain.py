#!/usr/bin/env python3
"""Assemble an isolatation boot image that uses the non-prelinked kernel.

Purpose: separate "the plain kernel cannot start" from "the experimental
prelink is wrong". This does not change kernel or prelink sources.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path('/root/unixnu-build')
PROJECT = Path('/mnt/g/UniXNU-Port')
OUT = ROOT / 'venus-ios26-plain-001'
ADT_TOOL = ROOT / 'venus-xnu26-platform/tree/scripts/make-zeta-adt.py'
KERNEL = OUT / 'kernel.macho'
TRUST = ROOT / 'venus-ios26-trustcache.bundle'
DATA = ROOT / 'venus-ios26-data.dbr'
FD_SOURCE = PROJECT / 'artifacts/venus-metal-touch-040/phone/SILICIUM_UEFI.fd'
CHIP = 0x1BACB3B1A9B58B23
CHIP_ID = 0x8350
OS_VOLUME = 'B6C635B2-67F6-4034-B5D5-539E4D03D1EC'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command):
    print('RUN', ' '.join(map(str, command)), flush=True)
    result = subprocess.run([str(v) for v in command])
    if result.returncode:
        raise RuntimeError(f'command failed: {command}')
    return result


def main():
    adt = OUT / 'kernel.macho.adt'
    run([sys.executable, ADT_TOOL, '--output', str(adt), '--dram-size', '0x200000000',
         '--owned-memory-size', '0x40000000', '--unique-chip-id', f'{CHIP:x}', '--chip-id', f'{CHIP_ID:x}',
         '--packed-data-ramdisk', '--persistent-data', '--trust-cache', '--csr-config', '0x2',
         '--root-match-volume-uuid', OS_VOLUME])
    payload = OUT / 'payload.img'
    run(['mkfs.vfat', '-n', 'VENUSXNU', '-C', str(payload), str(160 * 1024)])
    for relative in ('EFI', 'EFI/UniXNU', 'EFI/UniXNU/Payloads'):
        run(['mmd', '-i', str(payload), '::/' + relative])
    for name, source in (('kernel.macho', KERNEL), ('kernel.macho.adt', adt),
                         ('kernel.macho.trustcache', TRUST), ('scratch-data.img', DATA)):
        run(['mcopy', '-o', '-i', str(payload), str(source), '::/EFI/UniXNU/Payloads/' + name])
    config = OUT / 'unixnu.toml'
    config.write_text('''version = 1
[boot]
timeout = 5
default = "xnu"
[kits]
autoload = false
[[entry]]
id = "xnu"
title = "Venus iOS26 plain kernel isolation"
type = "xnu"
path = "Payloads/kernel.macho"
initrd = "Payloads/scratch-data.img"
args = "-v serial=3 debug=0x14e -no_slto_panic cpus=1 kt_fixed_zones=120 offline-apfs-load=1 native-ufs-root=1 native-ufs-probe=0"
''')
    run(['mcopy', '-o', '-i', str(payload), str(config), '::/EFI/UniXNU/unixnu.toml'])
    artifacts = OUT / 'uefi-input'
    artifacts.mkdir()
    shutil.copyfile(FD_SOURCE, artifacts / 'SILICIUM_UEFI.fd')
    for name in ('UniXNU.efi', 'UniXNUDxe.efi', 'DarwinBoot.efi'):
        shutil.copyfile(FD_SOURCE.parent / name, artifacts / name)
    run([sys.executable, PROJECT / 'tools/package-venus-uefi.py', '--tree', PROJECT / 'ports/uefi-venus',
         '--workspace', PROJECT, '--artifacts', artifacts, '--payload', payload])
    image = artifacts / 'boot-venus-unixnu.img'
    report = dict(result='plain-kernel-isolation-assembled', image=str(image),
                  image_sha256=sha(image), image_bytes=image.stat().st_size,
                  kernel_sha256=sha(KERNEL), prelinked=False,
                  adt_sha256=sha(adt), data_sha256=sha(DATA), trust_sha256=sha(TRUST),
                  note='One-CPU single-core isolation run to see whether the plain kernel reaches its console before any prelink involvement.',
                  phone_tested=False)
    (OUT / 'candidate.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
