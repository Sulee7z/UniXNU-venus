#!/usr/bin/env python3
"""Extract os_log tracev3 payloads from a saved Data run and scan for keywords.

Bounded, read-only, host-only. Raw chunks are kept; LZ4-block payloads are
decoded when their header is recognisable. Missing keywords are reported as
absent, never as zero.
"""
import argparse
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_store_view as store

KEYWORDS = ['FBSDisplayMode', 'main-screen-scale', 'display-scale', 'preferredScale',
            'SpringBoard', 'IOMobileFramebuffer', 'screen parameters', 'EXC_BREAKPOINT',
            'MTLDevice', 'CA::Display']


def lz4_block(data, expected):
    out = bytearray()
    index = 0
    while index < len(data):
        token = data[index]
        index += 1
        literals = token >> 4
        if literals == 15:
            while True:
                value = data[index]
                index += 1
                literals += value
                if value != 255:
                    break
        out += data[index:index + literals]
        index += literals
        if index >= len(data):
            break
        offset = data[index] | data[index + 1] << 8
        index += 2
        match = token & 15
        if match == 15:
            while True:
                value = data[index]
                index += 1
                match += value
                if value != 255:
                    break
        match += 4
        if not offset or offset > len(out):
            raise ValueError('bad LZ4 offset')
        start = len(out) - offset
        for i in range(match):
            out.append(out[start + i])
        if len(out) > expected:
            raise ValueError('LZ4 output overrun')
    return bytes(out)


def scan(blob, name, hits, limit=6):
    for keyword in KEYWORDS:
        needle = keyword.encode()
        position = 0
        found = 0
        while found < limit:
            at = blob.find(needle, position)
            if at < 0:
                break
            context = blob[max(0, at - 90):at + 150]
            text = ''.join(chr(c) if 32 <= c < 127 else '.' for c in context)
            hits.setdefault(keyword, []).append({'file': name, 'offset': at, 'context': text})
            position = at + 1
            found += 1


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--offline', type=Path, required=True)
parser.add_argument('--keyword', action='append', default=[])
parser.add_argument('--max-bytes', type=int, default=96 << 20)
args = parser.parse_args()

ROOT = Path(__file__).resolve().parents[3]
if args.keyword:
    KEYWORDS = args.keyword

view, apfs, volume = store.open_volume(args.offline, ROOT / 'artifacts/venus-deployment/Data.dbr', ROOT)
out = args.offline / 'extracted' / 'tracev3'
out.mkdir(parents=True, exist_ok=True)
hits = {}
files = {}
total = 0
for entry in store.list_directory(apfs, volume, '/db/diagnostics/Persist'):
    if entry.get('kind') != 'file' or not entry['name'].endswith('.tracev3'):
        continue
    if total >= args.max_bytes:
        break
    path = '/db/diagnostics/Persist/' + entry['name']
    try:
        blob = store.read_file(view, apfs, volume, path)
    except ValueError as error:
        files[path] = {'error': str(error)}
        continue
    total += len(blob)
    (out / entry['name']).write_bytes(blob)
    record = {'bytes': len(blob), 'sha256': store.sha(out / entry['name']), 'decoded': 0}
    scan(blob, entry['name'], hits)
    # Chunks begin after the 0x1000 file header; a 4-byte big-endian length may
    # prefix an LZ4 block. Try each 0x1000 boundary and keep successful decodes.
    decoded = bytearray()
    for at in range(0x1000, len(blob) - 8, 0x1000):
        size = struct.unpack_from('>I', blob, at)[0]
        if not 0 < size <= (4 << 20):
            continue
        try:
            payload = lz4_block(blob[at + 4:], size)
        except (ValueError, IndexError):
            continue
        text = ''.join(chr(c) if 32 <= c < 127 else '\n' for c in payload)
        decoded += payload
        scan(payload, entry['name'] + '@' + hex(at), hits)
    if decoded:
        (out / (entry['name'] + '.lz4.bin')).write_bytes(decoded)
        record['decoded'] = len(decoded)
    files[path] = record

report = {'run': str(args.offline), 'present_pages': view.index['present_pages'],
          'tracev3': files, 'keywords': KEYWORDS, 'hits': hits,
          'scope': 'Raw and LZ4-decoded os_log chunks; absence of a keyword is not proof it was never logged'}
(args.offline / 'tracev3-scan.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'files': len(files), 'hits': {k: len(v) for k, v in hits.items()},
                  'report': str(args.offline / 'tracev3-scan.json')}, indent=2))
