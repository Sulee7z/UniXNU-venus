"""Read Venus GPT/F2FS prerequisites from Android; never plan, resize or write a device."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import struct
import subprocess
import sys

root = Path(r'G:\UniXNU-Port')
sys.path.insert(0, str(root / 'sources/UniXNU-guide/scripts/dual_sys'))
from gpt import read_gpt

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--adb-port', choices=(5037, 5038), type=int, required=True)
args = parser.parse_args()
adb = [str(root / 'tools/platform-tools/adb.exe'), '-P', str(args.adb_port), '-s', '55870427']
def command(text, binary=False):
    result = subprocess.run([*adb, 'exec-out' if binary else 'shell',
                             'su -c ' + shlex.quote(text)], capture_output=True, timeout=30, check=True)
    return result.stdout if binary else result.stdout.decode('utf-8', 'strict').strip()

identity = subprocess.check_output([*adb, 'shell', 'getprop ro.product.device'], timeout=15).strip()
if identity != b'venus' or command('id -u') != '0':
    raise SystemExit('Expected the authorized Venus device with read access')

def block(value):
    if not re.fullmatch(r'/dev/block/[A-Za-z0-9_-]+', value):
        raise SystemExit('Unexpected block path')
    return value

raw = block(command('readlink -f /dev/block/by-name/userdata'))
node = Path(raw).name
sys_path = command(f'readlink -f /sys/class/block/{node}')
disk = block('/dev/block/' + Path(sys_path).parent.name)
sector = int(command(f'blockdev --getss {disk}'))
disk_bytes = int(command(f'blockdev --getsize64 {disk}'))
if sector not in (512, 4096) or disk_bytes % sector:
    raise SystemExit('Unsupported logical sector geometry')
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out = root / 'evidence/venus' / ('dual-readonly-' + stamp)
out.mkdir(exist_ok=False)
def read(lba, count):
    if lba < 0 or count <= 0 or sector * count > 1024 * 1024 or lba + count > disk_bytes // sector:
        raise SystemExit('GPT read outside bounded input')
    data = command(f'dd if={disk} bs={sector} skip={lba} count={count} 2>/dev/null', binary=True)
    if len(data) != sector * count:
        raise SystemExit('Short GPT read')
    return data
gpt = read_gpt(read, sector, disk_bytes // sector)
(out / 'gpt-primary.bin').write_bytes(gpt.primary)
(out / 'gpt-backup.bin').write_bytes(gpt.backup)
users = [e for e in gpt.entries if e['name'] == 'userdata']
if len(users) != 1:
    raise SystemExit('userdata GPT identity is ambiguous')
user = users[0]
mounts = command('cat /proc/mounts')
data_mounts = [line.split() for line in mounts.splitlines() if len(line.split()) >= 4 and line.split()[1] == '/data']
if len(data_mounts) != 1 or data_mounts[0][2] != 'f2fs':
    raise SystemExit('Expected one current F2FS /data mount')
mount = data_mounts[0]
mapped = block(command('readlink -f ' + shlex.quote(mount[0])))
superblocks = command(f'dd if={mapped} bs=4096 count=2 2>/dev/null', binary=True)
if len(superblocks) != 8192:
    raise SystemExit('Short F2FS superblock read')
(out / 'f2fs-superblocks.bin').write_bytes(superblocks)
s, t = superblocks[1024:4096], superblocks[5120:8192]
u32 = lambda offset: struct.unpack_from('<I', s, offset)[0]
if u32(0) != 0xf2f52010:
    raise SystemExit('Mapped data does not expose an F2FS superblock')
raw_bytes = int(command(f'blockdev --getsize64 {raw}'))
mapped_bytes = int(command(f'blockdev --getsize64 {mapped}'))
slaves = command(f'ls -1 /sys/class/block/{Path(mapped).name}/slaves').splitlines()
holders = command(f'ls -1 /sys/class/block/{node}/holders').splitlines()
twrp = command('getprop ro.twrp.version')
booted = command('getprop sys.boot_completed')
fs = {'copies_equal': s == t, 'log_sectorsize': u32(8), 'log_sectors_per_block': u32(12),
      'log_blocksize': u32(16), 'log_blocks_per_segment': u32(20), 'segments_per_section': u32(24),
      'blocks': struct.unpack_from('<Q', s, 36)[0], 'feature_bits': u32(2180),
      'device_table_nonempty': bool(s[2201]), 'mount_options': mount[3]}
conditions = {'gpt_copies_and_crcs_valid': True,
              'userdata_last_occupied': user['end'] == max(e['end'] for e in gpt.entries),
              'free_gpt_entry': len(gpt.entries) < gpt.h['count'],
              'unixnu_absent': not any(e['name'].lower() == 'unixnu' for e in gpt.entries),
              'f2fs_geometry_matches_helper': s == t and u32(16) == 12 and u32(20) == 9 and u32(24) == 1
                  and u32(8) + u32(12) == 12 and 9 <= u32(8) <= 12 and not s[2201] and not u32(2180) & 2,
              'checkpoint_enabled': 'checkpoint=disable' not in mount[3],
              'equal_mapping_size': raw_bytes == mapped_bytes,
              'single_dm_backing': raw == mapped or slaves == [node],
              'single_raw_holder': raw == mapped or holders == [Path(mapped).name],
              'compatible_recovery_active': bool(twrp) and booted != '1',
              'recovery_resize_ioctl_verified': None, 'dm_offset_rechecked': None}
result = {'device': 'venus', 'serial': '55870427', 'kernel': command('uname -r'),
          'twrp_version': twrp, 'sys_boot_completed': booted, 'disk': disk, 'logical_block_bytes': sector,
          'disk_bytes': disk_bytes, 'userdata': user, 'userdata_raw': raw, 'userdata_bytes': raw_bytes,
          'mapped_data': mapped, 'mapped_bytes': mapped_bytes, 'entries': gpt.entries,
          'f2fs': fs, 'conditions': conditions, 'official_partition_plan_created': False,
          'device_write_performed': False, 'reference_revision': '16e592abee8a550dec8154ed1f38b5ebc4f16213',
          'snapshot': str(out), 'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()}}
(out / 'report.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
(root / 'ports/UniXNU-venus/evidence/dual-readonly.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'snapshot': str(out), 'logical_block_bytes': sector, 'userdata': user,
                  'f2fs': fs, 'conditions': conditions}, indent=2))
