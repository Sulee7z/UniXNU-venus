#!/usr/bin/env python3
"""Build the iOS17 Data seed in an isolated Linux guest from original private/var."""
import argparse
import ctypes
import ctypes.util
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import uuid

root = Path('/mnt/g/UniXNU-Port')
device = root / 'ports/UniXNU-venus'
output = root / 'artifacts/venus-deployment'
tools = Path('/root/unixnu-build/venus-apfs-tools')
config = json.loads((tools / 'inputs.json').read_text())
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--attempt', type=int, default=1)
args = parser.parse_args()
work = tools / ('seed-attempt-' + str(args.attempt))
work.mkdir(exist_ok=False)
def run(command, **kwargs):
    return subprocess.run([str(x) for x in command], check=True, **kwargs)
def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
plan_path = output / 'data-plan.json'
if not plan_path.exists():
    plan_path.write_text(json.dumps({'volume_uuid': str(uuid.uuid4()).upper(), 'logical_bytes': 8 << 30,
                                     'target_partition': 'unixnu', 'created_on_phone': False}, indent=2) + '\n')
plan = json.loads(plan_path.read_text())
raw = work / 'Data.raw'
with raw.open('xb') as f: f.truncate(plan['logical_bytes'])
run([config['mkapfs'], '-L', 'Data', '-u', plan['volume_uuid'], raw])
ramfs = work / 'initramfs'
for name in ('bin', 'dev', 'proc', 'sys', 'tmp', 'mods', 'mnt/os', 'mnt/data'):
    (ramfs / name).mkdir(parents=True)
os.mknod(ramfs / 'dev/console', stat.S_IFCHR | 0o600, os.makedev(5, 1))
os.mknod(ramfs / 'dev/null', stat.S_IFCHR | 0o666, os.makedev(1, 3))
shutil.copy2('/usr/bin/busybox', ramfs / 'bin/busybox')
zstd = ctypes.CDLL(ctypes.util.find_library('zstd'))
zstd.ZSTD_getFrameContentSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
zstd.ZSTD_getFrameContentSize.restype = ctypes.c_uint64
zstd.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
zstd.ZSTD_decompress.restype = ctypes.c_size_t
zstd.ZSTD_isError.argtypes = [ctypes.c_size_t]
zstd.ZSTD_isError.restype = ctypes.c_uint
modules = []
for name in ('crc32c_generic', 'libcrc32c', 'virtio_pci', 'virtio_blk', 'apfs'):
    lines = subprocess.check_output(['modprobe', '-d', tools / 'guest', '-S', config['kernel_release'],
                                     '--show-depends', name], text=True).splitlines()
    for line in lines:
        if not line.startswith('insmod '): continue
        source = Path(line.split()[1])
        if source in modules: continue
        modules.append(source)
module_records = []
loads = []
for i, source in enumerate(modules):
    data = source.read_bytes()
    if source.suffix == '.zst':
        size = zstd.ZSTD_getFrameContentSize(data, len(data))
        if size >= (1 << 64) - 2: size = 64 << 20
        if size > 64 << 20: raise SystemExit('Unexpected module size')
        decoded = ctypes.create_string_buffer(size)
        n = zstd.ZSTD_decompress(decoded, size, data, len(data))
        if zstd.ZSTD_isError(n): raise SystemExit('Module zstd decode failed')
        data = decoded.raw[:n]
    if data[:5] != b'\x7fELF\x02' or struct.unpack_from('<H', data, 18)[0] != 62:
        raise SystemExit('Wrong guest module architecture')
    name = f'{i:02d}.ko'
    (ramfs / 'mods' / name).write_bytes(data)
    loads.append(f'insmod /mods/{name}')
    module_records.append({'source': str(source), 'sha256': hashlib.sha256(data).hexdigest()})
spec = importlib.util.spec_from_file_location('seed_reference', root / 'sources/UniXNU-zeta-reference/scripts/make-zeta-data-seed.py')
reference = importlib.util.module_from_spec(spec); spec.loader.exec_module(reference)
directories = []
for name in reference.RUNTIME + reference.SKELETON:
    uid = 501 if name.startswith('mobile/') else 0
    mode = '1777' if name == 'tmp' else '755'
    directories.append(f'if [ ! -e /mnt/data/{name} ]; then mkdir -p /mnt/data/{name}; chown {uid}:{uid} /mnt/data/{name}; chmod {mode} /mnt/data/{name}; fi')
