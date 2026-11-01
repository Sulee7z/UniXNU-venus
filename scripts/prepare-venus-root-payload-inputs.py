"""Validate the Data volume/packed reconstruction and make the original trust bundle."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import uuid

root = Path('/mnt/g/UniXNU-Port')
device = root / 'ports/UniXNU-venus'
upstream = root / 'sources/UniXNU-guide'
out = root / 'artifacts/venus-deployment'
sys.path.insert(0, str(upstream / 'scripts'))
from unixnu.ipsw import im4p_payload
sys.path.insert(0, str(upstream / 'drivers/DarwinBoot/Test'))
from packed_ramdisk import regions, inspect

def need(value, message):
    if not value: raise SystemExit(message)
def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
cache = root / 'artifacts/venus-guide/ipsw/21H461'
modules = [im4p_payload((cache / name).read_bytes()) for name in
           ('044-76040-038.dmg.trustcache', '044-76034-038.dmg.trustcache')]
pins = ('da88460e6e513438d5307e5c526f76497a74754476a24da29f239f0c90120fc2',
        'd121ba89167e03aafd00fa687c30cd8ebc4ccafd10c1408adb2ba3de12403651')
for module, pin in zip(modules, pins):
    need(hashlib.sha256(module).hexdigest() == pin, 'Original trust module differs')
    need(struct.unpack_from('<I', module)[0] == 2 and len(module) == 24 + 24 * struct.unpack_from('<I', module, 20)[0],
         'Invalid trust module extent/version')
bundle = struct.pack('<3I', 2, 12, 12 + len(modules[0])) + b''.join(modules)
bundle_hash = hashlib.sha256(bundle).hexdigest()
need(bundle_hash == '7416ca4f8377146626bb284e2133c76bee6cb4e3ee0af5d648b186235a7323a7', 'Trust bundle differs from OS profile')
(out / 'original-static-system.bundle').write_bytes(bundle)
data = json.loads((out / 'Data.json').read_text())
packed = Path(data['packed']); raw = Path(data['raw'])
need(sha(packed) == data['metadata']['encoded_sha256'] and sha(raw) == data['raw_sha256'], 'Data inputs changed')
logical, extents = regions(packed.read_bytes())
digest = hashlib.sha256(); position = 0; zero = bytes(1024 * 1024)
for offset, content in [*extents, (logical, b'')]:
    while position < offset:
        length = min(len(zero), offset - position)
        digest.update(memoryview(zero)[:length]); position += length
    digest.update(content); position += len(content)
need(digest.hexdigest() == data['raw_sha256'], 'Packed reconstruction is not lossless')
metadata, _ = inspect(packed)
need(metadata == data['metadata'], 'Packed identity differs')
path = root / 'sources/UniXNU-zeta-reference/scripts/zeta_apfs_image.py'
spec = importlib.util.spec_from_file_location('apfs_reader', path)
reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)
with raw.open('rb') as stream:
    container = reader.Container(stream)
    volumes = list(container.volumes())
    need(len(volumes) == 1, 'Ambiguous Data volume')
    observed_uuid = str(uuid.UUID(bytes=volumes[0].superblock[0xf0:0x100])).upper()
need(observed_uuid == data['volume_uuid'], 'Actual Data UUID differs from planned kernel input')
record = {'original_trust_bundle_sha256': bundle_hash, 'original_trust_modules_sha256': list(pins),
          'data_volume_uuid': observed_uuid, 'data_raw_sha256': data['raw_sha256'],
          'data_packed_sha256': data['metadata']['encoded_sha256'], 'data_logical_bytes': logical,
          'data_packed_bytes': packed.stat().st_size, 'packed_full_reconstruction_verified': True,
          'own_code_trust_entries_added': False, 'phone_tested': False}
(device / 'evidence/root-payload-inputs.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
