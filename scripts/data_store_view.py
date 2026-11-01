#!/usr/bin/env python3
"""Strict read-only SHNGDATA view and uncompressed APFS file extraction.

APFS j_inode_val_t has a 92-byte fixed prefix; its type-8 xfield is j_dstream_t.
Read j_dstream_t.size, never the allocation/extent length, as the file's EOF.
Format reference: Apple File System Reference, Inodes and Extended Fields;
https://github.com/sgan81/apfs-fuse/blob/master/ApfsLib/DiskStruct.h
"""
import bisect
import hashlib
import importlib.util
import json
import mmap
import struct
import uuid
import zlib
from pathlib import Path

PAGE = 4096
SEED_SHA = 'ca732abdafa194ceb1d1ede1b20f930374180d238da6f74ebb00a2caa4c6fb33'
DATA_UUID = 'FCC1EC83-9500-4D4D-AEED-6004A520B3C0'
MAX_FILE_BYTES = 128 << 20


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_metadata(meta, index, seed_identity):
    geometry = index['geometry']
    pages = geometry['pages']
    bitmap_blocks = (pages + 32767) // 32768
    if (pages != 2097152 or geometry['seed_bytes'] != pages*PAGE or
            geometry['store_absolute_lba'] != [59299519, 61396736] or
            geometry['partition_relative_skip_blocks'] != 14417855 or
            geometry['bitmap_blocks'] != bitmap_blocks or
            geometry['metadata_blocks'] != 1+bitmap_blocks or
            geometry['metadata_bytes'] != (1+bitmap_blocks)*PAGE):
        raise ValueError('Unqualified Data geometry')
    if len(meta) != (1+bitmap_blocks)*PAGE:
        raise ValueError('Short metadata')
    if hashlib.sha256(meta).hexdigest() != index['metadata_sha256']:
        raise ValueError('Metadata SHA mismatch')
    magic, version, head_size, n = struct.unpack_from('<8sIIQ', meta)
    if (magic, version, head_size, n) != (b'SHNGDATA', 1, 64, pages):
        raise ValueError('Wrong SHNGDATA header')
    if struct.unpack_from('<I', meta, 60)[0] != zlib.crc32(meta[:60]):
        raise ValueError('Bad SHNGDATA CRC')
    if meta[24:56].hex() != seed_identity:
        raise ValueError('Store belongs to another seed')
    if struct.unpack_from('<I', meta, 56)[0] != index['generation']:
        raise ValueError('Generation mismatch')
    if sum(b.bit_count() for b in meta[PAGE:]) != index['present_pages']:
        raise ValueError('Present-page count mismatch')
    return pages


