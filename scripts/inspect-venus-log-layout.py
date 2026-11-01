#!/usr/bin/env python3
"""Audit the already compiled unixnu log reservation; never access the phone."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[1]
SOURCE = Path('/root/unixnu-build/venus-guide-out/venus/ipados-17.7.11-21H461/venus/tree/build/venus-ufs-root-unixnu/source/NativeUfs.cpp')
KERNEL = ROOT / 'artifacts/venus-hid-phone/kernel/kernel.macho'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


ufs = json.loads((ROOT / 'artifacts/venus-ufs-root-unixnu/venus-build.json').read_text())
layout = json.loads((ROOT / 'artifacts/venus-deployment/unixnu-root.json').read_text())
candidate = json.loads((ROOT / 'artifacts/venus-hid-phone/candidate.json').read_text())
assert sha(SOURCE)==ufs['native_ufs_source_sha256'], 'UFS source is not the compiled transport source'
assert ufs['root_boot'] and ufs['root_partition']=='unixnu'
assert sha(KERNEL)==candidate['kernel_sha256']
source = SOURCE.read_text()
def constant(name):
    return int(re.search(r'constexpr uint(?:32|64)_t '+name+r' = (\d+);',source)[1])
log_blocks = constant('kLogReserveBlocks')
export_blocks = constant('kExportBlocks')
reserve_blocks = constant('kDefaultReserveMiB') * 256
args = candidate['args'].split()
assert not any(a.startswith(('sheng-log=', 'sheng-log-reserve=')) for a in args)
first, end, block = 44881664, 61658880, 4096
assert (end-first)*block==layout['partition_bytes']
reserve_first = end-reserve_blocks
log_first = end-log_blocks
export_first = log_first-export_blocks
image_end = first+(layout['image_bytes']+block-1)//block
assert image_end+1024 <= reserve_first <= export_first < log_first < end
assert 'gStoreGeometry.last + 1 - reserve - blocks' in source
symbols = subprocess.check_output(['/usr/bin/llvm-nm',str(KERNEL)],text=True)
apis = {}
for name in ('_native_ufs_log_open','_native_ufs_log_write','_native_ufs_log_sync','_native_ufs_store_gpt_check'):
    matches = re.findall(r'^([0-9a-f]+)\s+\S\s+'+name+r'$',symbols,re.M)
    assert len(matches)==1 and int(matches[0],16)
    apis[name] = '0x'+matches[0]
report = {'device':'venus','date':'2026-10-28','partition':'unixnu','block_bytes':block,
    'partition_absolute_lba':[first,end], 'range_convention':'half-open [first,end)',
    'compiled_source_sha256':sha(SOURCE), 'kernel_sha256':sha(KERNEL), 'bounded_write_apis':apis,
    'root_image_end_absolute_lba':image_end,
    'existing_reserve':{'mib':reserve_blocks//256,'absolute_lba':[reserve_first,end]},
    'data_store_end_exclusive_lba':reserve_first,
    'export':{'bytes':export_blocks*block,'absolute_lba':[export_first,log_first]},
    'log':{'bytes':log_blocks*block,'absolute_lba':[log_first,end],
           'partition_relative_skip_blocks':log_first-first,'count_blocks':log_blocks},
    'writer_enabled_in_candidate':False, 'phone_read_or_write_performed':False,
    'finding':'The qualified UFS transport already reserves the last 1 GiB independently of logging; the last 32 MiB are its log window. Data ends below the reserve. The composite root image length alone is not a free-space allocation rule.',
    'remaining':['Connect a bounded log writer with boot ID, completion header and sync',
                 'Provide an exact-range reader and decoder, verify one manual cycle before automation'],
    'reader_command_template':f'dd if=/dev/block/by-name/unixnu bs=4096 skip={log_first-first} count={log_blocks}',
    'device_verification':'Requires actual layout/reader validation and specific operation authorization; these are host source/layout checks only'}
(DEVICE / 'evidence/log-layout-host.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
