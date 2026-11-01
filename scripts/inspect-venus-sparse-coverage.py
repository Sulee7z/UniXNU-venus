#!/usr/bin/env python3
"""Read sparse chunk headers and report whether every output block is written.

This inspects local files only. It neither expands the image nor accesses a
device, and it does not claim verification of the RAW payload hashes.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import struct


def inspect(path):
    size = path.stat().st_size
    kinds = {0xcac1: 'RAW', 0xcac2: 'FILL', 0xcac3: 'DONT_CARE'}
    counts = {name: {'chunks': 0, 'blocks': 0} for name in kinds.values()}
    covered = largest_raw = 0
    with path.open('rb') as stream:
        header = stream.read(28)
        if len(header) != 28:
            raise ValueError('Truncated sparse header')
        magic, major, minor, hs, cs, block, total, count, checksum = struct.unpack('<IHHHHIIII', header)
        if (magic, major, minor, hs, cs, block, checksum) != (0xed26ff3a, 1, 0, 28, 12, 4096, 0):
            raise ValueError('Unexpected sparse format')
        if not total or not count:
            raise ValueError('Empty image')
        for index in range(count):
            raw = stream.read(cs)
            if len(raw) != cs:
                raise ValueError(f'Truncated chunk {index}')
            kind, reserved, blocks, length = struct.unpack('<HHII', raw)
            if kind not in kinds or reserved or not blocks or blocks > total - covered:
                raise ValueError(f'Invalid chunk {index}')
            payload = blocks * block if kind == 0xcac1 else (4 if kind == 0xcac2 else 0)
            if length != cs + payload or stream.tell() + payload > size:
                raise ValueError(f'Invalid payload extent {index}')
            stream.seek(payload, 1)
            counts[kinds[kind]]['chunks'] += 1
            counts[kinds[kind]]['blocks'] += blocks
            covered += blocks
            if kind == 0xcac1:
                largest_raw = max(largest_raw, payload)
        if covered != total or stream.tell() != size:
            raise ValueError('Incomplete coverage or trailing bytes')
    skipped = counts['DONT_CARE']['blocks'] * block
    return dict(image=str(path.resolve()), sparse_bytes=size, expanded_bytes=total * block,
                chunk_header_structure_valid=True, chunk_count=count, block_bytes=block,
                counts=counts, largest_raw_chunk_bytes=largest_raw,
                skipped_bytes=skipped, complete_write_coverage=skipped == 0,
                raw_payload_hashes_verified=False, device_access=False,
                inspected_at=datetime.now(timezone.utc).isoformat())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    report = inspect(args.image)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
