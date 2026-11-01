#!/usr/bin/env python3
"""Assemble unchanged iOS17 disks plus real VerifiedRoot policies for unixnu."""
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import uuid

root = Path('/mnt/g/UniXNU-Port')
device = root / 'ports/UniXNU-venus'
out = root / 'artifacts/venus-deployment'
kit = root / 'sources/UniXNU-guide/kits/VerifiedRoot'
MIB = 1 << 20
def align(n): return (n + MIB - 1) // MIB * MIB
def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def need(ok, message):
    if not ok: raise SystemExit(message)
layout = json.loads((out / 'partition-preview.json').read_text())
need(layout['unixnu_bytes'] == 64 << 30 and layout['unixnu_index'] == 35, 'Unexpected target plan')
image = out / 'unixnu-root.img'
need(not image.exists(), 'Root image already exists; preserve it and inspect its report before rebuilding')
keys = Path('/root/unixnu-build/venus-owner-root')
keys.mkdir(mode=0o700, exist_ok=True)
os.chmod(keys, 0o700)
private, public = keys / 'owner.pem', keys / 'owner-public.pem'
if not private.exists():
    need(not public.exists(), 'Refuse replacing the owner key')
    mask = os.umask(0o077)
    try:
        subprocess.run(['openssl', 'genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:3072', '-out', private],
                       check=True, capture_output=True)
    finally: os.umask(mask)
if not public.exists():
    subprocess.run(['openssl', 'pkey', '-in', private, '-pubout', '-out', public], check=True, capture_output=True)
spec = importlib.util.spec_from_file_location('verified_manifest', kit / 'tools/manifest.py')
signing = importlib.util.module_from_spec(spec); spec.loader.exec_module(signing)
anchor = signing.public_anchor(public)
header = ('/* Public owner anchor. Private key remains in the G-backed WSL key directory. */\n'
          'const unsigned char verified_root_key[395] = {\n' +
          ''.join('  ' + ','.join(f'0x{b:02x}' for b in anchor[i:i+16]) + ',\n' for i in range(0, len(anchor), 16)) + '};\n')
public_header = device / 'package/VenusOwnerRootKey.h'
need(not public_header.exists() or public_header.read_text() == header, 'Owner anchor mismatch')
public_header.write_text(header)
windows = []
for name in ('OS', 'SystemOS'):
    item = json.loads((out / (name + '-source.json')).read_text())
    path = Path(item['raw'])
    need(sha(path) == item['raw_sha256'], 'Input changed: ' + name)
    policy_dir = out / (name + '-policy')
    identity = item['volumes'][0]['volume_uuid']
    with path.open('rb') as stream:
        policy = signing.make(stream, item['raw_bytes'], private, public, uuid.UUID(identity), 1, policy_dir)
    need(policy['image_sha256'] == item['raw_sha256'], 'Signed different bytes')
    windows.append(dict(name=name, path=str(path), size=item['raw_bytes'], sha256=item['raw_sha256'],
                        volume_uuid=identity, policy_path=str(policy_dir / 'manifest.bin'),
                        policy_bytes=(policy_dir / 'manifest.bin').stat().st_size))
    print(name, 'signed:', item['raw_bytes'], identity, flush=True)
cursor = MIB
for item in windows:
    item['offset'] = cursor; cursor += align(item['size'])
for item in windows:
    item['policy_offset'] = cursor; cursor += align(item['policy_bytes'])
need(cursor + (8 << 30) + (1 << 30) + (4 << 20) < layout['unixnu_bytes'], 'Root/Data/reserve exceed target')
manifest = bytearray(4096); manifest[:8] = b'SHNGROOT'
struct.pack_into('<IIQ', manifest, 8, 1, 2, cursor)
for i, item in enumerate(windows):
    extra = struct.pack('<QQ24s', item['policy_offset'], item['policy_bytes'], bytes(24))
    struct.pack_into('<32sQQII32s40s', manifest, 24 + i*128, item['name'].encode(), item['offset'], item['size'],
                     512, 1, bytes.fromhex(item['sha256']), extra)
