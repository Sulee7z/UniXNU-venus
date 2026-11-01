#!/usr/bin/env python3
"""Verify the entire pinned zeta source snapshot by Git blob identity, without phone I/O."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import urllib.request

ROOT=Path('/mnt/g/UniXNU-Port')
REFERENCE=ROOT/'sources/UniXNU-zeta-none24smu'
REVISION='eb489285a1d9153872f00c93ebb519a269b249b5'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
out=args.output;out.mkdir(parents=True,exist_ok=False)
with urllib.request.urlopen(f'https://api.github.com/repos/none24smu/UniXNU-zeta/git/trees/{REVISION}?recursive=1',timeout=60) as response:
    tree=json.load(response)
assert not tree.get('truncated'), 'Incomplete source inventory'
records=[]
for entry in tree['tree']:
    if entry['type']!='blob':continue
    relative=PurePosixPath(entry['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    source=REFERENCE.joinpath(*relative.parts)
    data=source.read_bytes() if source.is_file() else None
    blob=lambda value:hashlib.sha1(b'blob '+str(len(value)).encode()+b'\0'+value).hexdigest()
    local_matches=data is not None and blob(data)==entry['sha']
    if not local_matches:
        with urllib.request.urlopen(f'https://raw.githubusercontent.com/none24smu/UniXNU-zeta/{REVISION}/{entry["path"]}',timeout=60) as response:data=response.read()
    assert blob(data)==entry['sha'] and len(data)==entry['size'], entry['path']
    destination=out/'sources'/Path(*relative.parts)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(data)
    records.append({'path':entry['path'],'git_blob':entry['sha'],'sha256':hashlib.sha256(data).hexdigest(),
                    'bytes':len(data),'local_reference_matched':local_matches})
report={'repository':'https://github.com/none24smu/UniXNU-zeta','revision':REVISION,
        'git_tree':tree['sha'],'files':records,'file_count':len(records),
        'local_reference_mismatches':[row['path'] for row in records if not row['local_reference_matched']],
        'verified':True,'phone_operations':False}
(out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print('Verified complete zeta snapshot:',len(records),'files; local mismatches:',len(report['local_reference_mismatches']))
