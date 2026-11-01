"""Prepare a fully covered sparse root image, independently expanded and hashed."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
from venus_sparse import encode, inspect_complete

root = Path('/mnt/g/UniXNU-Port')
out = root/'artifacts/venus-deployment'
source = out/'unixnu-root.img'; sparse = out/'unixnu-root.sparse.img'
report = json.loads((out/'unixnu-root.json').read_text())
if shutil.disk_usage(out).free < source.stat().st_size + (5 << 30): raise SystemExit('Insufficient staging space')
if sparse.exists(): raise SystemExit('Preserve and verify the existing transfer image before rebuilding')
partial = out/'unixnu-root.sparse.partial'
result = encode(source, partial)
if result['expanded_sha256'] != report['image_sha256'] or result['expanded_bytes'] != report['image_bytes']:
    raise SystemExit('Raw root identity changed')
if inspect_complete(partial) != report['image_bytes']: raise SystemExit('Sparse coverage mismatch')
reference_path = root/'sources/UniXNU-zeta-reference/scripts/make-zeta-root-delta.py'
spec = importlib.util.spec_from_file_location('reference_sparse', reference_path)
reference = importlib.util.module_from_spec(spec); spec.loader.exec_module(reference)
with tempfile.TemporaryDirectory(prefix='venus-sparse-', dir='/root/unixnu-build') as temporary:
    empty = Path(temporary)/'empty-base'; empty.write_bytes(b'')
    reconstructed = reference.apply_and_hash(empty, partial)
if reconstructed != report['image_sha256']: raise SystemExit('Independent expanded SHA256 differs')
partial.replace(sparse)
with sparse.open('rb') as f: encoded_hash = hashlib.file_digest(f, 'sha256').hexdigest()
result.update(partition='unixnu', sparse_path=str(sparse), sparse_bytes=sparse.stat().st_size,
              sparse_sha256=encoded_hash, independent_expanded_sha256=reconstructed,
              independent_decoder_sha256=hashlib.sha256(reference_path.read_bytes()).hexdigest(),
              requires_existing_device_bytes=False, android_reset_verified=False,
              flash_authorized=False, device_written=False, fastboot_chunk_limit='128M')
(out/'root-flash-plan.json').write_text(json.dumps(result,indent=2)+'\n')
(root/'ports/UniXNU-venus/evidence/root-flash-preparation.json').write_text(json.dumps(result,indent=2)+'\n')
os.sync()
print(json.dumps(result,indent=2))
