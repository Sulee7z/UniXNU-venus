"""Retain the exact first tested archive/source before the bank-selector revision."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--suffix', choices=('', '-banks'), default='')
args = parser.parse_args()
root = Path('/mnt/g/UniXNU-Port')
artifact = root / ('artifacts/venus-ufs-read' + args.suffix)
source = root / 'artifacts/venus-ufs-read-unixnu'
compiled = Path('/root/unixnu-build/venus-guide-out/venus/ipados-17.7.11-21H461/venus/tree/build/venus-ufs-read-unixnu/source')
record = json.loads((root / ('ports/UniXNU-venus/evidence/ufs-read' + args.suffix + '-candidate.json')).read_text())
expected = record['archive']['archive_sha256']
if hashlib.sha256((source / 'libShengUfs.a').read_bytes()).hexdigest() != expected:
    raise SystemExit('Active archive is no longer the first tested revision')
out = artifact / 'linked-inputs'
out.mkdir(exist_ok=False)
for name in ('libShengUfs.a', 'venus-build.json', 'bindings.json', 'compile-command.json'):
    shutil.copy2(source / name, out / name)
shutil.copytree(compiled, out / 'source')
os.sync()
print('Retained first tested inputs:', out, expected)
