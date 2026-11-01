"""Windows-side fallback for a package pinned by the retained signed APT index."""
import hashlib
from pathlib import Path
import urllib.request

out = Path('G:/UniXNU-Port/artifacts/venus-deployment')
name = 'linux-modules-6.8.0-147-generic_6.8.0-147.147_amd64.deb'
expected = '3b9188304d600fc35a4f4d1f99751f7ea485bb7f9e0cb87831d4ebf2d3423d9d'
target = out / name
if target.exists():
    with target.open('rb') as f:
        if hashlib.file_digest(f, 'sha256').hexdigest() != expected:
            raise SystemExit('Existing guest package hash mismatch; preserved')
else:
    partial = target.with_suffix('.partial')
    digest = hashlib.sha256()
    with urllib.request.urlopen('https://archive.ubuntu.com/ubuntu/pool/main/l/linux/' + name, timeout=90) as response, partial.open('wb') as f:
        while data := response.read(1024 * 1024):
            f.write(data); digest.update(data)
    if partial.stat().st_size != 39250112 or digest.hexdigest() != expected:
        raise SystemExit('Guest modules package identity mismatch')
    partial.replace(target)
print('Verified:', target, expected)
