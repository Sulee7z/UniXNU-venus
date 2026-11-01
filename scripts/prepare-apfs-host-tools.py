#!/usr/bin/env python3
"""Build the Linux APFS image tools; module is for a separate QEMU guest only."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

root = Path('/mnt/g/UniXNU-Port')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--offline', action='store_true')
args = parser.parse_args()
work = Path('/root/unixnu-build/venus-apfs-tools')
work.mkdir(exist_ok=True)
env = dict(os.environ, DEBIAN_FRONTEND='noninteractive')
def run(args, cwd=work):
    subprocess.run([str(a) for a in args], cwd=cwd, env=env, check=True)
if not args.offline: run(['apt-get', 'update'])
deps = subprocess.check_output(['apt-cache', 'depends', 'linux-headers-generic'], text=True)
match = re.search(r'Depends:\s+linux-headers-(6\.8\.0-\d+-generic)', deps)
if not match: raise SystemExit('Unexpected guest kernel series')
kernel = match.group(1)
if not args.offline:
    run(['apt-get', 'install', '-y', '--no-install-recommends', 'qemu-system-x86', 'busybox-static', 'cpio', 'kmod',
         'libfuse-dev', 'zlib1g-dev', 'libbz2-dev', 'libssl-dev', 'liblzma-dev', 'pkg-config',
         'linux-headers-' + kernel])
packages = work / 'packages'; packages.mkdir(exist_ok=True)
if not args.offline: run(['apt-get', 'download', 'linux-image-' + kernel, 'linux-modules-' + kernel], packages)
archives = list(packages.glob('linux-image-' + kernel + '_*.deb'))
if len(archives) != 1: raise SystemExit('Ambiguous guest kernel package')
guest = work / 'guest'; guest.mkdir(exist_ok=True)
run(['dpkg-deb', '-x', archives[0], guest])
modules = list(packages.glob('linux-modules-' + kernel + '_*.deb'))
if not modules:
    modules = list((root / 'artifacts/venus-deployment').glob('linux-modules-' + kernel + '_*.deb'))
if len(modules) != 1: raise SystemExit('Ambiguous guest modules package')
run(['dpkg-deb', '-x', modules[0], guest])
records = {}
for name, url in [('apfsprogs', 'https://github.com/eafer/apfsprogs.git'),
                  ('linux-apfs-rw', 'https://github.com/linux-apfs/linux-apfs-rw.git')]:
    source = work / name
    if not source.exists(): run(['git', 'clone', '--depth', '1', url, source])
    records[name] = {'url': url, 'revision': subprocess.check_output(['git', '-C', source, 'rev-parse', 'HEAD'], text=True).strip()}
if records['apfsprogs']['revision'] != '1bd1c1c2140d13d1b6d2e03379316572bee70aa3':
    raise SystemExit('Review mkapfs directory inode flags before using another revision')
run(['make', '-j8'], work / 'apfsprogs/mkapfs')
run(['make', '-j8'], work / 'apfsprogs/apfsck')
run(['make', '-j8', 'KERNEL_DIR=/usr/src/linux-headers-' + kernel], work / 'linux-apfs-rw')
extra = guest / 'lib/modules' / kernel / 'extra'
extra.mkdir(parents=True, exist_ok=True)
__import__('shutil').copy2(work / 'linux-apfs-rw/apfs.ko', extra / 'apfs.ko')
run(['depmod', '-b', guest, kernel])
record = {'kernel_release': kernel, 'kernel': str(guest / 'boot' / ('vmlinuz-' + kernel)),
          'kernel_package_sha256': hashlib.sha256(archives[0].read_bytes()).hexdigest(), 'sources': records,
          'module_loaded_into_host': False, 'module': str(extra / 'apfs.ko'),
          'module_sha256': hashlib.sha256((extra / 'apfs.ko').read_bytes()).hexdigest(),
          'mkapfs': str(work / 'apfsprogs/mkapfs/mkapfs'), 'apfsck': str(work / 'apfsprogs/apfsck/apfsck')}
(work / 'inputs.json').write_text(json.dumps(record, indent=2) + '\n')
os.sync()
print(json.dumps(record, indent=2))
