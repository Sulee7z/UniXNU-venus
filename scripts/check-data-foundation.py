#!/usr/bin/env python3
"""Prepare the exact persistent-Data metadata range and optionally read it through Android.

Default is host-only. --read-android performs bounded read-only ADB/root commands:
identity, partition size, then the SHNGDATA header plus bitmap. It does not reboot,
flash, initialize the store, change the seed, or read user-file payload pages.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import zlib

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[1]
OUT = ROOT/'artifacts/venus-data-foundation'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--read-android', action='store_true')
options = parser.parse_args()
OUT.mkdir(parents=True, exist_ok=True)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def need(ok, message):
    if not ok:
        raise SystemExit(message)


seed_path = ROOT/'artifacts/venus-deployment/Data.dbr'
seed_record = json.loads((ROOT/'artifacts/venus-deployment/Data.json').read_text())
spec = importlib.util.spec_from_file_location('packed_data',ROOT/'sources/UniXNU-guide/drivers/DarwinBoot/Test/packed_ramdisk.py')
packed = importlib.util.module_from_spec(spec);spec.loader.exec_module(packed)
seed, _ = packed.inspect(seed_path)
need(seed['encoded_sha256']==seed_record['metadata']['encoded_sha256']==
     'ca732abdafa194ceb1d1ede1b20f930374180d238da6f74ebb00a2caa4c6fb33','Data seed changed')
need(seed['sha256']==seed_record['metadata']['sha256'] and seed['bytes']==8<<30,'Data logical identity differs')
layout = json.loads((DEVICE/'evidence/log-layout-host.json').read_text())
need(layout['partition']=='unixnu' and layout['block_bytes']==4096 and
     layout['partition_absolute_lba']==[44881664,61658880],'Unqualified partition geometry')
need(layout['existing_reserve']['mib']==1024,'Data store placement would change')
pages = seed['bytes']//4096
bitmap_blocks = (pages+32767)//32768
window_blocks = 1+bitmap_blocks+pages
store_end = layout['data_store_end_exclusive_lba']
store_first = store_end-window_blocks
relative = store_first-layout['partition_absolute_lba'][0]
need(store_first>=layout['root_image_end_absolute_lba']+1024 and relative>=0,'Store overlaps root/guard')
plan = {'device':'venus','serial':'55870427','partition':'unixnu','block_bytes':4096,
    'partition_bytes':68719476736,'seed':seed,'logical_pages':pages,
    'store_absolute_lba':[store_first,store_end], 'range_convention':'half-open',
    'metadata_read':{'skip_blocks':relative,'count_blocks':1+bitmap_blocks,'bytes':(1+bitmap_blocks)*4096},
    'read_only':True,'actual_write_reboot_readback_verified':False}
(OUT/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps(plan,indent=2))
if not options.read_android:
    raise SystemExit(0)

need(ROOT.drive.upper()=='G:', '--read-android uses the Windows platform-tools on G:')
adb = ROOT/'tools/platform-tools/adb.exe'
need(adb.is_file(),'ADB executable missing')
run_dir = OUT/datetime.now(timezone.utc).strftime('read-%Y%m%dT%H%M%SZ')
run_dir.mkdir(exist_ok=False)
commands = []
def adb_run(arguments, binary=False):
    command = [str(adb),'-P','5037','-s','55870427',*arguments]
    result = subprocess.run(command,capture_output=True,timeout=45)
    commands.append({'command':command,'returncode':result.returncode,
                     'stderr':result.stderr.decode('utf-8','replace'),
                     'stdout':None if binary else result.stdout.decode('utf-8','replace')})
    (run_dir/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    need(result.returncode==0,'Android read command failed; inspect '+str(run_dir/'commands.json'))
    return result.stdout

need(adb_run(['shell','getprop','ro.product.device']).strip()==b'venus','Wrong connected device')
need(adb_run(['shell','getprop','sys.boot_completed']).strip()==b'1','Android boot not complete')
need(b'uid=0(' in adb_run(['shell',"su -c 'id'"]),'Root read access is unavailable')
size = adb_run(['shell',"su -c 'blockdev --getsize64 /dev/block/by-name/unixnu'"]).strip()
need(size==b'68719476736','Unexpected unixnu partition size')
# exec-out can merge the remote stderr into its byte stream. Keep dd's transfer
# statistics out of the metadata; exact byte count and header CRC remain gates.
command = f"su -c 'dd if=/dev/block/by-name/unixnu bs=4096 skip={relative} count={1+bitmap_blocks} 2>/dev/null'"
data = adb_run(['exec-out',command],binary=True)
(run_dir/'data-metadata.bin').write_bytes(data)
need(len(data)==plan['metadata_read']['bytes'],
     f"Metadata length mismatch: got {len(data)}, expected {plan['metadata_read']['bytes']}")
magic,version,header_bytes,n = struct.unpack_from('<8sIIQ',data)
checks = {'magic':magic==b'SHNGDATA','version':version==1,'header_bytes':header_bytes==64,
          'page_count':n==pages,'seed_identity':data[24:56].hex()==seed['sha256'],
          'header_crc':struct.unpack_from('<I',data,60)[0]==zlib.crc32(data[:60])}
bitmap = data[4096:]
present = sum(b.bit_count() for b in bitmap)
checks['bitmap_bounds'] = all(not (bitmap[i//8]&(1<<(i%8))) for i in range(pages,len(bitmap)*8))
result = {'plan':plan,'checks':checks,'metadata_sha256':hashlib.sha256(data).hexdigest(),
    'generation':struct.unpack_from('<I',data,56)[0], 'present_pages':present,
    'actual_phone_metadata_read':True,'phone_written':False,'phone_rebooted':False,
    'write_reboot_readback_test_passed':False,
    'scope':'Valid persisted metadata with the expected seed is evidence of an existing store, not a controlled known-file write/reboot/readback qualification.'}
(run_dir/'result.json').write_text(json.dumps(result,indent=2)+'\n')
(DEVICE/'evidence/data-metadata-read.json').write_text(json.dumps(result,indent=2)+'\n')
need(all(checks.values()),'Data metadata validation failed; retain bytes and inspect before any write')
print('PASS: exact-range Data metadata read, matching seed/header CRC/page count; present pages:',present)
