#!/usr/bin/env python3
"""Assemble the iOS26 SHNGROOT unixnu image on C: with the Venus owner anchor."""
import argparse
import hashlib
import importlib.util
import json
import os
import struct
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path('/root/unixnu-build')
PROJECT = Path('/mnt/g/UniXNU-Port')
INPUTS = ROOT / 'venus-ios26-inputs'
SCRATCH = Path('/mnt/c/unixnu-ios26-root')
KIT = PROJECT / 'sources/UniXNU-guide/kits/VerifiedRoot'
KEYS = ROOT / 'venus-owner-root'
MIB = 1 << 20
CHUNK = 8 * MIB
CAPACITY = 68719476736  # 64 GiB, unixnu 44881664..61658879 on 4096-byte LBAs


def align(value):
    return (value + MIB - 1) // MIB * MIB


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def gpt_header(mine, other, first, last, guid, entries_lba, entries):
    import zlib
    header = bytearray(struct.pack('<8sIIIIQQQQ16sQIII', b'EFI PART', 0x10000, 92, 0, 0,
                                   mine, other, first, last, guid.bytes_le, entries_lba,
                                   128, 128, zlib.crc32(entries)))
    struct.pack_into('<I', header, 16, zlib.crc32(header))
    return bytes(header).ljust(512, b'\0')