class DataView:
    def __init__(self, run_dir, seed_path, root):
        self.run_dir = Path(run_dir).resolve()
        self.index = json.loads((self.run_dir/'index.json').read_text(encoding='utf-8'))
        self.meta = (self.run_dir/'metadata.bin').read_bytes()
        self.bitmap = self.meta[PAGE:]
        self.maps, self.handles, self.provenance = [], [], []
        self.seed_stream = None
        self.seed_path = Path(seed_path)
        if sha(self.seed_path) != SEED_SHA:
            raise ValueError('Data seed SHA mismatch')
        packed = module(Path(root)/'sources/UniXNU-guide/drivers/DarwinBoot/Test/packed_ramdisk.py', 'packed_view')
        logical, extents = packed.regions(self.seed_path.read_bytes())
        self.pages = check_metadata(self.meta, self.index, packed.logical_hash(logical, extents))
        if logical != self.pages*PAGE:
            raise ValueError('Seed size mismatch')
        self.length = logical
        self.seed = [(offset, bytes(data)) for offset, data in extents]
        self.seed_starts = [offset for offset, _ in self.seed]
        covered = bytearray(len(self.bitmap))
        end = 0
        try:
            for entry in self.index['runs']:
                first, blocks = entry['first_page'], entry['blocks']
                if first < end or blocks <= 0 or first+blocks > self.pages:
                    raise ValueError('Overlapping or out-of-range capture run')
                end = first+blocks
                path = (self.run_dir/entry['file']).resolve()
                if not path.is_relative_to(self.run_dir) or path == self.run_dir:
                    raise ValueError('Capture filename escapes run directory')
                if path.stat().st_size != blocks*PAGE:
                    raise ValueError('Short/oversized capture run: '+entry['file'])
                digest = sha(path)
                if entry.get('sha256', digest) != digest:
                    raise ValueError('Capture run SHA mismatch: '+entry['file'])
                self.provenance.append({**entry, 'sha256': digest,
                    'capture_time_sha_available': 'sha256' in entry})
                for page in range(first, end):
                    mask = 1 << (page & 7)
                    if not self.bitmap[page >> 3] & mask:
                        raise ValueError('Capture run includes an unmarked page')
                    covered[page >> 3] |= mask
                handle = path.open('rb')
                self.handles.append(handle)
                self.maps.append((first, blocks, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)))
            if covered != self.bitmap:
                raise ValueError('Missing captured pages; refusing to substitute zeros')
        except BaseException:
            self.close()
            raise
        self.starts = [a for a, _, _ in self.maps]
        self.position = 0

    def present(self, page):
        if not 0 <= page < self.pages:
            raise ValueError('Page outside Data disk')
        return bool(self.bitmap[page >> 3] & (1 << (page & 7)))

    def page(self, page):
        if self.present(page):
            i = bisect.bisect_right(self.starts, page)-1
            if i >= 0:
                first, blocks, mapping = self.maps[i]
                if page < first+blocks:
                    at = (page-first)*PAGE
                    return mapping[at:at+PAGE]
            raise ValueError('Present page has no capture')
        at = page*PAGE
        i = bisect.bisect_right(self.seed_starts, at)-1
        if i >= 0:
            start, data = self.seed[i]
            if at < start+len(data):
                return data[at-start:at-start+PAGE]
        return bytes(PAGE)

    def read_at(self, offset, length):
        if offset < 0 or length < 0:
            raise ValueError('Negative disk range')
        length = min(length, max(0, self.length-offset))
        out = bytearray()
        while len(out) < length:
            pos = offset+len(out)
            within = pos % PAGE
            count = min(PAGE-within, length-len(out))
            out += self.page(pos//PAGE)[within:within+count]
        return bytes(out)

    def seek(self, offset, whence=0):
        if whence != 0 or offset < 0:
            raise ValueError('Only nonnegative absolute seeks are supported')
        self.position = offset
        return offset

    def read(self, length):
        data = self.read_at(self.position, length)
        self.position += len(data)
        return data

    def close(self):
        for _, _, mapping in self.maps:
            mapping.close()
        for handle in self.handles:
            handle.close()
        self.maps.clear()
        self.handles.clear()

    def __enter__(self): return self
    def __exit__(self, *args): self.close()


def open_volume(run_dir, seed_path, root):
    view = DataView(run_dir, seed_path, root)
    try:
        apfs = module(Path(root)/'sources/UniXNU-zeta-reference/scripts/zeta_apfs_image.py', 'apfs_view')
        container = apfs.Container(view)
        volumes = list(container.volumes())
        if len(volumes) != 1:
            raise ValueError('Ambiguous Data volume count')
        volume = volumes[0]
        if str(uuid.UUID(bytes=volume.superblock[0xf0:0x100])).upper() != DATA_UUID:
            raise ValueError('Wrong Data volume UUID')
        if container.block_size != PAGE or not volume.fs_flags & 1:
            raise ValueError('Unsupported Data block size/encryption')
        return view, apfs, volume
    except BaseException:
        view.close()
        raise


def volume_path(path):
    if path == '/private/var': return '/'
    if path.startswith('/private/var/'): return path[len('/private/var'):]
    return path


def inode_info(value):
    if len(value) < 92:
        raise ValueError('Truncated inode')
    info = {'private_id': struct.unpack_from('<Q', value, 8)[0],
            'mode': struct.unpack_from('<H', value, 80)[0],
            'flags': struct.unpack_from('<Q', value, 48)[0],
            'bsd_flags': struct.unpack_from('<I', value, 68)[0], 'size': None,
            'xfields': []}
    if len(value) == 92: return info
    if len(value) < 96: raise ValueError('Truncated xfield header')
    count, used = struct.unpack_from('<HH', value, 92)
    start = at = 96+count*4
    if start+used > len(value): raise ValueError('Xfields exceed inode')
    for i in range(count):
        kind, flags, size = struct.unpack_from('<BBH', value, 96+i*4)
        if at+size > start+used: raise ValueError('Xfield exceeds declared data')
        info['xfields'].append({'type':kind, 'bytes':size, 'offset':at})
        if kind == 8:
            if size != 40 or info['size'] is not None:
                raise ValueError('Invalid/duplicate DSTREAM')
            info['size'], info['allocated'], info['crypto'], _, _ = struct.unpack_from('<5Q', value, at)
        at += (size+7)&~7
    if at != start+used: raise ValueError('Xfield alignment/length mismatch')
    return info


def file_info(apfs, volume, path):
    inode = volume.lookup(volume_path(path))
    records = volume.records(inode, apfs.TYPE_INODE)
    if len(records) != 1: raise ValueError('Ambiguous inode: '+path)
    return {'inode':inode, **inode_info(records[0][1])}


def read_file(view, apfs, volume, path, limit=None):
    info = file_info(apfs, volume, path)
    if info['mode'] & 0o170000 != 0o100000:
        raise ValueError('Not a regular file: '+path)
    if info['bsd_flags'] & 0x20:
        raise ValueError('Compressed file requires decmpfs decoding: '+path)
    spans = []
    end = 0
    for key, value in volume.records(info['private_id'], apfs.TYPE_FILE_EXTENT):
        if len(key) != 16 or len(value) != 24:
            raise ValueError('Invalid extent record')
        logical, = struct.unpack_from('<Q', key, 8)
        length_flags, physical, crypto = struct.unpack('<3Q', value)
        length = length_flags & 0x00ffffffffffffff
        if crypto or length_flags >> 56:
            raise ValueError('Unsupported encrypted/flagged extent')
        if not length or logical < end or (logical|length) % PAGE:
            raise ValueError('Invalid/overlapping extent')
        if physical and (physical*PAGE+length > view.length):
            raise ValueError('Extent outside Data disk')
        if logical > end and not info['flags'] & 0x200:
            raise ValueError('Missing nonsparse extent')
        spans.append((logical, length, physical))
        end = logical+length
    size = info['size']
    if size is None:
        if spans: raise ValueError('File extents without DSTREAM length')
        size = 0
    if size > end and not info['flags'] & 0x200:
        raise ValueError('File data shorter than DSTREAM length')
    if limit is not None:
        if limit < 0: raise ValueError('Negative limit')
        size = min(size, limit)
    if size > MAX_FILE_BYTES:
        raise ValueError('File exceeds extraction limit')
    out = bytearray(size)
    for logical, length, physical in spans:
        take = min(length, max(0, size-logical))
        if physical and take:
            data = view.read_at(physical*PAGE, take)
            if len(data) != take: raise ValueError('Short extent read')
            out[logical:logical+take] = data
    return bytes(out)


def list_directory(apfs, volume, path):
    inode = 2 if volume_path(path)=='/' else volume.lookup(volume_path(path))
    result = []
    for key, value in volume.records(inode, apfs.TYPE_DIR_REC):
        length = int.from_bytes(key[8:12], 'little') & 0x3ff
        name = key[12:12+length].rstrip(b'\0').decode('utf-8')
        if not name or name in ('.','..') or any(c in name for c in '/\\\0'):
            raise ValueError('Unsafe directory name')
        records = volume.records(int.from_bytes(value[:8], 'little'), apfs.TYPE_INODE)
        if len(records) != 1: raise ValueError('Directory entry inode missing/ambiguous')
        info = inode_info(records[0][1])
        kind = {0o40000:'dir', 0o100000:'file', 0o120000:'symlink'}.get(info['mode']&0o170000,'other')
        result.append({'name':name,'kind':kind,'bytes':info['size'],'allocated_bytes':info.get('allocated')})
    return sorted(result, key=lambda row:(row['kind']!='dir',row['name']))
