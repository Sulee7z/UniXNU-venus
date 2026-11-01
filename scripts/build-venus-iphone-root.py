#!/usr/bin/env python3
"""Build the documented SHNGROOT media from the checked iPhone OS/SystemOS members."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path('/mnt/g/UniXNU-Port')
sys.path.insert(0,str(ROOT/'sources/UniXNU-guide/scripts'))
from unixnu import userdata
INPUT=ROOT/'artifacts/venus-iphone-inputs/20H392'
metadata=json.loads((INPUT/'report.json').read_text())
for component in ('OS','Cryptex1,SystemOS'):
    row=metadata['extracted'][component]
    with Path(row['path']).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256']


class PreparedIpsw:
    # Source-only adapter: the official builder gets exactly the recorded IPSW
    # members. No guest code or generated media structure is replaced.
    remote=True
    def __init__(self,ctx):
        assert metadata['target_product']=='iPhone10,3' and metadata['target_build']=='20H392'
    def extract(self,component):return Path(metadata['extracted'][component]['path'])


class Context:
    work=ROOT/'artifacts/venus-iphone-root/20H392'
    board={'userdata':{'partition':'unixnu','geometry_verified':True,
        'first_lba':44881664,'last_lba':61658879,'lba_bytes':4096,
        'windows':[{'name':'OS','component':'OS'},{'name':'SystemOS','component':'Cryptex1,SystemOS'}]}}


assert not (Context.work/'userdata/userdata-root.img').exists(),'Preserve an existing root build'
userdata.Ipsw=PreparedIpsw
image=userdata.build(Context())
print('Prepared iPhone root media:',image)
print('Phone operations: none; native iOS16 kernel, Data seed and driver ABI qualification still required.')
