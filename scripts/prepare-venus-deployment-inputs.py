#!/usr/bin/env python3
"""Host-only 64-GiB partition preview and hash-pinned OS/SystemOS decoding."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import uuid

root = Path('/mnt/g/UniXNU-Port')
device = root / 'ports/UniXNU-venus'
upstream = root / 'sources/UniXNU-guide'
os.environ['UNIXNU_TOOLCHAIN'] = '/root/unixnu-toolchain'
sys.path.insert(0, str(upstream / 'scripts'))
from dual_sys.gpt import GPT
from unixnu.udif import Image

out = root / 'artifacts/venus-deployment'
out.mkdir(exist_ok=True)
def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
def need(value, message):
    if not value:
        raise SystemExit(message)
previous = json.loads((device / 'evidence/dual-readonly.json').read_text())
snapshot = root / 'evidence/venus/dual-readonly-20261025T161421Z'
need(all(sha(snapshot / name) == previous['files'][name] for name in ('gpt-primary.bin', 'gpt-backup.bin')),
     'Retained GPT identity differs')
layout_path = out / 'partition-preview.json'
if not layout_path.exists():
    gpt = GPT((snapshot / 'gpt-primary.bin').read_bytes(), (snapshot / 'gpt-backup.bin').read_bytes(),
              previous['logical_block_bytes'], previous['disk_bytes'] // previous['logical_block_bytes'])
    primary, backup, layout = gpt.split(64 << 30, previous['userdata']['index'])
    after = GPT(primary, backup, gpt.sector, gpt.total)
    # All non-userdata existing partition bytes must remain identical.
    for index in range(gpt.h['count']):
        if index + 1 not in (layout['userdata_index'], layout['unixnu_index']):
            need(gpt.table[index*128:(index+1)*128] == after.table[index*128:(index+1)*128], 'Unrelated GPT entry changed')
    for name, content in [('gpt-primary.before', gpt.primary), ('gpt-backup.before', gpt.backup),
                          ('gpt-primary.preview', primary), ('gpt-backup.preview', backup)]:
        (out / name).write_bytes(content)
    layout.update(device='venus', serial='55870427', sector_bytes=gpt.sector, disk_bytes=previous['disk_bytes'],
                  plan_source='retained Android GPT also matched by the XNU phone block-read test',
                  android_data_may_be_erased=True, approved_device_operations=False,
                  preview_only=True, recovery_session_validated=False,
                  unixnu_guid=next(e['guid'] for e in after.entries if e['name'] == 'unixnu'))
    layout_path.write_text(json.dumps(layout, indent=2) + '\n')
else:
    layout = json.loads(layout_path.read_text())
need(layout['unixnu_bytes'] == 64 << 30 and layout['serial'] == '55870427', 'Unexpected retained preview')
print('Preview: unixnu', hex(layout['unixnu_start']), '..', hex(layout['unixnu_end']),
      'slot', layout['unixnu_index'], '; Android userdata bytes', layout['new_userdata_bytes'], flush=True)

module_path = root / 'sources/UniXNU-zeta-reference/scripts/zeta_apfs_image.py'
spec = importlib.util.spec_from_file_location('zeta_apfs_readonly', module_path)
apfs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apfs)
cache = root / 'artifacts/venus-guide/ipsw/21H461'
windows = []
for name, member, pin in [
    ('OS', '044-76040-038.dmg', '3f99b859c9728379110b66657c7b15285bcb1925ad8b5726542e2cdcf8b1028d'),
    ('SystemOS', '044-76034-038.dmg', 'b4908cde41d23e6bc05e6af51a2c9eeb00cf0f863a6a18b1600c96a3fd70414f'),
]:
    source = cache / member
    need(sha(source) == pin, name + ': input DMG differs from profile pin')
    raw = out / (name + '.raw')
    report_path = out / (name + '-source.json')
    image = Image(source)
    need(shutil.disk_usage(out).free > image.size + (5 << 30) or raw.exists(), 'Insufficient output space')
    if not raw.exists():
        temporary = raw.with_suffix('.partial')
        digest = hashlib.sha256()
        done = 0
        with temporary.open('wb') as target:
            for data in image.blocks():
                target.write(data); digest.update(data); done += len(data)
            target.flush(); os.fsync(target.fileno())
        need(done == image.size, 'Decoded extent differs: ' + name)
        temporary.replace(raw)
    digest = sha(raw)
    need(raw.stat().st_size == image.size, 'Existing raw image has wrong size')
    if report_path.exists():
        need(json.loads(report_path.read_text())['raw_sha256'] == digest, 'Existing raw image changed')
    with raw.open('rb') as stream:
        first = stream.read(4096)
        containers = []
        if first[32:36] == b'NXSB':
            containers.append((0, image.size))
        elif first[512:520] == b'EFI PART':
            entries_lba, count, width = struct.unpack_from('<QII', first, 512 + 72)
            need(width == 128 and 0 < count <= 4096, 'Unsupported IPSW GPT')
            stream.seek(entries_lba * 512)
            entries = stream.read(count * width)
            for index in range(count):
                e = entries[index*128:(index+1)*128]
                if e[:16] != uuid.UUID('7C3457EF-0000-11AA-AA11-00306543ECAC').bytes_le:
                    continue
                start, end = struct.unpack_from('<QQ', e, 32)
                containers.append((start * 512, (end - start + 1) * 512))
        need(len(containers) == 1, name + ': require one APFS container')
        offset, extent = containers[0]
        need(offset + extent <= image.size, 'Container exceeds raw disk')
        container = apfs.Container(stream, offset)
        need(container.block_size == 4096 and apfs.Container.valid(first if not offset else container.block(0)),
             'Invalid APFS block size/checksum')
        volumes = []
        for volume in container.volumes():
            sb = volume.superblock
            volumes.append({'name': volume.name, 'role': volume.role, 'volume_uuid': str(uuid.UUID(bytes=sb[0xf0:0x100])).upper(),
                            'xid': volume.xid, 'fs_flags': volume.fs_flags})
        need(len(volumes) == 1, name + ': volume identity needs explicit selection')
    record = {'component': name, 'ipsw_member': member, 'dmg_sha256': pin, 'dmg_bytes': source.stat().st_size,
              'raw': str(raw), 'raw_bytes': image.size, 'raw_sha256': digest, 'container_offset': offset,
              'container_extent': extent, 'volumes': volumes,
              'apfs_reader_source_sha256': sha(module_path), 'read_only_metadata_inspection': True}
    report_path.write_text(json.dumps(record, indent=2) + '\n')
    windows.append(record)
    print(json.dumps(record, indent=2), flush=True)
summary = {'partition_preview': layout, 'windows': windows, 'device_written': False, 'data_seed_available': False}
(device / 'evidence/deployment-inputs.json').write_text(json.dumps(summary, indent=2) + '\n')
os.sync()
