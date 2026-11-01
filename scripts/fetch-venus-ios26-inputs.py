#!/usr/bin/env python3
"""Fetch pinned23F84 components with checked ranges, complete ZIP CRC and resume."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile
import zlib

from importlib.util import spec_from_file_location, module_from_spec

PROJECT = Path('/mnt/g/UniXNU-Port')
INVENTORY = PROJECT / 'ports/UniXNU-venus/evidence/ios26-input-inventory.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--components', default='DeviceTree;KernelCache;StaticTrustCache;Cryptex1,SystemTrustCache;OS;Cryptex1,SystemOS')
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.parent.is_dir():
        parser.error('Output parent must already exist')
    out.mkdir(exist_ok=True)
    inventory = json.loads(INVENTORY.read_text())
    if inventory['result'] != 'identity-inspected':
        raise RuntimeError('Restore identity inventory has not passed')
    spec = spec_from_file_location('ios26_inventory', Path(__file__).with_name('inspect-venus-ios26-inputs.py'))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    url = inventory['target']['url']
    record = dict(target=inventory['target'], extracted={}, phone_operations=False,
                  source_inventory_sha256=sha(INVENTORY))
    report = out / 'report.json'
    if report.exists():
        record = json.loads(report.read_text())
        if record['target'] != inventory['target']:
            raise RuntimeError('Existing output uses another restore identity')
    with module.CheckedRangeFile(url, block=32 << 20) as remote, zipfile.ZipFile(remote) as archive:
        manifest = archive.read('BuildManifest.plist')
        if hashlib.sha256(manifest).hexdigest() != inventory['manifest_sha256']:
            raise RuntimeError('Restore manifest changed')
        (out / 'BuildManifest.plist').write_bytes(manifest)
        for name in args.components.split(';'):
            row = inventory['components'][name]
            member = archive.getinfo(row['member'])
            if member.file_size != row['bytes'] or f'{member.CRC:08x}' != row['zip_crc32']:
                raise RuntimeError(f'ZIP identity mismatch: {name}')
            path = out / Path(member.filename).name
            receipt = path.with_suffix(path.suffix + '.json')
            if path.exists():
                prior = json.loads(receipt.read_text())
                if prior['member'] != row['member'] or prior['source'] != url or sha(path) != prior['sha256']:
                    raise RuntimeError(f'Existing component changed: {name}')
                record['extracted'][name] = prior
                continue
            partial = path.with_suffix(path.suffix + '.partial')
            existing = partial.stat().st_size if partial.exists() else 0
            if existing > member.file_size or (existing and member.compress_type != zipfile.ZIP_STORED):
                raise RuntimeError('Partial cannot be safely resumed')
            # WSL's advertised virtual capacity is not its backing G: space.
            needed = member.file_size - existing + (2 << 30)
            if shutil.disk_usage(PROJECT).free < needed:
                raise RuntimeError(f'Insufficient G: backing space for{name}; need{needed} bytes')
            digest, crc, size = hashlib.sha256(), 0, 0
            if existing:
                with partial.open('rb') as stream:
                    while data := stream.read(8 << 20):
                        digest.update(data)
                        crc = zlib.crc32(data, crc)
                        size += len(data)
            print(f'Fetching{name}: {member.file_size:,} bytes; resume{existing:,}', flush=True)
            with archive.open(member) as source, partial.open('ab' if existing else 'xb') as target:
                if existing:
                    source.seek(existing)
                while data := source.read(8 << 20):
                    target.write(data)
                    digest.update(data)
                    crc = zlib.crc32(data, crc)
                    size += len(data)
                    if size % (512 << 20) == 0:
                        print(f'{name}: {size >> 20} MiB', flush=True)
            if size != member.file_size or crc != member.CRC:
                raise RuntimeError(f'ZIP CRC/size mismatch:{name}')
            pin = inventory['target'].get('sha256', {}).get(path.name)
            if pin and digest.hexdigest() != pin:
                raise RuntimeError(f'Published source SHA mismatch:{name}')
            partial.rename(path)
            result = dict(**row, source=url, path=str(path), sha256=digest.hexdigest(), zip_crc_verified=True)
            receipt.write_text(json.dumps(result, indent=2) + '\n')
            record['extracted'][name] = result
            report.write_text(json.dumps(record, indent=2) + '\n')
            print(f'PASS:{name}, CRC and SHA verified', flush=True)
    record['result'] = 'requested-components-verified'
    report.write_text(json.dumps(record, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
