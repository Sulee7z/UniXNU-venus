"""Read-only ADB boot/sysfs checks after the authorized Android reset."""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import re
import subprocess

root = Path('G:/UniXNU-Port')
device = root / 'ports/UniXNU-venus'
adb = [str(root/'tools/platform-tools/adb.exe'), '-P', '5037', '-s', '55870427']
commands = []
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--boot-only', action='store_true', help='Capture boot and block paths when shell cannot read protected sysfs geometry')
args = parser.parse_args()
def shell(text):
    result = subprocess.run([*adb, 'shell', text], capture_output=True, timeout=20)
    output = result.stdout.decode('utf-8', 'strict').strip()
    commands.append({'command': text, 'returncode': result.returncode, 'stdout': output,
                     'stderr': result.stderr.decode('utf-8', 'replace').strip()})
    if result.returncode: raise RuntimeError('Read-only Android query failed: ' + text)
    return output
plan = json.loads((root/'artifacts/venus-deployment/partition-preview.json').read_text())
result = {'serial': '55870427', 'read_only': True, 'commands': commands,
          'observed_at': datetime.now(timezone.utc).isoformat()}
try:
    result['device'] = shell('getprop ro.product.device')
    result['boot_completed'] = shell('getprop sys.boot_completed')
    result['slot_suffix'] = shell('getprop ro.boot.slot_suffix')
    result['android_version'] = shell('getprop ro.build.version.release')
    result['kernel'] = shell('uname -r')
    if result['device'] != 'venus' or result['boot_completed'] != '1':
        raise RuntimeError('Expected Venus with Android boot completed')
    result['partitions'] = {}
    for name, start, size in [('userdata', plan['userdata_start'], plan['new_userdata_bytes']),
                              ('unixnu', plan['unixnu_start'], plan['unixnu_bytes'])]:
        path = shell('readlink -f /dev/block/by-name/' + name)
        if not re.fullmatch(r'/dev/block/[a-zA-Z0-9_-]+', path):
            raise RuntimeError('Unexpected block-device path')
        node = path.rsplit('/', 1)[1]
        if args.boot_only:
            result['partitions'][name] = {'path': path, 'geometry_verified': False}
            continue
        blocks = int(shell(f'cat /sys/class/block/{node}/size'))
        first = int(shell(f'cat /sys/class/block/{node}/start'))
        events = dict(line.split('=', 1) for line in shell(f'cat /sys/class/block/{node}/uevent').splitlines() if '=' in line)
        # Linux sysfs size/start always use 512-byte units, including on 4K UFS.
        if blocks * 512 != size or first * 512 != start * plan['sector_bytes'] or events.get('PARTNAME') != name:
            raise RuntimeError('Post-reset partition geometry differs: ' + name)
        if name == 'unixnu' and events.get('PARTUUID', '').lower() != plan['unixnu_guid'].lower():
            raise RuntimeError('unixnu GUID differs from the applied plan')
        result['partitions'][name] = {'path': path, 'bytes': blocks * 512, 'start_bytes': first * 512, 'uevent': events}
    mounts = shell('cat /proc/mounts')
    data = [line for line in mounts.splitlines() if len(line.split()) >= 4 and line.split()[1] == '/data']
    if len(data) != 1 or data[0].split()[2] != 'f2fs':
        raise RuntimeError('Android /data is not the expected mounted F2FS')
    result['data_mount'] = data[0]
    result['android_boot_verified'] = True
    result['android_and_64g_partition_verified'] = not args.boot_only
    result['geometry_verification_pending_fastboot'] = args.boot_only
except Exception as error:
    result['android_and_64g_partition_verified'] = False
    result['error'] = str(error)
    raise
finally:
    (device/'evidence/android-reinitialized.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k != 'commands'}, indent=2))
