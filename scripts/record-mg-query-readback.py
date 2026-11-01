#!/usr/bin/env python3
"""Verify and record the captured008 installation/no-report result, host-only."""
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
sys.path.insert(0,str(DEVICE/'scripts'))
import data_store_view as store

RUN=ROOT/'artifacts/venus-data-forensics/read-20261029T041826Z'
CACHE=ROOT/'artifacts/venus-mg-query-008/launch-cache-inspection-v2'


def load(path):return json.loads(path.read_text(encoding='utf-8'))
def need(ok,why):
    if not ok:raise ValueError(why)


def main():
    candidate=load(DEVICE/'evidence/mg-query-candidate.json');index=load(RUN/'index.json')
    view,apfs,volume=store.open_volume(RUN,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT)
    try:
        modes={r['path']:oct(store.file_info(apfs,volume,r['path'])['mode']&0o7777)
               for r in candidate['installed_files']}
        need(all(int(modes[r['path']],8)==int(r['mode'],8) for r in candidate['installed_files']),
             'Installed modes differ')
        directory_modes={p:oct(store.file_info(apfs,volume,p)['mode']&0o7777)
                         for p in ('/ngpu','/ngpu/bin','/ngpu/daemons','/tmp')}
    finally:view.close()
    need(index['complete'] and index['metadata_stable'],'Incomplete/unstable capture')
    need((RUN/'metadata.bin').read_bytes()==(RUN/'metadata-after.bin').read_bytes(),'Metadata changed')
    extraction=load(RUN/'forensics-v2/report.json');installation=load(RUN/'mg-installation/report.json')
    need(all(installation['files'][r['path']]['matches_payload'] for r in candidate['installed_files']),'Installed inputs differ')
    for row in candidate['installed_files']:
        file=RUN/'mg-installation'/row['path'].rsplit('/',1)[1]
        need(file.stat().st_size==row['bytes'] and store.sha(file)==row['sha256'],'Extracted installation changed')
    need(all(extraction['files']['/tmp/venus-mg-query-008.'+ext]['state']=='absent'
             for ext in ('json','stderr')),'Expected no-report result changed')
    launch=RUN/'mg-launch-logs/log_com.apple.xpc.launchd_launchd.log';text=launch.read_text()
    boot_args=re.findall(r'boot-args = (.*)',text)
    need(boot_args==[candidate['args']],'Not the008 launch record')
    need('Early boot complete. Continuing system boot.' in text,'Early boot incomplete')
    need('Successfully spawned SpringBoard[27]' in text,'Missing SpringBoard startup record')
    summary=load(CACHE/'cache-summary.json')
    need(summary['job_count']==561 and not summary['candidate_queries'][
        '/System/Library/LaunchDaemons/org.blu-sharky.adrenoprobed.plist']['present'],'Launch cache changed')
    trace=load(RUN/'mg-trace-chunks/report.json')
    need(not any('preamble_error' in r or any('decode_error' in c for c in r['chunks'])
                 for r in trace['files'].values()),'Trace decoding incomplete')
    record={'schema_version':1,'date':'2026-10-29','device':'venus','serial':'55870427',
        'authorization':str(ROOT/'evidence/mg-query-008-read-authorization.json'),
        'capture':{'path':str(RUN),'present_pages':index['present_pages'],'page_bytes':index['present_pages']*4096,
                   'runs':len(index['runs']),'generation':index['generation'],
                   'metadata_sha256':index['metadata_sha256'],'metadata_stable':True,
                   'all_run_hashes_verified':True,'complete_page_coverage_verified':True,
                   'checkpoint_xid':extraction['volume_checkpoint_xid'],
                   'phone_written':False,'phone_rebooted':False},
        'installed_files':{r['path']:{**installation['files'][r['path']],'verified_mode':modes[r['path']]}
                           for r in candidate['installed_files']},'directory_modes':directory_modes,
        'query_output':{p:extraction['files'][p] for p in ('/tmp/venus-mg-query-008.json','/tmp/venus-mg-query-008.stderr')},
        'launchd':{'log':str(launch),'log_sha256':store.sha(launch),'args_match_candidate':True,
                   'early_boot_completed':True,'springboard_spawned_pid':27,
                   'query_name_present_in_log':any(s in text for s in ('venus-mg-query','adrenoprobed','ngpu/')),
                   'association':'Complete boot args include mg-query-008 and match the authorized candidate. Log has no embedded image SHA or kern.bootsessionuuid.'},
        'launch_cache':{'directory':str(CACHE),'jobs':561,
                        'new_query_path_present':False,'full_fdr_definition_cached':True,
                        'cache_summary_sha256':store.sha(CACHE/'cache-summary.json')},
        'trace':{'directory':str(RUN/'mg-trace-chunks'),'files':len(trace['files']),
                  'decoded_bytes':sum(r['decoded_bytes'] for r in trace['files'].values()),
                  'framing_and_decode_errors':0,'event_attribution_verified':False},
        'actual_mg_api_result':None,'helper_execution_verified':False,'daemon_union_mount_status':None,
        'finding':'The installer persisted both exact files; no JSON/stderr measurement.008 launchd reached normal bootstrap and uses signed cached service definitions. New query is absent from cache.',
        'hypothesis':'Directory-only insertion did not activate the uncached service. Union mount stage and exact lookup/refusal branch were not captured.',
        'next_action':'Verify an explicit one-shot execution path compatible with this launchd/cache before any new exact-image phone test. Renaming an overlay plist to a cached service is insufficient evidence because cache includes its original ProgramArguments.'}
    destination=DEVICE/'evidence/mg-query-readback.json'
    destination.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    phone=load(DEVICE/'evidence/mg-query-phone.json')
    phone.update(observed='Exact installation persisted; no query output; normal launchd bootstrap observed in matching008 args log.',
                 readback_evidence=str(destination),installation_verified=True,query_output_present=False,
                 query_helper_started=None,actual_mg_api_result=None,
                 pending='Explicit task activation must be host-qualified;008 measurement failed at integration, not a measured zero answer.',
                 scope='One authorized RAM boot and one authorized readonly Data capture. Installation and normal launchd bootstrap verified; query execution/API/lockscreen unverified.')
    (DEVICE/'evidence/mg-query-phone.json').write_text(json.dumps(phone,indent=2)+'\n',encoding='utf-8')
    print('Recorded:',destination)


if __name__=='__main__':main()
