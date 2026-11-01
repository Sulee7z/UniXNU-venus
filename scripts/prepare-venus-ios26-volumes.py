#!/usr/bin/env python3
"""Decode decrypted23F84 DMGs into exact raw APFS containers and audit identities."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import uuid

PROJECT = Path('/mnt/g/UniXNU-Port')
INPUTS = Path('/root/unixnu-build/venus-ios26-inputs')
sys.path.insert(0, str(PROJECT / 'sources/UniXNU-guide/scripts'))
from unixnu.udif import Image


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    metadata = json.loads((INPUTS / 'report.json').read_text())
    source = PROJECT / 'sources/UniXNU-zeta-none24smu/scripts/zeta_apfs_image.py'
    spec = importlib.util.spec_from_file_location('apfs_reader26', source)
    apfs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(apfs)
    report = dict(target=metadata['target'], containers={}, phone_operations=False)
    for component, name in [('OS', 'OS'), ('Cryptex1,SystemOS', 'SystemOS')]:
        row = metadata['extracted'][component]
        dmg = Path(row['path']).with_suffix('')
        raw = INPUTS / (name + '.apfs')
        receipt = raw.with_suffix('.apfs.json')
        if raw.exists():
            existing = json.loads(receipt.read_text())
            if sha(raw) != existing['sha256'] or sha(dmg) != existing['dmg_sha256']:
                raise RuntimeError('Existing decoded container changed')
            if existing['sha256'] == existing['dmg_sha256'] and not os.path.samefile(raw, dmg):
                # These decrypted DMGs are already raw APFS. Preserve both
                # recorded paths while removing this tool's redundant copy.
                raw.unlink()
                os.link(dmg, raw)
                print(f'Deduplicated identical{name} raw/DMG paths', flush=True)
            report['containers'][name] = existing
            continue
        if sha(Path(row['path'])) != row['sha256']:
            raise RuntimeError('Encrypted input changed')
        image = Image(dmg)
        iterator = iter(image.blocks())
        prefix = bytearray()
        while len(prefix) < min(image.size, 2 << 20):
            prefix.extend(next(iterator))
        if prefix[32:36] == b'NXSB':
            offset, size = 0, image.size
        elif prefix[512:520] == b'EFI PART':
            entry_lba, count, width = struct.unpack_from('<QII', prefix, 512 + 72)
            if width != 128 or not 0 < count <= 4096 or entry_lba * 512 + count * width > len(prefix):
                raise RuntimeError('Invalid APFS image GPT')
            partitions = []
            for i in range(count):
                entry = prefix[entry_lba * 512 + i * width:entry_lba * 512 + (i + 1) * width]
                if entry[:16] == uuid.UUID('7C3457EF-0000-11AA-AA11-00306543ECAC').bytes_le:
                    first, last = struct.unpack_from('<QQ', entry, 32)
                    partitions.append((first * 512, (last - first + 1) * 512))
            if len(partitions) != 1:
                raise RuntimeError('Expected one APFS partition')
            offset, size = partitions[0]
        else:
            raise RuntimeError('Decoded image is neither raw APFS nor GPT')
        if shutil.disk_usage(PROJECT).free < size + (2 << 30):
            raise RuntimeError('Not enough backing G: space for raw container')
        temporary = raw.with_suffix('.partial')
        if temporary.exists():
            raise RuntimeError('Unverified partial container exists; preserve it for inspection')
        digest, done, position = hashlib.sha256(), 0, 0
        def pieces():
            yield bytes(prefix)
            yield from iterator
        with temporary.open('xb') as output:
            for data in pieces():
                begin = max(offset, position)
                end = min(offset + size, position + len(data))
                if begin < end:
                    chunk = data[begin - position:end - position]
                    output.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                position += len(data)
        if position != image.size or done != size:
            raise RuntimeError('Raw container decode length mismatch')
        with temporary.open('rb') as stream:
            first = stream.read(4096)
            block_size, blocks = struct.unpack_from('<IQ', first, 36)
            if first[32:36] != b'NXSB' or block_size != 4096 or blocks * block_size != done:
                raise RuntimeError('APFS superblock geometry differs from exact decode')
            container = apfs.Container(stream)
            volumes = [dict(name=v.name, uuid=str(uuid.UUID(bytes=v.superblock[0xf0:0x100])).upper(),
                            xid=v.xid, fs_flags=v.fs_flags) for v in container.volumes()]
            if len(volumes) != 1:
                raise RuntimeError('Expected one system container volume')
        temporary.rename(raw)
        result = dict(path=str(raw), bytes=done, sha256=digest.hexdigest(),
                      dmg_sha256=sha(dmg), source_aea_sha256=row['sha256'],
                      original_container_offset=offset, volumes=volumes,
                      reader_sha256=sha(source), exact_geometry_verified=True)
        receipt.write_text(json.dumps(result, indent=2) + '\n')
        report['containers'][name] = result
        print(f'PASS:{name}, {done:,} bytes, volume{volumes[0]["uuid"]}', flush=True)
        (INPUTS / 'volumes.json').write_text(json.dumps(report, indent=2) + '\n')
    (INPUTS / 'volumes.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
