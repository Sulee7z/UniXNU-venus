#!/usr/bin/env python3
"""Keep010-tagged trace-file display contexts separate from full event parsing."""
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3];RUN=ROOT/'artifacts/venus-data-forensics/read-20261029T063818Z'
trace=json.loads((RUN/'mg-trace-chunks/report.json').read_text())
rows=[]
for name,row in trace['files'].items():
    tags=row['hits'].get('sheng-chain-010',[])
    if not tags:continue
    hits=row['hits'].get('FBSDisplayMode cannot be configured',[])
    modes=[]
    for hit in hits:
        match=re.search(r'FBSDisplayMode cannot be configured as requested\s*:\s*(<FBSDisplayMode:[^>]+>)',hit['context'])
        if match:modes.append({'mode':match[1],**hit})
    rows.append({'file':name,'sha256':row['sha256'],'decoded_bytes':row['decoded_bytes'],
                 'tag_context':tags,'display_rejection_contexts':modes})
result={'files_with_010_tag':rows,
        'scope':'Validated decoded string spans in the same trace file as010 boot args. Full event PID/timestamp/boot linkage is not parsed. Current PID-matched IPS is the primary crash attribution evidence.'}
destination=RUN/'sheng-chain-analysis/trace-context.json'
if destination.exists():raise ValueError('Preserve existing trace summary')
destination.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'files':[r['file'] for r in rows],
      'display_modes':sorted({m['mode'] for r in rows for m in r['display_rejection_contexts']}),
      'scope':result['scope'],'report':str(destination)},indent=2))
