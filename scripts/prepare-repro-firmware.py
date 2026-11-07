#!/usr/bin/env python3
"""Apply the hash-locked firmware source overlay without discarding user edits."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tomllib

# Firmware preflight does not inherit XNU_*. The assembled board kit carries
# its own marker; reject ambiguous matches rather than assuming a device name.
tree = Path(__file__).resolve().parents[1]
markers = list((tree / 'kits').glob('*/repro-inputs.toml'))
if len(markers) != 1:
    raise ValueError('Exactly one source-replay device kit marker is required')
marker = markers[0]
document = tomllib.loads(marker.resolve().read_text())
repo = (marker.resolve().parent / document['device_directory']).resolve()
inputs = tomllib.loads((repo / document['source_inputs']).read_text())
uefi = Path(os.environ['UNIXNU_UEFI']).resolve()
revision = subprocess.check_output(['git', '-C', str(uefi), 'rev-parse', 'HEAD'], text=True).strip()
if revision != inputs['uefi']['commit']:
    raise ValueError('Pinned Mu-Silicium source required')
lock = json.loads((repo / 'repro/support.lock.json').read_text())['files']
overlay = repo / 'repro/firmware/overlay'
for source in overlay.rglob('*'):
    if not source.is_file():
        continue
    name = source.relative_to(overlay).as_posix()
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != lock[source.relative_to(repo).as_posix()]:
        raise ValueError('Firmware source overlay changed: ' + name)
    target = uefi / name
    if target.exists() and target.read_bytes() != data:
        original = subprocess.run(['git', '-C', str(uefi), 'show', 'HEAD:' + name], capture_output=True)
        if original.returncode or target.read_bytes() != original.stdout:
            raise ValueError('Preserve existing firmware source edits: ' + name)
    if not target.exists() or target.read_bytes() != data:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
print('Pinned066 DSC/FDF, SEC, shim and memory-map source overlay validated')
