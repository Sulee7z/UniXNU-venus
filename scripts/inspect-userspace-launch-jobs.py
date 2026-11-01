#!/usr/bin/env python3
"""Read display/watchdog launch jobs from the deployed OS image on the host."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import re
import struct
import subprocess
import uuid
import zlib

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
OUT=ROOT/'artifacts/venus-userspace-001/launch-jobs';OUT.mkdir(exist_ok=True)
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def need(ok,why):
    if not ok:raise ValueError(why)
metadata=json.loads((ROOT/'artifacts/venus-deployment/OS-source.json').read_text())
raw=Path(metadata['raw']);reader=ROOT/'sources/UniXNU-zeta-reference/scripts/zeta_apfs_image.py'
need(sha(raw)==metadata['raw_sha256'],'Deployed OS input changed')
need(sha(reader)==metadata['apfs_reader_source_sha256'],'APFS reader changed')
spec=importlib.util.spec_from_file_location('apfs_readonly',reader)
apfs=importlib.util.module_from_spec(spec);spec.loader.exec_module(apfs)
helpers=DEVICE/'scripts/symbolicate-venus-fault.py'
# Reuse only the previously reviewed reader definitions; skip that command's
# argument parser, dyld scans and subprocess main. Record the exact source hash.
syntax=ast.parse(helpers.read_text())
names={'catalog_node','sealed_records','sealed_extents','lzfse_decode','decode_fork','File'}
definitions=[node for node in syntax.body if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names]
need({n.name for n in definitions}==names,'APFS helper definitions changed')
found={}
programs=set()
def program_strings(data):
    strings=[s.decode('ascii') for s in re.findall(rb'[\x20-\x7e]{5,}',data)]
    return [s for s in strings if re.search('FDR|IOMFB|Framebuffer|fail|error|calibr|wait|Usage',s,re.I)]
with raw.open('rb') as stream:
    container=apfs.Container(stream,metadata['container_offset'])
    volumes=list(container.volumes());need(len(volumes)==1,'Ambiguous OS volume')
    volume=volumes[0]
    need(str(uuid.UUID(bytes=volume.superblock[0xf0:0x100])).upper()==metadata['volumes'][0]['volume_uuid'],'OS volume mismatch')
    context={'container':container,'volume':volume,'struct':struct,'zlib':zlib,'OUT':OUT,
             'subprocess':subprocess,'apfs':apfs,'need':need}
    exec(compile(ast.Module(body=definitions,type_ignores=[]),str(helpers),'exec'),context)
    if volume.incompatible & 0x20:
        volume.records=lambda oid,kind:context['sealed_records'](oid,kind,volume.root_tree)
        volume.stream_extents=context['sealed_extents']
    for directory in ('/System/Library/LaunchDaemons','/usr/libexec'):
        inode=volume.lookup(directory);context['directory']=directory
        entries=volume.records(inode,apfs.TYPE_DIR_REC)
        need(len(entries)<10000,'Unexpected directory size')
        for key,_ in entries:
            length=struct.unpack_from('<I',key,8)[0]&0x3ff
            name=key[12:12+length].rstrip(b'\0').decode()
            if not any(s in name.lower() for s in ('iomfb','watchdog')):continue
            record={'path':directory+'/'+name}
            try:
                attrs=volume.xattrs(volume.lookup(record['path']))
                compression=attrs.get('com.apple.decmpfs')
                header=compression[1] if compression else b''
                if len(header)>=17 and struct.unpack_from('<I',header,4)[0]==9:
                    # decmpfs9 is uncompressed inline data following markerCC.
                    # Require both the marker and exact declared length.
                    magic,kind,size=struct.unpack_from('<4sIQ',header)
                    need(magic==b'fpmc' and header[16]==0xcc and len(header)-17==size,'Invalid inline plain decmpfs')
                    data=header[17:];record['decmpfs_type']=kind
                else:
                    file=context['File'](name)
                    need(file.extent_bytes<=4*1024*1024,'File exceeds this bounded inspection')
                    data=file.read(0,file.extent_bytes)
                destination=OUT/name;destination.write_bytes(data)
                record.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
                if name.endswith('.plist'):
                    job=plistlib.loads(data)
                    record['job']={k:job[k] for k in ('Label','Program','ProgramArguments','RunAtLoad','KeepAlive',
                        'LaunchEvents','MachServices','ProcessType','ThrottleInterval','ExitTimeOut') if k in job}
                    program=job.get('Program') or (job.get('ProgramArguments') or [None])[0]
                    if program and program.startswith('/'):programs.add(program)
                else:
                    record['relevant_strings']=program_strings(data)
            except (ValueError,KeyError,zlib.error,subprocess.CalledProcessError) as error:
                record['read_error']=str(error)
            found[record['path']]=record
    for program in sorted(programs):
        if program in found:continue
        context['directory']=str(Path(program).parent)
        record={'path':program}
        try:
            file=context['File'](Path(program).name)
            need(file.extent_bytes<=4*1024*1024,'Program exceeds bounded inspection')
            data=file.read(0,file.extent_bytes)
            (OUT/Path(program).name).write_bytes(data)
            record.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),relevant_strings=program_strings(data))
        except (ValueError,KeyError,zlib.error,subprocess.CalledProcessError) as error:record['read_error']=str(error)
        found[program]=record
report={'device':'venus','date':'2026-10-28','os_raw_sha256':metadata['raw_sha256'],
        'reader_sha256':sha(reader),'reused_reader_helper_sha256':sha(helpers),'files':found,
        'inline_plain_format_reference':'https://github.com/sgan81/apfs-fuse/blob/master/ApfsLib/Decmpfs.cpp (type9, marker0xCC, exact uncompressed size)',
        'scope':'Read-only host inspection of supplied 21H461 OS launch configuration and program strings; no runtime-cause claim'}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(DEVICE/'evidence/userspace-launch-jobs.json').write_text(json.dumps(report,indent=2)+'\n')
for path,record in found.items():
    print(path)
    print(json.dumps(record.get('job',record.get('read_error',record.get('relevant_strings'))),indent=2))
