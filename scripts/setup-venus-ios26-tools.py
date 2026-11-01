#!/usr/bin/env python3
"""Install a pinned standalone ipsw tool in WSL and verify its release hashes."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import urllib.request

OUT = Path('/root/unixnu-build/venus-ios26-tools')
VERSION = '3.1.739'
NAME = f'ipsw_{VERSION}_linux_x86_64.tar.gz'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    if not OUT.parent.is_dir():
        raise RuntimeError('WSL build parent missing')
    OUT.mkdir(exist_ok=True)
    with urllib.request.urlopen(f'https://api.github.com/repos/blacktop/ipsw/releases/tags/v{VERSION}', timeout=60) as stream:
        release = json.load(stream)
    asset = next(row for row in release['assets'] if row['name'] == NAME)
    archive = OUT / NAME
    if not archive.exists():
        with urllib.request.urlopen(asset['browser_download_url'], timeout=120) as stream, archive.open('xb') as target:
            while data := stream.read(8 << 20):
                target.write(data)
    if 'sha256:' + sha(archive) != asset['digest'] or archive.stat().st_size != asset['size']:
        raise RuntimeError('ipsw release asset checksum/size mismatch')
    checksum_asset = next(row for row in release['assets'] if row['name'] == 'checksums.txt')
    with urllib.request.urlopen(checksum_asset['browser_download_url'], timeout=60) as stream:
        checksums = stream.read()
    if 'sha256:' + hashlib.sha256(checksums).hexdigest() != checksum_asset['digest']:
        raise RuntimeError('Release checksums metadata changed')
    expected = next(line.split()[0] for line in checksums.decode().splitlines() if line.split()[-1] == NAME)
    if sha(archive) != expected:
        raise RuntimeError('ipsw asset differs from checksums.txt')
    (OUT / 'checksums.txt').write_bytes(checksums)
    binary = OUT / 'ipsw'
    if not binary.exists():
        with tarfile.open(archive) as package:
            members = [row for row in package.getmembers() if Path(row.name).name == 'ipsw' and row.isfile()]
            if len(members) != 1:
                raise RuntimeError('Expected one standalone ipsw executable')
            with package.extractfile(members[0]) as source, binary.open('xb') as target:
                target.write(source.read())
        binary.chmod(0o755)
    version = subprocess.check_output([binary, 'version'], text=True).strip()
    if VERSION not in version:
        raise RuntimeError('Extracted tool version mismatch')
    report = dict(version=version, url=asset['browser_download_url'], archive_sha256=sha(archive),
                  executable_sha256=sha(binary), global_install=False)
    (OUT / 'tools.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
