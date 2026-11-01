#!/usr/bin/env python3
"""Build paired entry-stage probe images for the official bring-up stage 5.

Each image answers exactly one question by timing the reset:
  entry     blue bar only; reset 8s after kernel entry with the MMU still off
  after-mmu reset 8s after the MMU is enabled (magenta path already taken)
The two delays differ from the plain kernel's own behaviour, so a reset at the
expected time proves the code at that site executed.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path('/root/unixnu-build')
PROJECT = Path('/mnt/g/UniXNU-Port')
DEVICE = PROJECT / 'ports/UniXNU-venus'
OUT = ROOT / 'venus-ios26-probe'
PROBE = ROOT / 'venus-xnu26-platform/tree/scripts/patch-zeta-kernel-probe.py'
PLAIN = ROOT / 'venus-ios26-plain-001/kernel.macho'
BASE = ROOT / 'venus-ios26-phone-v3'
FD_SOURCE = PROJECT / 'artifacts/venus-metal-touch-040/phone/SILICIUM_UEFI.fd'
TRUST = ROOT / 'venus-ios26-trustcache.bundle'
DATA = ROOT / 'venus-ios26-data.dbr'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command):
    result = subprocess.run([str(v) for v in command], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f'command failed: {command}\n{result.stdout}{result.stderr}')
    return result.stdout


def main():
    parser_stage = [('entry', 'entry'), ('after-mmu', 'after-mmu')]
    OUT.mkdir(exist_ok=True)
    report = {'plain_kernel': dict(path=str(PLAIN), sha256=sha(PLAIN)),
              'probe_script_sha256': sha(PROBE), 'stages': {}, 'phone_operations': False}
    for stage, label in parser_stage:
        work = OUT / label
        work.mkdir(exist_ok=True)
        patched = work / 'kernel.macho'
        if patched.exists():
            raise SystemExit(f'{patched} exists; preserve it')
        out = run([sys.executable, PROBE, PLAIN, '--output', patched,
                   '--stage', stage, '--reset-delay', '8'])
        probe = json.loads(out[out.index('{'):]) if '{' in out else {}
        payload = work / 'payload.img'
        run(['mkfs.vfat', '-n', 'VENUSXNU', '-C', payload, str(160 * 1024)])
        for relative in ('EFI', 'EFI/UniXNU', 'EFI/UniXNU/Payloads'):
            run(['mmd', '-i', payload, '::/' + relative])
        # Reuse the corrected ADT and configuration from the v3 candidate.
        adt = BASE / 'kernel.macho.adt'
        config = BASE / 'unixnu.toml'
        for name, source in (('kernel.macho', patched), ('kernel.macho.adt', adt),
                             ('kernel.macho.trustcache', TRUST), ('scratch-data.img', DATA),
                             ('unixnu.toml', config)):
            target = '::/EFI/UniXNU/Payloads/' + name if name != 'unixnu.toml' else '::/EFI/UniXNU/unixnu.toml'
            run(['mcopy', '-o', '-i', payload, source, target])
        artifacts = work / 'uefi-input'
        artifacts.mkdir()
        shutil.copyfile(FD_SOURCE, artifacts / 'SILICIUM_UEFI.fd')
        for name in ('UniXNU.efi', 'UniXNUDxe.efi', 'DarwinBoot.efi'):
            shutil.copyfile(FD_SOURCE.parent / name, artifacts / name)
        run([sys.executable, PROJECT / 'tools/package-venus-uefi.py', '--tree', PROJECT / 'ports/uefi-venus',
             '--workspace', PROJECT, '--artifacts', artifacts, '--payload', payload])
        image = artifacts / 'boot-venus-unixnu.img'
        report['stages'][label] = dict(stage=stage, image=str(image), image_sha256=sha(image),
                                       patched_kernel_sha256=sha(patched),
                                       reset_delay_seconds=8,
                                       probe=probe, adt_sha256=sha(adt))
        print(f'{label}: {sha(image)}')
    (OUT / 'probe-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['stages'], indent=2))


if __name__ == '__main__':
    main()
