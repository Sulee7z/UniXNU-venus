#!/usr/bin/env python3
"""Re-extract existing captures using APFS EOF and validated page coverage."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import plistlib
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_store_view as store

ROOT = Path(__file__).resolve().parents[3]
PREFIX = '/private/var'
MG_FILES = {
    PREFIX+'/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist': 'MobileGestalt.plist',
    PREFIX+'/mobile/Library/Preferences/com.apple.MobileGestalt.plist': 'MobileGestalt-upper.plist',
    PREFIX+'/mobile/Library/Preferences/com.apple.mobilegestalt.plist': 'MobileGestalt-lower.plist',
    PREFIX+'/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist.venus-scale-011.bak': 'MobileGestalt-011-backup.plist',
    PREFIX+'/mobile/Library/Preferences/com.apple.MobileGestalt.plist.venus-scale-011.bak': 'MobileGestalt-upper-011-backup.plist',
    PREFIX+'/mobile/Library/Preferences/com.apple.mobilegestalt.plist.venus-scale-011.bak': 'MobileGestalt-lower-011-backup.plist',
    PREFIX+'/db/venus-scale-012/cache-0.plist': 'MobileGestalt-012-backup.plist',
    PREFIX+'/db/venus-scale-012/cache-1.plist': 'MobileGestalt-upper-012-backup.plist',
    PREFIX+'/db/venus-scale-012/cache-2.plist': 'MobileGestalt-lower-012-backup.plist',
}


def json_value(value):
    if isinstance(value, bytes): return {'type':'data','base64':base64.b64encode(value).decode()}
    if isinstance(value, dict): return {str(k):json_value(v) for k,v in value.items()}
    if isinstance(value, list): return [json_value(v) for v in value]
    if hasattr(value, 'isoformat'): return value.isoformat()
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # This tool must never silently replace the earlier flawed extraction.
    if args.output.exists(): parser.error('Choose a new evidence output directory')
    for path in (args.run, args.output):
        resolved = path.resolve()
        if sys.platform == 'win32':
            if resolved.drive.upper() != 'G:': parser.error('All files must be on G:')
        elif not resolved.is_relative_to(Path('/mnt/g')):
            parser.error('Use the G: mount for evidence')
    view, apfs, volume = store.open_volume(args.run, ROOT/'artifacts/venus-deployment/Data.dbr', ROOT)
    try:
        args.output.mkdir(parents=True)
        result = {'schema_version':2, 'run':str(args.run), 'volume_uuid':store.DATA_UUID,
            'volume_checkpoint_xid':volume.xid, 'metadata_sha256':store.sha(args.run/'metadata.bin'),
            'seed_sha256':store.SEED_SHA,'parser_sha256':store.sha(Path(store.__file__)),
            'captures':view.provenance,'files':{},'directories':{},
            'historical_capture_limit':'Legacy runs have metadata SHA and lengths but no capture-time per-run hashes or post-read metadata check. New per-run hashes record present host bytes only.',
            'boot_image_association':'Not established by the APFS checkpoint or filesystem timestamp alone'}
        for path, name in MG_FILES.items():
            try:
                info = store.file_info(apfs, volume, path)
                data = store.read_file(view, apfs, volume, path)
                (args.output/name).write_bytes(data)
                decoded = plistlib.loads(data)
                (args.output/(name+'.json')).write_text(json.dumps(json_value(decoded),indent=2)+'\n',encoding='utf-8')
                result['files'][path] = {'state':'parsed','info':info,'bytes':len(data),
                    'sha256':hashlib.sha256(data).hexdigest(),'keys':list(decoded),'output':name}
            except ValueError as error:
                result['files'][path] = {'state':'absent' if 'has 0 directory records' in str(error) else 'error','detail':str(error)}
        for path in ('/mobile/Library/Logs/CrashReporter','/root/Library/Logs/CrashReporter','/logs/CrashReporter',
                     '/db/diagnostics','/db/diagnostics/Persist','/db/diagnostics/timesync'):
            try:
                entries = store.list_directory(apfs, volume, path)
                result['directories'][path] = entries
                if 'CrashReporter' in path:
                    target = args.output/('crashes-'+path.split('/')[1]);target.mkdir(exist_ok=True)
                    for entry in entries:
                        if entry['kind']!='file' or not entry['name'].endswith('.ips'): continue
                        data = store.read_file(view,apfs,volume,path+'/'+entry['name'])
                        (target/entry['name']).write_bytes(data)
            except ValueError as error:
                result['directories'][path] = {'state':'absent' if 'has 0 directory records' in str(error) else 'error','detail':str(error)}
        # Single helper report: no repeated photographs or tracev3 guessing.
        for path,name in (('/tmp/venus-mg-query-008.json','MGQuery-008.json'),
                          ('/tmp/venus-mg-query-008.stderr','MGQuery-008.stderr'),
                          ('/tmp/venus-mg-query-009.json','MGQuery-009.json'),
                          ('/tmp/venus-mg-query-009.stderr','MGQuery-009.stderr'),
                          ('/tmp/venus-mg-query-009-launch.jsonl','MGQuery-009-launch.jsonl'),
                          ('/tmp/venus-scale-011.jsonl','ScaleRefresh-011.jsonl'),
                          ('/db/venus-scale-012/refresh.jsonl','ScaleRefresh-012.jsonl'),
                          ('/db/venus-st-017/startup.jsonl','TouchStartup-017.jsonl'),
                          ('/db/venus-st-018/startup.jsonl','TouchStartup-018.jsonl'),
                          ('/db/venus-st-019/startup.jsonl','TouchStartup-019.jsonl'),
                          ('/db/venus-st-020/startup.jsonl','TouchStartup-020.jsonl'),
                          ('/db/venus-st-021/startup.jsonl','TouchStartup-021.jsonl'),
                          ('/db/venus-st-022/startup.jsonl','TouchStartup-022.jsonl'),
                          ('/db/venus-st-023/startup.jsonl','TouchStartup-023.jsonl'),
                          ('/db/venus-st-024/startup.jsonl','TouchStartup-024.jsonl'),
                          ('/db/venus-st-025/startup.jsonl','TouchStartup-025.jsonl'),
                          ('/db/venus-st-026/startup.jsonl','TouchStartup-026.jsonl'),
                          ('/db/venus-st-027/startup.jsonl','TouchStartup-027.jsonl'),
                          ('/db/venus-st-028/startup.jsonl','TouchStartup-028.jsonl'),
                          ('/db/venus-st-029/startup.jsonl','TouchStartup-029.jsonl'),
                          ('/db/venus-st-030/startup.jsonl','TouchStartup-030.jsonl'),
                          ('/db/venus-st-031/startup.jsonl','TouchStartup-031.jsonl'),
                          ('/db/venus-st-032/startup.jsonl','TouchStartup-032.jsonl'),
                          ('/db/venus-metal-041/startup.json','MetalStartup-041.json'),
                          ('/db/venus-metal-040/native.jsonl','MetalNative-040.jsonl'),
                          ('/root/Library/Caches/com.apple.backboardd/venus-metal13/native.jsonl','MetalNative-040-root.jsonl'),
                          ('/mobile/Library/Caches/com.apple.backboardd/venus-metal13/native.jsonl','MetalNative-040-mobile.jsonl'),
                          ('/tmp/venus-metal13-native.jsonl','MetalNative-040-tmp.jsonl')):
            try:
                data=store.read_file(view,apfs,volume,path,limit=1<<20)
                (args.output/name).write_bytes(data)
                row={'state':'extracted','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
                if name.endswith('.json'):
                    try:
                        decoded=json.loads(data)
                        if name.startswith('MetalStartup-'):
                            fields=('gpu_power_stage','addon_stage','addon_status','metal_stage','metal_status','kext_status','gpu_done')
                            if decoded.get('schema')!=1 or decoded.get('sample')!='prelaunchd' or any(key not in decoded for key in fields):
                                raise ValueError('Wrong prelaunchd Metal report')
                            row.update(complete=True,report=decoded)
                        else:
                            if decoded.get('schema_version')!=1 or decoded.get('probe')!='venus-mg-query-v1':
                                raise ValueError('Wrong probe report')
                            row.update(complete=decoded.get('complete') is True,report=decoded)
                    except (ValueError,UnicodeDecodeError) as error:
                        row.update(complete=False,parse_error=str(error))
                if name.endswith('.jsonl'):
                    try:
                        events=[json.loads(line) for line in data.splitlines()]
                        if name.startswith('TouchStartup-'):
                            if len(events)!=1 or events[0].get('schema')!=1 or events[0].get('build') not in ('touch-017','touch-018','touch-019','touch-020','touch-021','touch-022','touch-023','touch-024','touch-025','touch-026','touch-027','touch-028','touch-029','touch-030','touch-031','touch-032') or events[0].get('sample')!='prelaunchd':
                                raise ValueError('Wrong startup touch sample')
                        elif name.startswith('MetalNative-'):
                            if not events or len(events)>128 or any(event.get('schema')!=1 or event.get('process')!='backboardd' or not event.get('stage') for event in events):
                                raise ValueError('Wrong native Metal diagnostic')
                        else:
                            expected_probe=('venus-scale-refresh-'+name[len('ScaleRefresh-'):len('ScaleRefresh-')+3]) if name.startswith('ScaleRefresh-') else 'venus-mg-task-v1'
                            if not events or any(event.get('probe')!=expected_probe for event in events):
                                raise ValueError('Wrong or empty task-launch journal')
                        row['events']=events
                    except (ValueError,UnicodeDecodeError) as error:row['parse_error']=str(error)
                result['files'][path]=row
            except ValueError as error:
                result['files'][path]={'state':'absent' if 'has 0 directory records' in str(error) else 'error','detail':str(error)}
        (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        for path,row in result['files'].items():
            print(path, row['state'], row.get('bytes',''), row.get('detail',''))
        print('Saved:',args.output/'report.json')
    finally:
        view.close()


if __name__ == '__main__': main()
