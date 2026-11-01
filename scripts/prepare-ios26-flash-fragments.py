#!/usr/bin/env python3
"""Prepare bounded transfer fragments from a complete RAW/FILL root image.

There are no device commands. Each fragment skips only the part of the partition
assigned to other fragments. The union of assigned RAW/FILL ranges must cover
every byte of the complete root image. Sample fragment ranges are independently
decoded and compared with the pinned raw image.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct

BLOCK = 4096
HEADER = 28
CHUNK = 12
MAGIC, RAW, FILL, SKIP = 0xed26ff3a, 0xcac1, 0xcac2, 0xcac3
EXPECTED_RAW_BYTES = 22338863104
EXPECTED_RAW_SHA = 'b0c3dd3ff44f3bb7bf639e281b05da948d7ad85da060f113051d4d03e928049c'
EXPECTED_SPARSE_SHA = 'c21357134f9e2e22b69dd49e6bb16c166e48a9e63530b23039eb858f8dace6a1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def plan_fragments(path, limit):
    parts, rows, covered, encoded = [], [], 0, HEADER + 2 * CHUNK
    size = path.stat().st_size

    def close():
        nonlocal rows, encoded
        if rows:
            first = rows[0]['first_block']
            blocks = sum(row['blocks'] for row in rows)
            parts.append(dict(index=len(parts), first_block=first, blocks=blocks,
                end_block=first + blocks, rows=rows,
                encoded_bytes=HEADER + (CHUNK if first else 0) +
                              sum(row['encoded_bytes'] for row in rows) +
                              (CHUNK if first + blocks < total else 0)))
            rows, encoded = [], HEADER + 2 * CHUNK

    with path.open('rb') as stream:
        raw = stream.read(HEADER)
        magic, major, minor, hs, cs, block, total, count, checksum = struct.unpack('<IHHHHIIII', raw)
        if (magic, major, minor, hs, cs, block, checksum) != (MAGIC, 1, 0, HEADER, CHUNK, BLOCK, 0):
            raise ValueError('Unexpected complete sparse header')
        if total * BLOCK != EXPECTED_RAW_BYTES:
            raise ValueError('Unexpected expanded root extent')
        for index in range(count):
            raw = stream.read(CHUNK)
            if len(raw) != CHUNK:
                raise ValueError(f'Truncated chunk{index}')
            kind, reserved, blocks, length = struct.unpack('<HHII', raw)
            if kind not in (RAW, FILL) or reserved or not 0 < blocks <= total - covered:
                raise ValueError('Source must completely cover the image with RAW/FILL only')
            payload = blocks * BLOCK if kind == RAW else 4
            if length != CHUNK + payload or stream.tell() + payload > size:
                raise ValueError('Invalid chunk payload')
            if HEADER + 2 * CHUNK + length > limit:
                raise ValueError('Source chunk exceeds the bounded fragment limit')
            if encoded + length > limit:
                close()
            rows.append(dict(kind=kind, first_block=covered, blocks=blocks,
                             payload_offset=stream.tell(), payload_bytes=payload,
                             encoded_bytes=length))
            encoded += length
            stream.seek(payload, 1)
            covered += blocks
        close()
        if covered != total or stream.tell() != size:
            raise ValueError('Incomplete input or trailing bytes')
    position = 0
    for part in parts:
        if part['first_block'] != position or part['encoded_bytes'] > limit:
            raise ValueError('Fragment plan has a gap, overlap or oversized transfer')
        position = part['end_block']
    if position != total:
        raise ValueError('Fragment union does not cover the complete root')
    return parts, total


def build_fragment(source, target, part, total):
    first, end = part['first_block'], part['end_block']
    count = len(part['rows']) + bool(first) + bool(end < total)
    with source.open('rb') as stream, target.open('xb') as out:
        out.write(struct.pack('<IHHHHIIII', MAGIC, 1, 0, HEADER, CHUNK, BLOCK, total, count, 0))
        if first:
            out.write(struct.pack('<HHII', SKIP, 0, first, CHUNK))
        for row in part['rows']:
            out.write(struct.pack('<HHII', row['kind'], 0, row['blocks'], row['encoded_bytes']))
            stream.seek(row['payload_offset'])
            remaining = row['payload_bytes']
            while remaining:
                data = stream.read(min(8 << 20, remaining))
                if not data:
                    raise ValueError('Truncated source during fragment staging')
                out.write(data)
                remaining -= len(data)
        if end < total:
            out.write(struct.pack('<HHII', SKIP, 0, total - end, CHUNK))
    if target.stat().st_size != part['encoded_bytes']:
        raise ValueError('Staged fragment byte length differs')


def verify_fragment(fragment, raw_path, part, total):
    digest, position, written = hashlib.sha256(), 0, 0
    first, end = part['first_block'], part['end_block']
    with fragment.open('rb') as stream:
        header = struct.unpack('<IHHHHIIII', stream.read(HEADER))
        if header[:8] != (MAGIC, 1, 0, HEADER, CHUNK, BLOCK, total, len(part['rows']) + bool(first) + bool(end < total)):
            raise ValueError('Fragment header differs')
        for _ in range(header[7]):
            kind, reserved, blocks, size = struct.unpack('<HHII', stream.read(CHUNK))
            following = position + blocks
            if reserved or not blocks or following > total:
                raise ValueError('Invalid staged fragment range')
            if kind == SKIP:
                if size != CHUNK or (position < end and first < following):
                    raise ValueError('Fragment skips a block assigned to itself')
            elif kind in (RAW, FILL):
                if not first <= position < following <= end:
                    raise ValueError('Fragment writes outside its assigned range')
                if kind == RAW:
                    if size != CHUNK + blocks * BLOCK:
                        raise ValueError('Invalid staged RAW payload')
                    remaining = blocks * BLOCK
                    while remaining:
                        data = stream.read(min(8 << 20, remaining))
                        if not data:
                            raise ValueError('Truncated staged RAW payload')
                        digest.update(data)
                        remaining -= len(data)
                else:
                    if size != CHUNK + 4:
                        raise ValueError('Invalid staged FILL payload')
                    pattern = stream.read(4)
                    if len(pattern) != 4:
                        raise ValueError('Truncated FILL')
                    remaining = blocks * BLOCK
                    while remaining:
                        size_now = min(8 << 20, remaining)
                        digest.update(pattern * (size_now // 4))
                        remaining -= size_now
                written += blocks
            else:
                raise ValueError('Unsupported staged chunk')
            position = following
        if position != total or written != part['blocks'] or stream.read(1):
            raise ValueError('Fragment coverage differs')
    expected = hashlib.sha256()
    with raw_path.open('rb') as raw:
        raw.seek(first * BLOCK)
        remaining = part['blocks'] * BLOCK
        while remaining:
            data = raw.read(min(8 << 20, remaining))
            if not data:
                raise ValueError('Truncated pinned raw range')
            expected.update(data)
            remaining -= len(data)
    if digest.hexdigest() != expected.hexdigest():
        raise ValueError('Independent fragment decode differs from raw root range')
    return dict(index=part['index'], path=str(fragment.resolve()), bytes=fragment.stat().st_size,
                sha256=sha(fragment), raw_range_sha256=expected.hexdigest(),
                first_block=first, end_block=end, independent_range_decode_verified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--raw', required=True, type=Path)
    parser.add_argument('--sample-directory', required=True, type=Path)
    parser.add_argument('--plan', required=True, type=Path)
    args = parser.parse_args()
    if args.plan.exists() or args.sample_directory.exists():
        raise SystemExit('Preserve existing plan/samples; choose new output names')
    if not args.plan.parent.is_dir() or not args.sample_directory.parent.is_dir():
        raise SystemExit('Output parents must exist')
    if args.raw.stat().st_size != EXPECTED_RAW_BYTES or sha(args.raw) != EXPECTED_RAW_SHA:
        raise SystemExit('Raw image differs from the pinned root')
    if sha(args.input) != EXPECTED_SPARSE_SHA:
        raise SystemExit('Use the verified complete RAW/FILL transfer')
    limit = 128 << 20
    parts, total = plan_fragments(args.input, limit)
    args.sample_directory.mkdir()
    samples = []
    for index in sorted({0, len(parts) // 2, len(parts) - 1}):
        path = args.sample_directory / f'fragment-{index:04}.sparse.img'
        build_fragment(args.input, path, parts[index], total)
        samples.append(verify_fragment(path, args.raw, parts[index], total))
    report = dict(source=str(args.input.resolve()), source_sha256=EXPECTED_SPARSE_SHA,
                  raw=str(args.raw.resolve()), raw_sha256=EXPECTED_RAW_SHA,
                  expanded_bytes=EXPECTED_RAW_BYTES, total_blocks=total,
                  fragments=parts, fragment_count=len(parts), maximum_encoded_bytes=max(p['encoded_bytes'] for p in parts),
                  encoded_limit=limit, fragment_assigned_ranges_cover_entire_root=True,
                  original_zero_blocks_written_as_fill=True, independently_verified_samples=samples,
                  phone_operations=False, flashed=False, prepared_at=datetime.now(timezone.utc).isoformat())
    with args.plan.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('fragment_count', 'maximum_encoded_bytes',
        'fragment_assigned_ranges_cover_entire_root', 'independently_verified_samples', 'phone_operations')}, indent=2))


if __name__ == '__main__':
    main()
