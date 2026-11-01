#!/usr/bin/env python3
"""Bind010 launchd logs and real SpringBoard IPS reports to observed failures."""
import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
sys.path.insert(0,str(DEVICE/'scripts'))
import data_store_view as store


def load(p):return json.loads(p.read_text(encoding='utf-8'))
def need(ok,why):
    if not ok:raise ValueError(why)


def ips_objects(text):
    decoder=json.JSONDecoder();objects=[];at=0
    while at<len(text):
        if text[at].isspace():at+=1;continue
        obj,end=decoder.raw_decode(text,at);objects.append(obj);at=end
    need(len(objects)==2 and all(isinstance(o,dict) for o in objects),'Expected IPS header and body')
    return objects


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True);args=parser.parse_args()
    run=args.run.resolve()
    if sys.platform=='win32' and run.drive.upper()!='G:':parser.error('Use G:')
    if sys.platform!='win32' and not run.is_relative_to(Path('/mnt/g')):parser.error('Use G: mount')
    out=run/'sheng-chain-analysis';out.mkdir(exist_ok=False)
    candidate=load(DEVICE/'evidence/sheng-chain-control-candidate.json');index=load(run/'index.json')
    need(index['complete'] and index['metadata_stable'],'Incomplete capture')
    need((run/'metadata.bin').read_bytes()==(run/'metadata-after.bin').read_bytes(),'Metadata changed')
    view,apfs,volume=store.open_volume(run,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT)
    try:
        policy=store.read_file(view,apfs,volume,'/db/com.apple.xpc.launchd/disabled.plist')
        import plistlib
        decoded=plistlib.loads(policy);need(decoded.get('com.apple.watchdogd') is True,'Watchdog policy did not persist')
        mg=store.read_file(view,apfs,volume,'/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist')
        mg_sha=hashlib.sha256(mg).hexdigest()
        checkpoint=volume.xid
    finally:view.close()
    log=run/'mg-launch-logs/log_com.apple.xpc.launchd_launchd.log';lines=log.read_text().splitlines();text='\n'.join(lines)
    need(re.findall(r'boot-args = (.*)',text)==[candidate['args']],'Not the exact010 boot-args log')
    need('Early boot complete. Continuing system boot.' in text,'No early-boot completion')
    events=[];exits=Counter();sb_by_pid={}
    for i,line in enumerate(lines,1):
        match=re.search(r'\(([^)]+?) \[(\d+)\]\).*exited (.*)',line)
        if not match:continue
        service,pid,reason=match.groups();name=service.rsplit('/',1)[1];exits[name]+=1
        row={'line':i,'pid':int(pid),'reason':reason,'text':line}
        if name=='com.apple.SpringBoard':events.append(row);sb_by_pid[int(pid)]=row
    reports=[]
    for path in sorted((run/'forensics-v2/crashes-mobile').glob('SpringBoard*.ips')):
        header,body=ips_objects(path.read_text());pid=body['pid']
        need(header['incident_id']==body['incident'],'IPS incident mismatch')
        need(body['procName']=='SpringBoard' and body['osVersion']['build']=='21H461','Wrong crash process/build')
        need(pid in sb_by_pid and body['exception']['signal']=='SIGTRAP','No matching010 SIGTRAP exit')
        thread=body['threads'][body['faultingThread']];frame=thread['frames'][0]
        image=body['usedImages'][frame['imageIndex']];pc=thread['threadState']['pc']['value']
        need(pc==image['base']+frame['imageOffset'],'Crash PC/image mapping differs')
        need(image['uuid'].lower()=='81ef9aac-02b7-30f1-8181-bb60a5115835' and frame['imageOffset']==63300,'Not the known exact FBS validation frame')
        instructions=base64.b64decode(body['instructionByteStream']['atPC'],validate=True)
        need(struct.unpack_from('<I',instructions)[0]==0xd4200000,'Crash instruction is not BRK0')
        row={'file':str(path),'sha256':store.sha(path),'pid':pid,'incident':body['incident'],
            'header_timestamp':header['timestamp'],'capture_time':body['captureTime'],
            'proc_launch':body['procLaunch'],'proc_start_abs_time':body['procStartAbsTime'],
            'proc_exit_abs_time':body['procExitAbsTime'],'reported_uptime':body['uptime'],
            'exception':body['exception'],'termination':body['termination'],
            'pc':hex(pc),'image_uuid':image['uuid'],'image_path':image['path'],
            'image_offset':hex(frame['imageOffset']),'symbol':frame['symbol'],'symbol_location':frame['symbolLocation'],
            'instruction':'BRK #0','matched_log_exit':sb_by_pid[pid],
            'frames':[{'symbol':f.get('symbol'), 'image':body['usedImages'][f['imageIndex']].get('path'),
                       'image_offset':hex(f['imageOffset'])} for f in thread['frames']],
            'application_specific':{k:v for k,v in body.items() if k in ('asi','applicationSpecificInformation','faultingThread','lastExceptionBacktrace')},
            'shared_cache':body.get('sharedCache'),'body_keys':list(body)}
        reports.append(row)
    need(reports,'No SpringBoard report parsed')
    record={'schema_version':1,'date':'2026-10-29','device':'venus','serial':'55870427',
        'image_sha256':candidate['image_sha256'],'kernel_sha256':candidate['kernel_sha256'],
        'read_authorization':str(ROOT/'evidence/sheng-chain-010-read-authorization.json'),
        'capture':{'run':str(run),'present_pages':index['present_pages'],'runs':len(index['runs']),
             'page_bytes':index['present_pages']*4096,'metadata_sha256':index['metadata_sha256'],
             'metadata_stable':True,'all_run_hashes_and_page_coverage_verified':True,'checkpoint_xid':checkpoint,
             'phone_written':False,'phone_rebooted':False},
        'launchd':{'log_sha256':store.sha(log),'bytes':log.stat().st_size,'lines':len(lines),
             'args_match_010':True,'early_boot_complete':True,'first_line':lines[0],'last_line':lines[-1],
             'association':'Exact complete010 boot args plus PID-matched IPS reports; file names and wall clocks alone are not used.'},
        'watchdog_policy':{'watchdogd_disabled':True,'bytes':len(policy),'sha256':hashlib.sha256(policy).hexdigest(),
             'watchdogd_exit_events_in_this_log':exits.get('com.apple.watchdogd',0)},
        'springboard':{'exit_events':events,'sigtrap_count':sum('SIGTRAP' in e['reason'] for e in events),
             'ips_reports':reports,'ips_count':len(reports),'same_fbs_brk_offset_all_reports':True},
        'other_exit_counts':dict(exits.most_common(20)),
        'mg_cache':{'bytes':len(mg),'sha256':mg_sha,'unchanged_from_prior':mg_sha=='661cdb8356befb18dae67ecb839db8d228b513482437db2c820fed68755f16a7'},
        'actual_mg_api_result':None,'ui_success_verified':False,
        'finding':'010 normal userspace startup is observed and watchdogd disabled. System keeps logging while SpringBoard repeatedly traps in exact FBS display-mode validation; this is not a successful UI.',
        'next_action':'Use actual IPS stack and current display failure evidence to isolate preferredScale/cache/calculation. Do not keep replacing the now-observed normal startup chain.'}
    (out/'report.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    (DEVICE/'evidence/sheng-chain-control-readback.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'snapshot_pages':index['present_pages'],'log_last_line':lines[-1],
         'watchdogd_disabled':True,'springboard_sigtrap_events':record['springboard']['sigtrap_count'],
         'crashes':[{'pid':r['pid'],'capture_time':r['capture_time'],'pc':r['pc'],'symbol':r['symbol'],
                    'frames':[f['symbol'] for f in r['frames']]} for r in reports],
         'other_exit_counts':record['other_exit_counts'],'MG_cache_unchanged':record['mg_cache']['unchanged_from_prior'],
         'report':str(out/'report.json')},indent=2))


if __name__=='__main__':main()
