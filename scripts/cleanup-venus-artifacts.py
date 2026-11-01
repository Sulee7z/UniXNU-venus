#!/usr/bin/env python3
"""Inventory artifacts and apply an explicit cleanup plan after checking the retained boot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

PROJECT = Path('/mnt/g/UniXNU-Port')
ARTIFACTS = PROJECT / 'artifacts'
EVIDENCE = PROJECT / 'ports/UniXNU-venus/evidence'
BOOT = ARTIFACTS / 'venus-metal-touch-040/phone/boot-venus-unixnu.img'
BOOT_SHA = '8cd2d96b12e6e9ffa014689158d8e32f5ce14c1002c1fb477dbfe3b2713dba19'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory():
    sizes = {}
    for current, dirs, names in os.walk(ARTIFACTS, followlinks=False):
        for name in names:
            path = Path(current) / name
            if path.is_symlink():
                continue
            relative = path.relative_to(ARTIFACTS)
            info = path.stat()
            for depth in (1, 2, 3):
                if len(relative.parts) <= depth:
                    continue
                key = '/'.join(relative.parts[:depth])
                row = sizes.setdefault(key, dict(bytes=0, files=0))
                row['bytes'] += info.st_size
                row['files'] += 1
    report = dict(free_bytes=shutil.disk_usage(ARTIFACTS).free,
                  sizes=dict(sorted(sizes.items(), key=lambda item: item[1]['bytes'], reverse=True)))
    (EVIDENCE / 'artifacts-inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    for key, row in report['sizes'].items():
        if key.count('/') <= 1 and row['bytes'] >= 16 << 20:
            print(f'{row["bytes"] / (1 << 30):8.3f} GiB  {key}  ({row["files"]} files)')
    print(f'Free: {report["free_bytes"] / (1 << 30):.2f} GiB')


def apply(plan_path):
    plan = json.loads(plan_path.read_text())
    if plan.get('authorization') != 'User authorized unused artifacts cleanup; retain last bootable build and active system images.':
        raise RuntimeError('Missing cleanup authorization context')
    if sha(BOOT) != BOOT_SHA:
        raise RuntimeError('Retained last RAM-booted040 image does not match its receipt')
    retained = [ARTIFACTS / value for value in plan['retain']]
    for path in retained:
        if not path.exists():
            raise RuntimeError(f'Retained path missing: {path}')
    values = list(plan['delete'])
    for value in plan.get('prune_children', []):
        parent = ARTIFACTS / value
        if parent.is_symlink() or not parent.resolve().is_relative_to(ARTIFACTS.resolve()):
            raise RuntimeError('Prune parent must stay in artifacts')
        for child in parent.iterdir():
            if any(child == keep or child in keep.parents or keep in child.parents for keep in retained):
                continue
            values.append(str(child.relative_to(ARTIFACTS)))
    delete = []
    for value in values:
        relative = Path(value)
        if relative.is_absolute() or '..' in relative.parts:
            raise RuntimeError('Cleanup path must be artifact-relative')
        path = ARTIFACTS / relative
        if any(path == keep or path in keep.parents or keep in path.parents for keep in retained):
            raise RuntimeError(f'Cleanup intersects retained input: {value}')
        if path.is_symlink() or not path.resolve().is_relative_to(ARTIFACTS.resolve()):
            raise RuntimeError(f'Cleanup cannot traverse an external link: {value}')
        if path.exists():
            delete.append(path)
    receipt = dict(authorization=plan['authorization'], plan_sha256=sha(plan_path),
                   retained_boot_sha256=BOOT_SHA, free_before=shutil.disk_usage(ARTIFACTS).free,
                   retained=plan['retain'], deleted=[], phone_operations=False)
    destination = EVIDENCE / 'artifacts-cleanup-result.json'
    destination.write_text(json.dumps(receipt, indent=2) + '\n')
    for path in delete:
        relative = str(path.relative_to(ARTIFACTS))
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        receipt['deleted'].append(relative)
        destination.write_text(json.dumps(receipt, indent=2) + '\n')
        print('Deleted:', relative, flush=True)
    if sha(BOOT) != BOOT_SHA:
        raise RuntimeError('Retained boot image changed during cleanup')
    receipt['free_after'] = shutil.disk_usage(ARTIFACTS).free
    receipt['freed_bytes'] = receipt['free_after'] - receipt['free_before']
    destination.write_text(json.dumps(receipt, indent=2) + '\n')
    print(f'Freed{receipt["freed_bytes"] / (1 << 30):.2f} GiB; free{receipt["free_after"] / (1 << 30):.2f} GiB')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply-plan', type=Path)
    args = parser.parse_args()
    if args.apply_plan:
        apply(args.apply_plan)
    else:
        inventory()
    return 0


if __name__ == '__main__':
    sys.exit(main())
