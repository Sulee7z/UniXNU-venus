#!/usr/bin/env python3
"""Plan or capture the bounded Data store; offline extraction uses APFS EOF.

--read-android issues only identity/geometry checks and read-only dd commands.
It requires the separately confirmed Android/root read scope. Default: --plan.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
sys.path.insert(0,str(DEVICE/'scripts'))
import data_store_view as store


def on_g(path):
    path=Path(path).resolve()
    if sys.platform=='win32':
        if path.drive.upper()!='G:':raise ValueError('All host paths must be on G:')
    elif not path.is_relative_to(Path('/mnt/g')):
        raise ValueError('Use the G: mount')
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--plan',action='store_true')
    mode.add_argument('--read-android',action='store_true')
    mode.add_argument('--offline',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--serial',choices=('55870427',),default='55870427')
    parser.add_argument('--adb-port',choices=('5037','5038'),default='5037')
    parser.add_argument('--max-run-blocks',type=int,default=4096,help='Maximum4KiB blocks per dd')
    parser.add_argument('--max-bytes',type=int,default=512<<20)
    args=parser.parse_args()
    on_g(ROOT)
    if not 1<=args.max_run_blocks<=4096 or not 0<args.max_bytes<=8<<30:
        parser.error('Read bounds invalid')
    if args.offline:
        run=on_g(args.offline)
        output=on_g(args.output or run/'forensics-v2')
        return subprocess.call([sys.executable,'-B',str(DEVICE/'scripts/recheck-data-forensics.py'),
                                '--run',str(run),'--output',str(output)])
    packed=store.module(ROOT/'sources/UniXNU-guide/drivers/DarwinBoot/Test/packed_ramdisk.py','packed')
    seed,_=packed.inspect(ROOT/'artifacts/venus-deployment/Data.dbr')
    if seed['encoded_sha256']!=store.SEED_SHA or seed['bytes']!=8<<30:
        raise ValueError('Data seed changed')
    geometry={'seed_bytes':8<<30,'pages':2097152,'bitmap_blocks':64,
              'store_absolute_lba':[59299519,61396736],'partition_relative_skip_blocks':14417855,
              'metadata_blocks':65,'metadata_bytes':266240}
    if not args.read_android:
        print(json.dumps({'geometry':geometry,'max_chunk_bytes':args.max_run_blocks*4096,
                          'read_only':True,'phone_commands_executed':False},indent=2));return 0
    if sys.platform!='win32':parser.error('Capture uses the G:-hosted Windows ADB')
    out=ROOT/'artifacts/venus-data-forensics'
    if not out.is_dir():raise ValueError('Missing capture parent')
    run=on_g(args.output or out/datetime.now(timezone.utc).strftime('read-%Y%m%dT%H%M%SZ'))
    run.mkdir(exist_ok=False)
    env=dict(os.environ,HOME=str(ROOT/'home'),USERPROFILE=str(ROOT/'home'),
             ANDROID_USER_HOME=str(ROOT/'home/.android'),ANDROID_SDK_HOME=str(ROOT/'home'),
             APPDATA=str(ROOT/'home/AppData/Roaming'),LOCALAPPDATA=str(ROOT/'home/AppData/Local'),
             TEMP=str(ROOT/'tmp'),TMP=str(ROOT/'tmp'))
    commands=[]
    def adb(arguments,binary=False):
        cmd=[str(ROOT/'tools/platform-tools/adb.exe'),'-P',args.adb_port,'-s',args.serial,*arguments]
        result=subprocess.run(cmd,capture_output=True,timeout=180,env=env)
        commands.append({'command':cmd,'returncode':result.returncode,
                         'stderr':result.stderr.decode('utf-8','replace'),
                         'stdout':None if binary else result.stdout.decode('utf-8','replace')})
        (run/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
        result.check_returncode();return result.stdout
    for arguments,want in ((['shell','getprop','ro.product.device'],b'venus'),
                           (['shell','getprop','sys.boot_completed'],b'1'),
                           (['shell',"su -c 'blockdev --getsize64 /dev/block/by-name/unixnu'"],b'68719476736')):
        if adb(arguments).strip()!=want:raise ValueError('Device identity/geometry check failed')
    if b'uid=0(' not in adb(['shell',"su -c 'id'"]):raise ValueError('Root unavailable')
    def dd(skip,count):
        # Reject ranges outside the known store, including accidental sector-unit changes.
        first=geometry['partition_relative_skip_blocks'];end=first+2097217
        if skip<first or count<=0 or skip+count>end:raise ValueError('Out-of-range dd')
        data=adb(['exec-out',f"su -c 'dd if=/dev/block/by-name/unixnu bs=4096 skip={skip} count={count} 2>/dev/null'"],True)
        if len(data)!=count*4096:raise ValueError('Short capture read')
        return data
    meta=dd(geometry['partition_relative_skip_blocks'],65)
    (run/'metadata.bin').write_bytes(meta)
    bitmap=meta[4096:];present=sum(b.bit_count() for b in bitmap)
    index={'geometry':geometry,'metadata_sha256':hashlib.sha256(meta).hexdigest(),
           'present_pages':present,'generation':int.from_bytes(meta[56:60],'little'),
           'seed_sha256':seed['encoded_sha256'],'runs':[],'read_only':True,
           'phone_written':False,'phone_rebooted':False,'complete':False}
    store.check_metadata(meta,index,seed['sha256'])
    if present*4096+2*geometry['metadata_bytes']>args.max_bytes:
        raise ValueError('Capture including both metadata reads exceeds requested byte bound')
    page=0
    while page<geometry['pages']:
        if not bitmap[page>>3]&(1<<(page&7)):
            page+=1;continue
        first=page;page+=1
        while page<geometry['pages'] and page-first<args.max_run_blocks and bitmap[page>>3]&(1<<(page&7)):
            page+=1
        data=dd(geometry['partition_relative_skip_blocks']+65+first,page-first)
        name=f"run-{len(index['runs']):05d}.bin"
        (run/name).write_bytes(data)
        index['runs'].append({'file':name,'first_page':first,'blocks':page-first,'sha256':hashlib.sha256(data).hexdigest()})
        (run/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    after=dd(geometry['partition_relative_skip_blocks'],65)
    (run/'metadata-after.bin').write_bytes(after)
    if after!=meta:raise ValueError('Metadata changed during capture; do not treat as a stable snapshot')
    index.update(complete=True,metadata_stable=True,metadata_after_sha256=hashlib.sha256(after).hexdigest())
    (run/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'run':str(run),'present_pages':present,'runs':len(index['runs'])},indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
