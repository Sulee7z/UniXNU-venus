#!/usr/bin/env python3
"""Build read-only apfs-fuse locally and mount the exact decrypted restore inputs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

OUT = Path('/root/unixnu-build/venus-ios26-tools')
INPUTS = Path('/root/unixnu-build/venus-ios26-inputs')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    source = OUT / 'apfs-fuse'
    if not source.exists():
        subprocess.run(['git', 'clone', '--depth', '1', 'https://github.com/sgan81/apfs-fuse.git', str(source)], check=True)
        subprocess.run(['git', '-C', str(source), 'submodule', 'update', '--init', '--depth', '1'], check=True)
    build = source / 'build'
    build.mkdir(exist_ok=True)
    with (OUT / 'apfs-fuse-build.log').open('w') as log:
        for command in (['cmake', '-S', str(source), '-B', str(build), '-DUSE_FUSE3=ON'],
                        ['cmake', '--build', str(build), '--parallel', '4']):
            completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
            if completed.returncode:
                raise RuntimeError('apfs-fuse build failed; see apfs-fuse-build.log')
    binary = build / 'apfs-fuse'
    record = dict(source_revision=subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(),
                  executable_sha256=sha(binary), mounts={}, writable=False)
    for name, sentinel in [('OS', 'sbin/launchd'), ('SystemOS', 'System/Library/Caches/com.apple.dyld')]:
        mount = INPUTS / ('mount-' + name)
        mount.mkdir(exist_ok=True)
        if not os.path.ismount(mount):
            subprocess.run([str(binary), str(INPUTS / (name + '.apfs')), str(mount)], check=True)
        root = mount / 'root' if (mount / 'root' / sentinel).exists() else mount
        if not (root / sentinel).exists():
            raise RuntimeError(f'{name} read-only mount does not expose{sentinel}')
        record['mounts'][name] = dict(path=str(root), mountpoint=str(mount), sentinel=sentinel)
    (OUT / 'apfs-fuse.json').write_text(json.dumps(record, indent=2) + '\n')
    print('PASS: read-only APFS OS/SystemOS mounts ready')


if __name__ == '__main__':
    main()
