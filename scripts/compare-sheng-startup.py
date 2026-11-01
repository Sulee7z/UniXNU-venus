#!/usr/bin/env python3
"""Compare official pinned startup policy and the phone-qualified Venus chain."""
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import tomllib

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
REF=ROOT/'references/sheng-startup/08cde20edc3254ed6f7df8d0f5384fb887786e8f'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
receipt=json.loads((REF/'receipt.json').read_text())
for name,row in receipt['files'].items():
    if sha(REF/name)!=row['sha256']:raise ValueError('Reference changed: '+name)
upstream=(REF/'package/BootWatchdogPolicy.c').read_text()
retained=(ROOT/'artifacts/venus-data-check-002/linked-inputs/BootWatchdogPolicy.c').read_text()
normalized=retained.replace('#include "BootDataCheck.h"\n','').replace('  venus_boot_data_check(p,scratch);\n','')
if re.sub(r'\s+','',normalized)!=re.sub(r'\s+','',upstream):raise ValueError('Policy has unexplained differences')
board=tomllib.loads((REF/'board.toml').read_text());venus=tomllib.loads((DEVICE/'board.toml').read_text())
kernel=ROOT/'artifacts/venus-mg-query-008/kernel/kernel.macho';blob=kernel.read_bytes()
if sha(kernel)!='4b1ae1c0bc6ea2b7dbb440099ef5c0a0c413d26aab8bfe304f1fbc8b1a2760be':raise ValueError('Qualified kernel changed')
flags=['kt_fixed_zones=120','sheng-disable-watchdogd=1','ml-timeout-lock-panic-scale=40','boot-ui-focus4=SpringBoard']
support={flag:flag.split('=')[0].encode() in blob for flag in flags}
source=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root/tree/.cache/xnu-work/bsd/kern/kern_exec.c')
chain=source.read_text()
begin=chain.index('load_init_program(proc_t p)');end=chain.index('\n/*',begin)
part=chain[begin:end]
positions={name:part.index(name) for name in ('native_owner_cache_prepare','native_owner_data_prepare','sheng_boot_watchdog_policy','load_init_program_at_path')}
if list(positions.values())!=sorted(positions.values()):raise ValueError('Unexpected init ordering')
result={'repo':receipt['repo'],'revision':receipt['revision'],'files_verified':len(receipt['files']),
    'policy_equal_except_venus_data_qualification_hook':True,'kernel_sha256':sha(kernel),
    'shared_init_order':list(positions),'kernel_current_source_sha256':sha(source),
    'original_init_path':'/sbin/launchd','candidate_flag_presence':support,
    'upstream_boot_args':board['payload']['kernel_args'],
    'venus_missing_common_args':[flag for flag in flags if flag not in venus['payload']['kernel_args']],
    'board_scope':{'reference_soc':'SM8550','venus_soc':'SM8350','reference_data_uuid':'18AB5557-DC2D-469B-8758-855E60F5B0DF',
        'venus_data_uuid':'FCC1EC83-9500-4D4D-AEED-6004A520B3C0','same_os_profile':board['board']['os_profile']==venus['board']['os_profile']},
    'decision':'Reuse normal shared init order and original watchdog policy. Prepare a qualified4b1 control with only supported generic original boot policies; board resource/GPU/SMP/storage and log writer require separate adaptation.',
    'limits':'Current source order is not an embedded image SHA proof.4b1 userland startup already has matching008 device log evidence. Presence of a boot-arg name alone does not establish every optional hook is active.'}
(DEVICE/'evidence/sheng-startup-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('revision','files_verified','policy_equal_except_venus_data_qualification_hook','shared_init_order','candidate_flag_presence','decision')},indent=2))