def wrap_apfs(source, output, name, volume_uuid):
    """Copy a raw APFS container behind a minimal protective GPT."""
    with source.open('rb') as stream:
        first = stream.read(4096)
    if len(first) != 4096 or first[32:36] != b'NXSB':
        raise RuntimeError(f'{source}: not a raw APFS container')
    block_size, blocks = struct.unpack_from('<IQ', first, 36)
    size = source.stat().st_size
    if block_size != 4096 or blocks * block_size != size:
        raise RuntimeError(f'{source}: APFS geometry does not cover the file')
    source_digest = sha(source)
    disk_uuid = uuid.uuid5(uuid.NAMESPACE_OID, 'venus-disk:' + source_digest)
    partition_uuid = uuid.uuid5(uuid.NAMESPACE_OID, 'venus-apfs:' + source_digest)
    total = align(MIB + size + MIB)
    sectors = total // 512
    start, end = MIB // 512, (MIB + size) // 512 - 1
    entries = bytearray(128 * 128)
    struct.pack_into('<16s16sQQQ72s', entries, 0,
                     uuid.UUID('7C3457EF-0000-11AA-AA11-00306543ECAC').bytes_le,
                     partition_uuid.bytes_le, start, end, 1 << 60,
                     (name + ' APFS').encode('utf-16-le'))
    mbr = bytearray(512)
    struct.pack_into('<B3sB3sII', mbr, 446, 0, b'\0\2\0', 0xee, b'\xff\xff\xff',
                     1, min(sectors - 1, 0xffffffff))
    mbr[510:512] = b'\x55\xaa'
    with output.open('xb') as out:
        out.truncate(total)
        out.write(mbr)
        out.write(gpt_header(1, sectors - 1, 34, sectors - 34, disk_uuid, 2, entries))
        out.write(entries)
        out.seek(MIB)
        digest = hashlib.sha256()
        with source.open('rb') as raw:
            for data in iter(lambda: raw.read(CHUNK), b''):
                digest.update(data)
                out.write(data)
        if digest.hexdigest() != source_digest:
            raise RuntimeError('input changed while copying')
        out.seek((sectors - 33) * 512)
        out.write(entries)
        out.write(gpt_header(sectors - 1, 1, 34, sectors - 34,
                             disk_uuid, sectors - 33, entries))
    return dict(name=name, source=str(source), source_bytes=size, source_sha256=source_digest,
                container_offset=MIB, size=total, partition_uuid=str(partition_uuid).upper(),
                volume_uuid=str(volume_uuid).upper(), path=str(output), sha256=sha(output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f'{args.output} exists; preserve the existing root image')
    SCRATCH.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('verified_manifest', KIT / 'tools/manifest.py')
    signing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(signing)
    private, public = KEYS / 'owner.pem', KEYS / 'owner-public.pem'
    anchor = signing.public_anchor(public)
    windows = []
    volumes = json.loads((INPUTS / 'volumes.json').read_text())['containers']
    for name, source in (('OS', INPUTS / 'OS-grown.apfs'), ('SystemOS', INPUTS / 'SystemOS.apfs')):
        identity = volumes[name]['volumes'][0]['uuid']
        wrapped = SCRATCH / (name + '.img')
        if wrapped.exists():
            raise SystemExit(f'{wrapped} exists; remove the scratch tree to rebuild')
        item = wrap_apfs(source, wrapped, name, uuid.UUID(identity))
        policy_dir = SCRATCH / (name + '-policy')
        with wrapped.open('rb') as raw:
            policy = signing.make(raw, item['size'], private, public, uuid.UUID(identity), 1, policy_dir)
        if policy['image_sha256'] != item['sha256']:
            raise RuntimeError('policy does not cover the exact wrapped image')
        item['policy_path'] = str(policy_dir / 'manifest.bin')
        item['policy_bytes'] = (policy_dir / 'manifest.bin').stat().st_size
        windows.append(item)
        print(f'{name}: wrapped and owner-signed', item['size'], identity, flush=True)
    cursor = MIB
    for item in windows:
        item['offset'] = cursor
        cursor += align(item['size'])
    for item in windows:
        item['policy_offset'] = cursor
        cursor += align(item['policy_bytes'])
    if cursor > CAPACITY:
        raise SystemExit('root image exceeds the 64 GiB unixnu partition')
    manifest = bytearray(4096)
    manifest[:8] = b'SHNGROOT'
    struct.pack_into('<IIQ', manifest, 8, 1, len(windows), cursor)
    for index, item in enumerate(windows):
        extra = struct.pack('<QQ24s', item['policy_offset'], item['policy_bytes'], bytes(24))
        struct.pack_into('<32sQQII32s40s', manifest, 24 + 128 * index, item['name'].encode(),
                         item['offset'], item['size'], 512, 1, bytes.fromhex(item['sha256']), extra)
    manifest[4064:] = hashlib.sha256(manifest[:4064]).digest()
    partial = args.output.with_suffix('.partial')
    with partial.open('xb') as out:
        out.truncate(cursor)
        out.write(manifest)
        for item in windows:
            for key, offset in (('path', item['offset']), ('policy_path', item['policy_offset'])):
                out.seek(offset)
                with Path(item[key]).open('rb') as raw:
                    for data in iter(lambda: raw.read(CHUNK), b''):
                        out.write(data)
        out.flush()
        os.fsync(out.fileno())
    with partial.open('rb') as stream:
        header = stream.read(4096)
        if header[:8] != b'SHNGROOT' or hashlib.sha256(header[:4064]).digest() != header[4064:]:
            raise RuntimeError('manifest readback failed')
        version, count, total = struct.unpack_from('<IIQ', header, 8)
        if (version, count, total) != (1, len(windows), cursor):
            raise RuntimeError('manifest geometry differs')
        for item in windows:
            stream.seek(item['offset'])
            digest = hashlib.sha256()
            remaining = item['size']
            while remaining:
                data = stream.read(min(CHUNK, remaining))
                if not data:
                    raise RuntimeError(f"{item['name']} window is truncated")
                digest.update(data)
                remaining -= len(data)
            if digest.hexdigest() != item['sha256']:
                raise RuntimeError(f"{item['name']} window readback differs")
        import ctypes
        library = SCRATCH / 'verified-root-host.so'
        subprocess.run(['cc', '-std=c11', '-O2', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror',
                        '-I', str(KIT / 'include'), str(KIT / 'src/verified_root.c'),
                        str(KIT / 'tests/openssl_provider.c'), '-lcrypto', '-o', str(library)], check=True)
        native = ctypes.CDLL(str(library))

        class View(ctypes.Structure):
            _fields_ = [('hashes', ctypes.c_void_p), ('image_bytes', ctypes.c_uint64),
                        ('block_count', ctypes.c_uint64), ('generation', ctypes.c_uint64),
                        ('volume_uuid', ctypes.c_uint8 * 16), ('image_sha256', ctypes.c_uint8 * 32)]

        native.vr_host_open.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                                        ctypes.c_uint64, ctypes.POINTER(View)]
        native.vr_host_open.restype = ctypes.c_int
        native.vr_host_block.argtypes = [ctypes.POINTER(View), ctypes.c_uint64, ctypes.c_void_p,
                                         ctypes.c_size_t]
        native.vr_host_block.restype = ctypes.c_int
        trusted = ctypes.create_string_buffer(anchor)
        for item in windows:
            stream.seek(item['policy_offset'])
            envelope = stream.read(item['policy_bytes'])
            encoded, view = ctypes.create_string_buffer(envelope), View()
            if native.vr_host_open(encoded, len(envelope), trusted, 1, ctypes.byref(view)) != 0:
                raise RuntimeError(f"{item['name']}: C signature validation failed")
            if view.image_bytes != item['size'] or bytes(view.volume_uuid) != uuid.UUID(item['volume_uuid']).bytes:
                raise RuntimeError(f"{item['name']}: signed volume/extent differs")
            stream.seek(item['offset'])
            for index in range(view.block_count):
                block = stream.read(min(4096, item['size'] - index * 4096))
                if native.vr_host_block(ctypes.byref(view), index, block, len(block)) != 0:
                    raise RuntimeError(f"{item['name']}: block {index} failed authentication")
            item['blocks_verified_by_c'] = view.block_count
            print(f"{item['name']}: C verified all {view.block_count} blocks", flush=True)
    partial.replace(args.output)
    report = dict(image=str(args.output), image_bytes=args.output.stat().st_size,
                  image_sha256=sha(args.output), windows=windows,
                  trusted_key_sha256=hashlib.sha256(anchor).hexdigest(),
                  unixnu_capacity=CAPACITY, hardware_tested=False, flashed=False,
                  root_mount_verified=False)
    args.output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('image', 'image_bytes', 'image_sha256')}, indent=2))


if __name__ == '__main__':
    main()