init = '''#!/bin/busybox sh
/bin/busybox --install -s /bin
set -eu
trap 'echo "VENUS_DATA_FAIL"; poweroff -f' EXIT
mount -t proc proc /proc
mount -t sysfs sys /sys
mount -t devtmpfs dev /dev
''' + '\n'.join(loads) + '''
mount -t apfs -o ro /dev/vdb1 /mnt/os
mount -t apfs -o readwrite /dev/vda /mnt/data
echo VENUS_DATA_BEGIN
test -f /mnt/os/sbin/launchd
test -d /mnt/os/private/var
cd /mnt/os/private/var
find . -path './staged_system_apps' -prune -o -type f -exec sha256sum '{}' ';' | sort > /tmp/source.sha
find . -path './staged_system_apps' -prune -o -mindepth 1 -exec stat -c '%u:%g:%a:%F:%n' '{}' ';' | sort > /tmp/source.meta
find . -path './staged_system_apps' -prune -o -type l -exec sh -c 'for x; do printf "%s:%s\\n" "$x" "$(readlink "$x")"; done' sh '{}' ';' | sort > /tmp/source.links
for x in * .[!.]* ..?*; do
  [ -e "$x" ] || [ -L "$x" ] || continue
  [ "$x" != staged_system_apps ] || continue
  cp -a "$x" /mnt/data/
done
cd /mnt/data
find . -mindepth 1 -exec stat -c '%u:%g:%a:%F:%n' '{}' ';' | sort > /tmp/target.meta
find . -type l -exec sh -c 'for x; do printf "%s:%s\\n" "$x" "$(readlink "$x")"; done' sh '{}' ';' | sort > /tmp/target.links
cmp /tmp/source.meta /tmp/target.meta
cmp /tmp/source.links /tmp/target.links
sha256sum -c /tmp/source.sha
echo VENUS_DATA_COPIED_AND_VERIFIED
''' + '\n'.join(directories) + '''
test ! -d Keychains || stat -c 'VENUS_KEYCHAINS=%u:%g:%a' Keychains
echo "VENUS_SOURCE_FILES=$(wc -l < /tmp/source.sha)"
echo "VENUS_SOURCE_NODES=$(wc -l < /tmp/source.meta)"
sync
cd /
umount /mnt/data
umount /mnt/os
echo VENUS_DATA_UNMOUNTED
trap - EXIT
poweroff -f
'''
(ramfs / 'init').write_text(init)
(ramfs / 'init').chmod(0o755)
listing = subprocess.check_output(['find', '.', '-print0'], cwd=ramfs)
cpio = subprocess.run(['cpio', '--null', '-o', '-H', 'newc'], input=listing, cwd=ramfs, capture_output=True, check=True).stdout
(work / 'initramfs.cpio').write_bytes(cpio)
source_os = output / 'OS.raw'
command = ['qemu-system-x86_64', '-accel', 'tcg', '-cpu', 'max', '-m', '1536', '-smp', '2',
           '-kernel', config['kernel'], '-initrd', work / 'initramfs.cpio',
           '-append', 'console=ttyS0 quiet rdinit=/init panic=-1', '-nographic', '-no-reboot', '-nic', 'none',
           '-drive', f'file={raw},format=raw,if=virtio',
           '-drive', f'file={source_os},format=raw,if=virtio,readonly=on']
(work / 'qemu-command.json').write_text(json.dumps([str(x) for x in command], indent=2) + '\n')
with (work / 'guest.log').open('w') as log:
    result = subprocess.run([str(x) for x in command], stdout=log, stderr=subprocess.STDOUT, timeout=900)
console = (work / 'guest.log').read_text(errors='replace')
if result.returncode or 'VENUS_DATA_FAIL' in console or 'VENUS_DATA_UNMOUNTED' not in console:
    raise SystemExit('Guest seed construction failed; preserved at ' + str(work))
with (work / 'apfsck.log').open('w') as log:
    run([config['apfsck'], raw], stdout=log, stderr=subprocess.STDOUT)
sys.path.insert(0, str(root / 'sources/UniXNU-guide/drivers/DarwinBoot/Test'))
from packed_ramdisk import pack, inspect
packed = output / 'Data.dbr'
metadata = pack(raw, packed)
_, first = inspect(packed)
if first[32:36] != b'NXSB': raise SystemExit('Packed seed lost its APFS header')
if metadata['encoded_bytes'] + (60 << 20) > 160 << 20: raise SystemExit('Seed cannot fit the current payload budget')
if sha(source_os) != json.loads((output / 'OS-source.json').read_text())['raw_sha256']:
    raise SystemExit('Original OS changed')
record = {'volume_uuid': plan['volume_uuid'], 'raw': str(raw), 'raw_sha256': sha(raw),
          'packed': str(packed), 'metadata': metadata, 'guest_kernel': config['kernel'],
          'modules': module_records, 'guest_log': str(work / 'guest.log'), 'apfsck_passed': True,
          'source_file_hashes_metadata_and_links_checked': True, 'source_os_unchanged': True,
          'user_keys_or_records_created': False, 'phone_tested': False, 'guest_accelerator': 'tcg'}
(output / 'Data.json').write_text(json.dumps(record, indent=2) + '\n')
(device / 'evidence/deployment-data-seed.json').write_text(json.dumps(record, indent=2) + '\n')
os.sync()
print(json.dumps(record, indent=2))
