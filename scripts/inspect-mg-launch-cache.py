#!/usr/bin/env python3
"""Inspect the deployed OS's launchd bootstrap inputs, host-only, at true EOF."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import plistlib
import re
import struct
import subprocess
import sys
import uuid
import zlib

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
sys.path.insert(0,str(DEVICE/'scripts'))
import data_store_view as store


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--prng-only',action='store_true')
    parser.add_argument('--cleanup-only',action='store_true')
    args=parser.parse_args();out=args.output.resolve()
    if sys.platform=='win32' and out.drive.upper()!='G:':parser.error('Use G:')
    if sys.platform!='win32' and not out.is_relative_to(Path('/mnt/g')):parser.error('Use G: mount')
    metadata=json.loads((ROOT/'artifacts/venus-deployment/OS-source.json').read_text())
    raw=ROOT/'artifacts/venus-deployment/OS.raw';reader=ROOT/'sources/UniXNU-zeta-reference/scripts/zeta_apfs_image.py'
    if store.sha(raw)!=metadata['raw_sha256'] or store.sha(reader)!=metadata['apfs_reader_source_sha256']:
        raise ValueError('Deployed OS/reader changed')
    helper=DEVICE/'scripts/symbolicate-venus-fault.py'
    names={'catalog_node','sealed_records','sealed_extents','lzfse_decode','decode_fork','File'}
    definitions=[node for node in ast.parse(helper.read_text()).body
                 if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names]
    if {node.name for node in definitions}!=names:raise ValueError('Reader definitions changed')
    apfs=store.module(reader,'launch_cache_apfs')
    out.mkdir(exist_ok=False)
    result={'os_raw_sha256':metadata['raw_sha256'],'helper_sha256':store.sha(helper),
            'directories':{},'files':{},'scope':'Read-only deployed OS launch inputs/strings, not device launch outcome.'}
    with raw.open('rb') as stream:
        container=apfs.Container(stream,metadata['container_offset']);volumes=list(container.volumes())
        if len(volumes)!=1:raise ValueError('Ambiguous OS volume')
        volume=volumes[0]
        if str(uuid.UUID(bytes=volume.superblock[0xf0:0x100])).upper()!=metadata['volumes'][0]['volume_uuid']:
            raise ValueError('Wrong OS UUID')
        def need(ok,why):
            if not ok:raise ValueError(why)
        context={'container':container,'volume':volume,'struct':struct,'zlib':zlib,'OUT':out,
                 'subprocess':subprocess,'apfs':apfs,'need':need}
        exec(compile(ast.Module(body=definitions,type_ignores=[]),str(helper),'exec'),context)
        if volume.incompatible&0x20:
            volume.records=lambda oid,kind:context['sealed_records'](oid,kind,volume.root_tree)
            volume.stream_extents=context['sealed_extents']
        paths=['/tmp','/usr/libexec/dirs_cleaner'] if args.cleanup_only else ['/usr/libexec/prng_seedctl'] if args.prng_only else ['/sbin/launchd','/usr/libexec/launchd_cache_loader']
        for directory in (() if args.prng_only or args.cleanup_only else ('/System/Library/xpc','/System/Library/LaunchDaemons')):
            try:
                inode=volume.lookup(directory);entries=[]
                for key,_ in volume.records(inode,apfs.TYPE_DIR_REC):
                    length=struct.unpack_from('<I',key,8)[0]&0x3ff
                    name=key[12:12+length].rstrip(b'\0').decode()
                    if any(k in name.lower() for k in ('launchd','cache','iomfb_fdr','adrenoprobed')):
                        entries.append(name);paths.append(directory+'/'+name)
                result['directories'][directory]=entries
            except ValueError as error:result['directories'][directory]={'error':str(error)}
        for path in paths:
            row={};result['files'][path]=row
            try:
                inode=volume.lookup(path);attrs=volume.xattrs(inode)
                directory,name=path.rsplit('/',1);context['directory']=directory
                if 'com.apple.fs.symlink' in attrs:
                    data=attrs['com.apple.fs.symlink'][1];row['symlink_target']=data.rstrip(b'\0').decode()
                    row['bytes']=len(data);row['sha256']=hashlib.sha256(data).hexdigest();continue
                if 'com.apple.decmpfs' in attrs:
                    header=attrs['com.apple.decmpfs'][1]
                    magic,kind,size=struct.unpack_from('<4sIQ',header)
                    if magic!=b'fpmc' or size>16<<20:raise ValueError('Bad compressed size/magic')
                    if kind==9:
                        if len(header)!=size+17 or header[16]!=0xcc:raise ValueError('Bad plain inline fork')
                        data=header[17:]
                    else:
                        file=context['File'](name);data=file.read(0,file.extent_bytes)
                else:
                    records=volume.records(inode,apfs.TYPE_INODE)
                    if len(records)!=1:raise ValueError('Ambiguous inode')
                    size=store.inode_info(records[0][1])['size']
                    if size is None or size>16<<20:raise ValueError('Missing/large true EOF')
                    file=context['File'](name);data=file.read(0,size)
                filename=path.replace('/','_').lstrip('_');(out/filename).write_bytes(data)
                row.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),output=filename)
                if path.endswith('.plist'):
                    plist=plistlib.loads(data)
                    row.update(plist_type=type(plist).__name__)
                    if isinstance(plist,dict):
                        row['top_keys']=list(plist)
                        row['selected']={k:plist[k] for k in ('Label','ProgramArguments','Program','RunAtLoad') if k in plist}
                row['strings']=[s.decode('ascii') for s in re.findall(rb'[\x20-\x7e]{5,}',data)
                    if re.search(rb'launchd|LaunchDaemons|[Cc]ache|bootstrap|[Dd]irectory|readdir|enumerat',s)]
            except (ValueError,KeyError,struct.error) as error:row['error']=str(error)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'files':{p:{k:r[k] for k in ('bytes','sha256','error','symlink_target') if k in r}
                              for p,r in result['files'].items()},'report':str(out/'report.json')},indent=2))


if __name__=='__main__':main()
