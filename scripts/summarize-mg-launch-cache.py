#!/usr/bin/env python3
"""Summarize already extracted launchd config/cache; never modify either."""
import argparse
import json
from pathlib import Path
import plistlib
import struct
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory',type=Path,required=True)
args=parser.parse_args();directory=args.directory.resolve()
if sys.platform=='win32' and directory.drive.upper()!='G:':parser.error('Use G:')
if sys.platform!='win32' and not directory.is_relative_to(Path('/mnt/g')):parser.error('Use G: mount')
output=directory/'cache-summary.json'
if output.exists():parser.error('Preserve existing summary')
cache=plistlib.loads((directory/'System_Library_xpc_launchd.plist').read_bytes())
jobs=cache['LaunchDaemons']
result={'cache_top_keys':list(cache),'jobs_type':type(jobs).__name__,'job_count':len(jobs),
        'candidate_queries':{},'config_sections':[]}
for path in ('/System/Library/LaunchDaemons/org.blu-sharky.adrenoprobed.plist',
             '/System/Library/LaunchDaemons/org.unixnu.venus.mg-query.plist',
             '/System/Library/LaunchDaemons/com.apple.iomfb_fdr_loader.plist'):
    result['candidate_queries'][path]={'present':path in jobs,'entry':jobs.get(path)} if isinstance(jobs,dict) else {'present':path in jobs}
blob=(directory/'sbin_launchd').read_bytes()
if struct.unpack_from('<I',blob)[0]!=0xfeedfacf:raise ValueError('Not64-bit Mach-O')
ncmds,sizeofcmds=struct.unpack_from('<II',blob,16);at=32
if at+sizeofcmds>len(blob):raise ValueError('Load commands exceed file')
for _ in range(ncmds):
    cmd,size=struct.unpack_from('<II',blob,at)
    if size<8 or at+size>32+sizeofcmds:raise ValueError('Bad load command')
    if cmd==0x19:
        count=struct.unpack_from('<I',blob,at+64)[0]
        if 72+count*80>size:raise ValueError('Bad segment sections')
        for i in range(count):
            section=at+72+i*80
            name=blob[section:section+16].split(b'\0')[0]
            if name==b'__config':
                length=struct.unpack_from('<Q',blob,section+40)[0];offset=struct.unpack_from('<I',blob,section+48)[0]
                if offset+length>len(blob):raise ValueError('Section exceeds EOF')
                data=blob[offset:offset+length].rstrip(b'\0')
                result['config_sections'].append({'offset':offset,'bytes':length,'plist':plistlib.loads(data)})
    at+=size
if at!=32+sizeofcmds:raise ValueError('Load command size mismatch')
output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
