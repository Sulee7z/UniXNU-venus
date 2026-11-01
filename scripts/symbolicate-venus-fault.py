#!/usr/bin/env python3
"""Map photographed arm64 crash addresses directly in the read-only 21H461 SystemOS image."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
import urllib.request
import uuid
import zlib

ROOT = Path('/mnt/g/UniXNU-Port')
DEFAULT_OUT = ROOT / 'artifacts/venus-exit-fault/symbolication'
FORMAT_URL = 'https://raw.githubusercontent.com/apple-oss-distributions/dyld/a571176e8e00c47e95b95e3156820ebec0cbd5e6/cache-builder/dyld_cache_format.h'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pc', required=True, type=lambda s: int(s, 0))
parser.add_argument('--lr', required=True, type=lambda s: int(s, 0))
parser.add_argument('--slide', required=True, type=lambda s: int(s, 0))
parser.add_argument('--esr', required=True, type=lambda s: int(s, 0))
parser.add_argument('--component', choices=('OS', 'SystemOS'), default='SystemOS')
parser.add_argument('--frame', action='append', default=[], type=lambda s: int(s, 0))
parser.add_argument('--output', type=Path, default=DEFAULT_OUT,
                    help='Independent output directory for this observation')
parser.add_argument('--photo', type=Path,
                    default=Path('/mnt/g/43ae1a26-abd0-4064-90a3-ccc6d3726c72~1.jpg'))
parser.add_argument('--inspect-frontboard', action='store_true',
                    help='Inspect nearby instructions, data references and call targets without local symbols')
parser.add_argument('--inspect-display-scale', action='store_true',
                    help='Inspect QuartzCore/MobileGestalt scale metadata and original readers')
args = parser.parse_args()
OUT = args.output
OUT.mkdir(parents=True, exist_ok=True)


def need(ok, why):
    if not ok:
        raise ValueError(why)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


# Compile offsetof/sizeof against selected structs from the exact Apple header.
# Unrelated chained-fixup definitions are not needed for this reader.
header_path = OUT / 'dyld_cache_format.h'
if not header_path.exists():
    cached_header = DEFAULT_OUT / 'dyld_cache_format.h'
    header_path.write_bytes(cached_header.read_bytes() if cached_header.exists() else
                            urllib.request.urlopen(FORMAT_URL, timeout=60).read())
header_source = header_path.read_text()
types = ['dyld_cache_header', 'dyld_cache_mapping_info', 'dyld_cache_mapping_and_slide_info',
         'dyld_cache_image_text_info', 'dyld_cache_local_symbols_info', 'dyld_cache_local_symbols_entry_64']
declarations = []
for name in types:
    match = re.search(r'struct\s+' + name + r'\s*\{.*?^};', header_source, re.M | re.S)
    need(match is not None, 'Missing Apple format declaration: ' + name)
    declarations.append(match.group())
fields = ['imagesTextOffset', 'localSymbolsOffset', 'sharedRegionStart', 'maxSlide', 'symbolFileUUID',
          'mappingWithSlideOffset', 'mappingOffset']
cpp = '#include <cstddef>\n#include <cstdio>\n#include <cstdint>\n#include <uuid/uuid.h>\n'
cpp += '\n'.join(declarations) + '\nint main(){\n'
cpp += '\n'.join(f'printf("{name} %zu\\n",offsetof(dyld_cache_header,{name}));' for name in fields)
cpp += '\n' + '\n'.join(f'printf("{name} %zu\\n",sizeof({name}));' for name in types[1:]) + '\n}\n'
(OUT / 'offsets.cpp').write_text(cpp)
subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror', str(OUT / 'offsets.cpp'),
                '-o', str(OUT / 'offsets')], check=True, timeout=60)
offsets = dict((k, int(v)) for k, v in (line.split() for line in
               subprocess.check_output([str(OUT / 'offsets')], text=True).splitlines()))
need(offsets['dyld_cache_mapping_info'] == 32 and offsets['dyld_cache_mapping_and_slide_info'] == 56 and
     offsets['dyld_cache_image_text_info'] == 32 and offsets['dyld_cache_local_symbols_info'] == 24 and
     offsets['dyld_cache_local_symbols_entry_64'] == 16, 'Unexpected original format sizes')

reader_path = ROOT / 'sources/UniXNU-zeta-reference/scripts/zeta_apfs_image.py'
spec = importlib.util.spec_from_file_location('venus_apfs_readonly', reader_path)
apfs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apfs)
source = json.loads((ROOT / f'artifacts/venus-deployment/{args.component}-source.json').read_text())
raw = Path(source['raw'])
pins = {'OS': 'e5634d04a8ac35f024845f583394e0a35deb26a04cb0c00286a8674e25a9a4f2',
        'SystemOS': 'b4908cde41d23e6bc05e6af51a2c9eeb00cf0f863a6a18b1600c96a3fd70414f'}
need(sha(raw) == source['raw_sha256'] == pins[args.component],
     args.component + ' image does not match deployed 21H461 inputs')
need(sha(reader_path) == source['apfs_reader_source_sha256'], 'Qualified read-only APFS reader changed')
stream = raw.open('rb')
container = apfs.Container(stream, source['container_offset'])
volumes = list(container.volumes())
need(len(volumes) == 1, 'Ambiguous SystemOS volume')
volume = volumes[0]
need(str(uuid.UUID(bytes=volume.superblock[0xf0:0x100])).upper() == source['volumes'][0]['volume_uuid'],
     'SystemOS volume UUID mismatch')
directory = '/System/Library/Caches/com.apple.dyld'
root_block = container.omap_lookup(volume.omap_root, volume.root_tree, volume.xid)
print('APFS root:', json.dumps({'incompatible': hex(volume.incompatible),
      'tree_type': hex(struct.unpack_from('<I', volume.superblock, 0x74)[0]),
      'root_oid': volume.root_tree, 'mapped_block': root_block,
      'first64': container.block(root_block)[:64].hex()}), flush=True)


def catalog_node(number):
    """Parse a catalog/fext node; sealed roots legitimately omit the object header."""
    block = container.block(number)
    if block[:32] != bytes(32) and not container.valid(block):
        raise ValueError(f'bad object checksum at block {number}')
    flags, level, count = struct.unpack_from('<HHI', block, 32)
    table_offset, table_length = struct.unpack_from('<HH', block, 40)
    keys = 56 + table_offset + table_length
    values = container.block_size - (40 if flags & 1 else 0)
    entries = []
    for index in range(count):
        if flags & 4:
            key_off, value_off = struct.unpack_from('<HH', block, 56 + table_offset + 4 * index)
            key = block[keys + key_off:keys + key_off + 16]
            value = block[values - value_off:values - value_off + (16 if level == 0 else 8)]
        else:
            key_off, key_len, value_off, value_len = struct.unpack_from('<4H', block, 56 + table_offset + 8 * index)
            key = block[keys + key_off:keys + key_off + key_len]
            value = block[values - value_off:values - value_off + value_len]
        entries.append((key, value))
    return flags, level, entries


def sealed_records(oid, kind, base):
    wanted = (oid, kind)
    found = []

    def visit(virtual):
        block = container.omap_lookup(volume.omap_root, virtual, volume.xid)
        flags, level, entries = catalog_node(block)
        prefixes = []
        for key, value in entries:
            header = struct.unpack_from('<Q', key)[0]
            prefixes.append((header & 0x0fffffffffffffff, header >> 60))
        for index, (key, value) in enumerate(entries):
            if level == 0:
                if prefixes[index] == wanted:
                    found.append((key, value))
                continue
            upper = prefixes[index + 1] if index + 1 < len(entries) else None
            if prefixes[index] <= wanted and (upper is None or wanted <= upper):
                # Sealed catalog index values are child_oid followed by a hash;
                # the child id is relative to the catalog root object id.
                child = struct.unpack_from('<Q', value)[0] + base
                visit(child)
    visit(base)
    return found


def sealed_extents(private_id):
    fext_oid = struct.unpack_from('<Q', volume.superblock, 0x408)[0]
    fext_type = struct.unpack_from('<I', volume.superblock, 0x410)[0]
    if not fext_oid:
        raise ValueError('sealed volume has no fext tree')
    root = fext_oid if fext_type & 0x40000000 else container.omap_lookup(volume.omap_root, fext_oid, volume.xid)
    found = []

    def visit(number):
        flags, level, entries = catalog_node(number)
        for key, value in entries:
            if len(key) < 16:
                continue
            key_private, logical = struct.unpack_from('<QQ', key)
            if len(value) >= 16 and key_private == private_id:
                length, physical = struct.unpack_from('<QQ', value)
                found.append((logical, length & 0x00ffffffffffffff, physical))
            if level and len(value) >= 8:
                visit(struct.unpack_from('<Q', value)[0])
    visit(root)
    found.sort()
    cursor = 0
    for logical, length, physical in found:
        if logical != cursor or not physical:
            raise ValueError(f'sealed stream {private_id:#x} has a hole or sparse extent')
        cursor += length
    return found


if volume.incompatible & 0x20:
    volume.records = lambda oid, kind: sealed_records(oid, kind, volume.root_tree)
    volume.stream_extents = sealed_extents
    print('APFS sealed catalog/fext reader selected', flush=True)
directory_inode = volume.lookup(directory)
names = []
for key, value in volume.records(directory_inode, apfs.TYPE_DIR_REC):
    length = struct.unpack_from('<I', key, 8)[0] & 0x3ff
    name = key[12:12 + length].rstrip(b'\0').decode()
    if name.startswith('dyld_shared_cache_arm64'):
        names.append(name)
print('Original cache files:', ', '.join(names), flush=True)


def lzfse_decode(blob):
    import os
    source = OUT / f'.lzfse-{os.getpid()}.in'
    target = OUT / f'.lzfse-{os.getpid()}.out'
    try:
        source.write_bytes(blob)
        subprocess.run(['/root/unixnu-toolchain/bin/lzfse', '-decode', '-i', str(source),
                        '-o', str(target)], check=True, timeout=300)
        return target.read_bytes()
    finally:
        source.unlink(missing_ok=True)
        target.unlink(missing_ok=True)


def decode_fork(fork):
    data_offset, map_offset, data_length, map_length = struct.unpack_from('>4I', fork)
    count = struct.unpack_from('<I', fork, data_offset + 4)[0]
    base = data_offset + 4
    out = bytearray()
    for index in range(count):
        offset, size = struct.unpack_from('<II', fork, base + 4 + 8 * index)
        chunk = fork[base + offset:base + offset + size]
        out += chunk[1:] if chunk[0] == 0xff else zlib.decompress(chunk)
    return bytes(out)


class File:
    def __init__(self, name):
        self.name = name
        inode = volume.lookup(directory + '/' + name)
        attrs = volume.xattrs(inode)
        records = volume.records(inode, apfs.TYPE_INODE)
        need(len(records) == 1, name + ': ambiguous inode')
        private_id = struct.unpack_from('<Q', records[0][1], 8)[0]
        self.data = None
        if 'com.apple.decmpfs' in attrs:
            value = attrs['com.apple.decmpfs'][1]
            magic, kind, size = struct.unpack_from('<4sIQ', value)
            need(magic == b'fpmc', name + ': invalid decmpfs header')
            if kind == 3:
                # Inline zlib payload follows the 16-byte decmpfs header.
                self.data = zlib.decompress(value[16:])
            elif kind == 4:
                stream_size, extents = volume.resource_fork(inode)
                fork = volume.read_extents(stream_size, extents)
                self.data = decode_fork(fork)
            elif kind in (8, 14):
                if 'com.apple.ResourceFork' in attrs:
                    stream_size, extents = volume.resource_fork(inode)
                    blob = volume.read_extents(stream_size, extents)
                else:
                    blob = value[16:]
                self.data = lzfse_decode(blob)
            else:
                raise ValueError(f'{name}: unsupported decmpfs type {kind}')
            need(len(self.data) == size, name + ': decoded length differs from inode size')
            self.extent_bytes = len(self.data)
        else:
            self.extents = volume.stream_extents(private_id)
            need(bool(self.extents), name + ': no regular data stream')
            self.extent_bytes = sum(length for _, length, _ in self.extents)

    def read(self, offset, size):
        need(0 <= offset <= offset + size <= self.extent_bytes, self.name + ': read outside stored extents')
        if self.data is not None:
            return self.data[offset:offset + size]
        parts = []
        for logical, length, physical in self.extents:
            begin, end = max(offset, logical), min(offset + size, logical + length)
            if begin < end:
                parts.append(container.read_raw(physical * container.block_size + begin - logical, end - begin))
        data = b''.join(parts)
        need(len(data) == size, self.name + ': incomplete extent read')
        return data

    def cstring(self, offset, maximum=2048):
        data = self.read(offset, min(maximum, self.extent_bytes - offset))
        need(b'\0' in data, self.name + ': unterminated string')
        return data.split(b'\0', 1)[0].decode()


files = {}
for name in names:
    if name.endswith(('.symbols', '.dyldlinkedit')) or (not (args.inspect_frontboard or args.inspect_display_scale) and name.endswith('.dylddata')):
        continue
    try:
        files[name] = File(name)
    except ValueError as error:
        print('Skipped cache file:', name, '-', error, flush=True)
main = files['dyld_shared_cache_arm64']
header = main.read(0, 512)
need(header[:16].rstrip(b'\0') == b'dyld_v1   arm64', 'Wrong target cache architecture')
region = struct.unpack_from('<Q', header, offsets['sharedRegionStart'])[0]
maximum = struct.unpack_from('<Q', header, offsets['maxSlide'])[0]
need(args.pc % 4 == 0 and args.lr % 4 == 0 and 0 <= args.slide <= maximum and args.slide % 4096 == 0,
     'Photographed addresses/slide violate cache bounds or instruction alignment')
catalog, slid = [], []
for name, f in files.items():
    if name.endswith('.symbols'):
        continue
    h = f.read(0, 512)
    need(h[:16].rstrip(b'\0') == b'dyld_v1   arm64', 'Mixed cache architecture: ' + name)
    off, count = struct.unpack_from('<II', h, offsets['mappingOffset'])
    need(0 < count < 1024, 'Invalid mapping count')
    for i in range(count):
        va, size, fileoff, maximum_prot, prot = struct.unpack('<3Q2I', f.read(off + i * 32, 32))
        need(fileoff + size <= f.extent_bytes, 'Cache mapping exceeds APFS extents')
        catalog.append((va, size, fileoff, prot, name))
    off, count = struct.unpack_from('<II', h, offsets['mappingWithSlideOffset'])
    need(count < 1024, 'Invalid slide mapping count')
    for i in range(count):
        slid.append((f, struct.unpack('<6Q2I', f.read(off + i * 56, 56))))


def original(va, size):
    matches = [(files[name], off + va - begin, prot) for begin, length, off, prot, name in catalog
               if begin <= va and va + size <= begin + length]
    need(len(matches) == 1, f'Unmapped or ambiguous cache address {va:#x}+{size:#x}')
    f, off, prot = matches[0]
    return f.read(off, size), f.name, off, prot


textoff, count = struct.unpack_from('<2Q', header, offsets['imagesTextOffset'])
need(0 < count < 10000, 'Invalid image-text count')
images = []
for i in range(count):
    image_uuid, va, size, pathoff = struct.unpack('<16sQ2I', main.read(textoff + i * 32, 32))
    images.append((va, size, main.cstring(pathoff), image_uuid.hex()))
entries, local = {}, files.get('dyld_shared_cache_arm64.symbols')
if local:
    need(local.read(88, 16) == header[offsets['symbolFileUUID']:offsets['symbolFileUUID'] + 16],
         'Symbols cache UUID does not match the main cache')
    lo, local_size = struct.unpack('<2Q', local.read(offsets['localSymbolsOffset'], 16))
    no, nc, so, ss, eo, ec = struct.unpack('<6I', local.read(lo, 24))
    need(no + nc * 16 <= local_size and so + ss <= local_size and eo + ec * 16 <= local_size,
         'Local symbol tables exceed their declared extent')
    for i in range(ec):
        image_offset, start, number = struct.unpack('<Q2I', local.read(lo + eo + i * 16, 16))
        entries[image_offset] = (start, number)


def describe(pc, return_address=False):
    va = pc - args.slide - (4 if return_address else 0)
    instruction, name, off, prot = original(va, 4)
    image = next((im for im in images if im[0] <= va < im[0] + im[1]), None)
    row = dict(observed=hex(pc), callsite_adjustment=-4 if return_address else 0,
               unslid_va=hex(va), cache_file=name, file_offset=off, instruction=instruction.hex(),
               executable=bool(prot & 4), image=image[2] if image else None)
    if local and image and image[0] - region in entries:
        start, number = entries[image[0] - region]
        need(start + number <= nc, 'Local-symbol range outside table')
        table = local.read(lo + no + start * 16, number * 16)
        best = None
        for pos in range(number):
            string, kind, section, desc, value = struct.unpack_from('<IBBHQ', table, pos * 16)
            if not kind & 0xe0 and kind & 0xe == 0xe and section and image[0] <= value <= va:
                if best is None or value > best[0]:
                    best = value, string
        if best:
            value, string = best
            need(string < ss, 'Local-symbol string outside pool')
            row.update(symbol=local.cstring(lo + so + string, min(2048, ss - string)),
                       symbol_va=hex(value), symbol_offset=va - value)
    return row


rows = [describe(args.pc), describe(args.lr, True)]
for frame in args.frame:
    if frame:
        try:
            rows.append(describe(frame, True))
        except ValueError as error:
            rows.append({'observed': hex(frame), 'not_symbolicated': str(error)})
pc = args.pc - args.slide
code, _, _, _ = original(pc - 128, 256)
(OUT / 'fault-block.bin').write_bytes(code)
assembly = subprocess.run(['/usr/bin/llvm-mc', '--triple=aarch64', '--disassemble'],
                          input=' '.join(f'0x{x:02x}' for x in code), text=True, capture_output=True)
(OUT / 'fault-block.disassembly.txt').write_text(assembly.stdout + assembly.stderr)
result = {
    'photo': str(args.photo).replace('/mnt/g/', 'G:/', 1),
    'photo_sha256': sha(args.photo),
    'input_kind': 'Manual photo transcription, not a GDB saved-state report',
    'raw_systemos_sha256': source['raw_sha256'], 'systemos_volume_uuid': source['volumes'][0]['volume_uuid'],
    'format_reference': FORMAT_URL, 'format_header_sha256': sha(header_path), 'compiled_format_offsets': offsets,
    'main_cache_uuid': header[88:104].hex(), 'symbols_uuid_matched': local is not None,
    'cache_slide': hex(args.slide), 'observed_esr': hex(args.esr),
    'esr_is_aarch64_brk_zero': args.esr >> 26 == 0x3c and args.esr & 0xffff == 0,
    'original_pc_is_brk_zero': rows[0]['instruction'] == '000020d4',
    'addresses': rows, 'disassembly_start_va': hex(pc - 128),
    'original_images_modified': False,
    'limit': 'Static code mapping of transcribed addresses; no live exception text or registers beyond the photo were read.'
}
(OUT / 'symbolication.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
if args.inspect_frontboard:
    from venus_frontboard_inspect import inspect
    inspect(original, images, slid, pc, OUT, result)
if args.inspect_display_scale:
    from venus_scale_inspect import inspect_scale
    inspect_scale(original, images, slid, OUT)
stream.close()
