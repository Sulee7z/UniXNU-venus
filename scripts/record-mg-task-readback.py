#!/usr/bin/env python3
"""Verify009 Data evidence without treating missing output or old logs as answers."""
import argparse
import ast
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
def need(ok,message):
    if not ok:raise ValueError(message)


def cstrings(source,name):
    body=re.search(r'\b'+re.escape(name)+r'\[\]\s*=\s*(.*?);',source,re.S)
    need(body is not None,'Missing policy string '+name)
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|//[^\n]*',body[1])
    return ''.join(ast.literal_eval(s) for s in tokens if s.startswith('"'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True);args=parser.parse_args()
    run=args.run.resolve()
    if sys.platform=='win32' and run.drive.upper()!='G:':parser.error('Use G:')
    if sys.platform!='win32' and not run.is_relative_to(Path('/mnt/g')):parser.error('Use G: mount')
    candidate=load(DEVICE/'evidence/mg-task-candidate.json');index=load(run/'index.json')
    need(index['complete'] and index['metadata_stable'],'Incomplete capture')
    need((run/'metadata.bin').read_bytes()==(run/'metadata-after.bin').read_bytes(),'Metadata changed')
    view,apfs,volume=store.open_volume(run,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT)
    try:
        installed={}
        for expected in candidate['installed_files']:
            path=expected['path'];data=store.read_file(view,apfs,volume,path)
            info=store.file_info(apfs,volume,path);inode=volume.lookup(store.volume_path(path))
            raw=volume.records(inode,apfs.TYPE_INODE)[0][1];uid,gid=struct.unpack_from('<II',raw,72)
            digest=hashlib.sha256(data).hexdigest()
            need(len(data)==expected['bytes'] and digest==expected['sha256'],'Installed file mismatch')
            installed[path]={'bytes':len(data),'sha256':digest,'mode':oct(info['mode']&0o7777),'uid':uid,'gid':gid}
        policy_path='/private/var/db/com.apple.xpc.launchd/disabled.plist'
        policy=store.read_file(view,apfs,volume,policy_path)
        source=(ROOT/'artifacts/venus-mg-query-009/activation-link-3/BootWatchdogPolicy.c').read_text()
        jobs=cstrings(source,'lite_jobs').split(',')
        expected=(cstrings(source,'policy_head')+''.join('<key>'+j+'</key><true/>' for j in jobs)+cstrings(source,'policy_tail')).encode()
        need(policy==expected,'009 kernel policy content differs')
        need(source.index('venus_mg_task_mount(p,scratch);')<source.index('policy[0]=0;'),'Hook ordering changed')
        previous=ROOT/'artifacts/venus-data-forensics/read-20261029T041826Z'
        old=store.DataView(previous,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT);old.close()
        log_path=run/'mg-launch-logs/log_com.apple.xpc.launchd_launchd.log'
        old_log=previous/'mg-launch-logs/log_com.apple.xpc.launchd_launchd.log'
        logs=load(run/'mg-launch-logs/report.json');old_logs=load(previous/'mg-launch-logs/report.json')
        same_logs=all(logs['files'][p]['sha256']==old_logs['files'][p]['sha256'] for p in logs['files'])
        extraction=load(run/'forensics-v2/report.json')
        outputs={p:extraction['files'][store.volume_path(p)] for p in candidate['output_paths']}
        need(all(row['state']=='absent' for row in outputs.values()),'Expected absent output changed')
        record={'schema_version':1,'date':'2026-10-29','device':'venus','serial':'55870427',
            'authorization':str(ROOT/'evidence/mg-query-009-r2-read-authorization.json'),
            'image_sha256':candidate['image_sha256'],'kernel_sha256':candidate['kernel_sha256'],
            'capture':{'run':str(run),'present_pages':index['present_pages'],'runs':len(index['runs']),
                'page_bytes':index['present_pages']*4096,'metadata_sha256':index['metadata_sha256'],
                'metadata_stable':True,'all_run_hashes_and_page_coverage_verified':True,
                'checkpoint_xid':volume.xid,'phone_written':False,'phone_rebooted':False},
            'installed_files':installed,'output_files':outputs,
            'kernel_policy':{'path':policy_path,'bytes':len(policy),'sha256':hashlib.sha256(policy).hexdigest(),
                'matches_009_kernel_source':True,'source_hook_precedes_policy_write':True,
                'differs_from_previous_1263B_binary_plist':True,
                'meaning':'Data installer ran and subsequent kernel policy write ran. MG mount helper returned or was skipped before this write; exact stage/status is not captured.'},
            'launchd_logs':{'all_four_files_identical_to_previous_008_capture':same_logs,
                'log_sha256':store.sha(log_path),'log_bytes':log_path.stat().st_size,
                'latest_recorded_tag':'mg-query-008','009_startup_evidence_found':False,
                'meaning':'Retained008 logs do not describe009. No claim that new launchd definitely never execed, or that mount definitely failed.'},
            'installation_verified':True,'task_union_verified':None,'wrapper_execution_verified':None,
            'actual_mg_api_result':None,'lockscreen_visible':None,
            'finding':'009 persisted all three exact0755 inputs and its kernel policy, but no task journal/API outputs and no new launchd log bytes.',
            'next_action':'Compare user-supplied official sheng startup chain and follow original post-Data/launchd sequence. If runtime localization is needed, persist kernel checkpoints before relying on a userspace journal.'}
    finally:view.close()
    destination=DEVICE/'evidence/mg-task-readback.json';destination.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    phone=load(DEVICE/'evidence/mg-task-phone.json')
    phone.update(installation_verified=True,readback_evidence=str(destination),actual_mg_api_result=None,
        pending='009 installation and kernel policy verified, but no journal/API report or new launchd log. Official sheng chain comparison in progress.',
        scope='One authorized boot and readonly capture. Exact Data files/policy observed; task union/exec/API/UI remain unverified.')
    (DEVICE/'evidence/mg-task-phone.json').write_text(json.dumps(phone,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'installed':installed,'policy_sha256':record['kernel_policy']['sha256'],
        'logs_unchanged':same_logs,'actual_mg_api_result':None,'evidence':str(destination)},indent=2))


if __name__=='__main__':main()
