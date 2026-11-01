#!/usr/bin/env python3
"""Remove a Mach-O init section and export its exact initializer for late registration."""
import argparse
from pathlib import Path
import struct
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'kits/XnuPrelink'))
from native_prelink import macho

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--initializer', required=True)
args = parser.parse_args()
original = args.source.read_bytes()
metadata = macho(original)
if metadata['kind'] != 1:
    raise SystemExit('Late registration requires a Mach-O object')
# LLVM 18 supports Mach-O section removal, but not --globalize-symbol.
subprocess.run(['llvm-objcopy', '--remove-section=__DATA,__mod_init_func', args.source, args.output], check=True)
data = bytearray(args.output.read_bytes())
info = macho(data)
if any(s['name'] == '__mod_init_func' for segment in info['segments'] for s in segment['sections']):
    raise SystemExit('Automatic initializer section remains')
symtab = [at for command, at, _ in info['commands'] if command == 2]
if len(symtab) != 1:
    raise SystemExit('Expected one symbol table')
offset, count, strings, string_size = struct.unpack_from('<4I', data, symtab[0] + 8)
if offset + 16 * count > len(data) or strings + string_size > len(data):
    raise SystemExit('Malformed symbol table')
matches = []
for index in range(count):
    at = offset + index * 16
    name_at, kind, section, _, _ = struct.unpack_from('<IBBHQ', data, at)
    if name_at >= string_size:
        raise SystemExit('Symbol string out of bounds')
    end = data.find(b'\0', strings + name_at, strings + string_size)
    if end < 0:
        raise SystemExit('Unterminated symbol')
    if data[strings + name_at:end].decode() == args.initializer:
        if kind & 0xe0 or kind & 0x0e != 0x0e or not section:
            raise SystemExit('Initializer must be a defined section symbol')
        matches.append(at + 4)
if len(matches) != 1:
    raise SystemExit('Initializer symbol missing or ambiguous')
data[matches[0]] |= 1  # N_EXT; preserve all other nlist attributes.
def text(blob):
    section = next(s for segment in macho(blob)['segments'] for s in segment['sections'] if s['name'] == '__text')
    return blob[section['fileoff']:section['fileoff'] + section['size']]
if text(data) != text(original):
    raise SystemExit('Late registration changed executable instructions')
args.output.write_bytes(data)
print('Late initializer exported; automatic init section removed; text unchanged')