manifest[4064:] = hashlib.sha256(manifest[:4064]).digest()
partial = image.with_suffix('.partial')
with partial.open('wb') as target:
    target.truncate(cursor); target.write(manifest)
    for item in windows:
        for filename, offset in ((item['path'], item['offset']), (item['policy_path'], item['policy_offset'])):
            target.seek(offset)
            with open(filename, 'rb') as source:
                for data in iter(lambda: source.read(8*MIB), b''): target.write(data)
    target.flush(); os.fsync(target.fileno())
library = out / 'verified-root-host.so'
subprocess.run(['cc', '-std=c11', '-O2', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror',
                '-I', kit / 'include', kit / 'src/verified_root.c', kit / 'tests/openssl_provider.c',
                '-lcrypto', '-o', library], check=True)
class View(ctypes.Structure):
    _fields_ = [('hashes', ctypes.c_void_p), ('image_bytes', ctypes.c_uint64), ('block_count', ctypes.c_uint64),
                ('generation', ctypes.c_uint64), ('volume_uuid', ctypes.c_uint8 * 16), ('image_sha256', ctypes.c_uint8 * 32)]
native = ctypes.CDLL(str(library))
native.vr_host_open.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_uint64, ctypes.POINTER(View)]
native.vr_host_open.restype = ctypes.c_int
native.vr_host_block.argtypes = [ctypes.POINTER(View), ctypes.c_uint64, ctypes.c_void_p, ctypes.c_size_t]
native.vr_host_block.restype = ctypes.c_int
trusted = ctypes.create_string_buffer(anchor)
with partial.open('rb', buffering=8*MIB) as stream:
    need(stream.read(4096) == manifest, 'Manifest writeback mismatch')
    for item in windows:
        stream.seek(item['policy_offset']); envelope = stream.read(item['policy_bytes'])
        encoded, view = ctypes.create_string_buffer(envelope), View()
        need(native.vr_host_open(encoded, len(envelope), trusted, 1, ctypes.byref(view)) == 0, 'C signature/table validation failed')
        need(view.image_bytes == item['size'] and bytes(view.volume_uuid) == uuid.UUID(item['volume_uuid']).bytes,
             'Signed volume/extent differs')
        stream.seek(item['offset']); digest = hashlib.sha256()
        for index in range(view.block_count):
            block = stream.read(min(4096, item['size'] - index*4096))
            need(native.vr_host_block(ctypes.byref(view), index, block, len(block)) == 0, 'Written block failed authentication')
            digest.update(block)
        need(digest.hexdigest() == item['sha256'], 'Assembled window differs from original raw disk')
        damaged = bytes([block[0] ^ 1]) + block[1:]
        need(native.vr_host_block(ctypes.byref(view), view.block_count-1, damaged, len(damaged)) == 5, 'Block corruption was accepted')
        damaged_envelope = bytearray(envelope); damaged_envelope[160] ^= 1
        bad = ctypes.create_string_buffer(bytes(damaged_envelope)); invalid = View()
        need(native.vr_host_open(bad, len(envelope), trusted, 1, ctypes.byref(invalid)) != 0, 'Bad signature accepted')
        item['all_written_blocks_verified_by_c'] = view.block_count
        print(item['name'], 'C verified every assembled block:', view.block_count, flush=True)
partial.replace(image)
record = dict(image=str(image), image_bytes=cursor, image_sha256=sha(image), windows=windows,
              partition='unixnu', partition_bytes=layout['unixnu_bytes'], partition_exists_on_device=False,
              owner_anchor_sha256=hashlib.sha256(anchor).hexdigest(), public_header=str(public_header),
              expected_data_logical_bytes=8 << 30, expected_reserve_bytes=1 << 30,
              data_seed_ready=False, boot_kernel_ready=False, device_written=False, flash_command=None,
              original_os_and_systemos_disks_unchanged=True, native_c_signatures_and_all_blocks_verified=True)
(out / 'unixnu-root.json').write_text(json.dumps(record, indent=2) + '\n')
(device / 'evidence/deployment-root-image.json').write_text(json.dumps(record, indent=2) + '\n')
os.sync()
print('Prepared', image, cursor, record['image_sha256'])
