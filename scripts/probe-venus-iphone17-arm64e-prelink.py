#!/usr/bin/env python3
"""Probe how far the ordinary-ARM64 prelink planner gets with the actual iOS17 kernelcache."""
import hashlib
import inspect
import json
from pathlib import Path
import sys
import traceback

ROOT=Path('/mnt/g/UniXNU-Port')
sys.path.insert(0,str(ROOT/'sources/UniXNU-guide/kits/XnuPrelink'))
import native_prelink
from native_prelink import plan as base_plan

NATIVE=ROOT/'artifacts/venus-metal-touch/kernel-link-37/kernel.macho'
ORIGINAL=ROOT/'artifacts/venus-iphone17-compat/21H16/kernelcache.decompressed'
ROOTS=[
 'com.apple.filesystems.apfs','com.apple.driver.AppleMobileFileIntegrity',
 'com.apple.iokit.IOHIDFamily','com.apple.iokit.IOHIDEventDriver',
 'com.apple.iokit.IOGPUFamily','com.apple.iokit.IOMobileGraphicsFamily',
 'com.apple.iokit.IOStorageFamily','com.apple.kec.corecrypto',
]
def fileset_headers(data, image):
    import struct
    result={}
    for command,offset,length in image['commands']:
        if command!=0x80000035:continue
        _,fileoff,nameoff=struct.unpack_from('<QQI',data,offset+8)
        end=data.index(b'\0',offset+nameoff)
        name=data[offset+nameoff:end].decode()
        if name in result:raise ValueError('Duplicate fileset entry: '+name)
        result[name]=fileoff
    return result

def relaxed(data,at=0):
    import struct
    if at<0 or at+32>len(data):raise ValueError('Mach-O header outside image')
    magic,cpu,subtype,kind,count,size=struct.unpack_from('<6I',data,at)
    if (magic,cpu) != (0xfeedfacf,0x100000c) or subtype & 0x00ffffff not in (0,2) or kind not in (2,11,12):
        raise ValueError(f'Expected little-endian ARM64/ARM64e at {at:#x}: magic={magic:#x} cpu={cpu:#x} subtype={subtype:#x} kind={kind:#x}')
    end=at+32+size
    if end>len(data):raise ValueError('Load commands outside image')
    offset=at+32;commands=[];segments=[]
    for _ in range(count):
        if offset+8>end:raise ValueError('Truncated load command')
        command,length=struct.unpack_from('<II',data,offset)
        if length<8 or length%8 or offset+length>end:raise ValueError('Invalid load command extent')
        commands.append((command,offset,length))
        if command==0x19:
            if length<72:raise ValueError('Truncated segment')
            name,va,vmsize,fileoff,filesize,maxprot,initprot,nsects,flags=struct.unpack_from('<16s4Q4I',data,offset+8)
            if length!=72+80*nsects or filesize>vmsize or va+vmsize>1<<64:raise ValueError('Invalid segment extent')
            segments.append({'name':name.rstrip(b'\0').decode(),'va':va,'size':vmsize,'fileoff':fileoff,
                'filesize':filesize,'command_offset':offset,'maxprot':maxprot,'initprot':initprot,'sections':[]})
            for index in range(nsects):
                section_at=offset+72+index*80
                section_name,_,address,extent,section_offset=struct.unpack_from('<16s16sQQI',data,section_at)
                if extent and not va<=address<=address+extent<=va+vmsize:raise ValueError('Section outside segment')
                segments[-1]['sections'].append({'name':section_name.rstrip(b'\0').decode(),'va':address,
                    'size':extent,'fileoff':section_offset,'command_offset':section_at})
        offset+=length
    if offset!=end:raise ValueError('Load command size mismatch')
    return {'kind':kind,'segments':segments,'commands':commands}
native_prelink.macho=relaxed
source=inspect.getsource(base_plan).replace(
    "if native['kind'] != 2 or original['kind'] != 2:",
    "if native['kind'] not in (2,12) or original['kind'] not in (2,12):")
source=source.replace("    selected, interfaces = set(), set()",
                      "    fileset = fileset_headers(original_data, original)\n    selected, interfaces = set(), set()")
source=source.replace("        va = entry.get('_PrelinkExecutableLoadAddr')\n",
                      "        va = entry.get('_PrelinkExecutableLoadAddr')\n        if va == 0x7fffffffffffffff: va = None\n")
source=source.replace(
    "if any(key in entry for key in executable_keys) or not isinstance(entry.get('IOKitPersonalities'), dict) or not entry['IOKitPersonalities']:",
    "if (any(key in entry for key in executable_keys) and entry.get('_PrelinkExecutableLoadAddr') != 0x7fffffffffffffff) or not isinstance(entry.get('IOKitPersonalities'), dict) or not entry['IOKitPersonalities']:")
source=source.replace("    original_symbols = exports(original_data, original)",
    "    kernel_header = fileset.get('com.apple.kernel')\n"
    "    original_symbols = exports(original_data, macho(original_data, kernel_header)) if kernel_header is not None else exports(original_data, original)")
source=source.replace("        header = backed_offset(parent, va, 32, len(original_data))",
                      "        header = fileset.get(identifier)\n        if header is None: header = backed_offset(parent, va, 32, len(original_data))")
namespace=dict(native_prelink.__dict__)
namespace['fileset_headers']=fileset_headers
exec(compile(source,'<fileset-plan>','exec'),namespace)
plan=namespace['plan']
out=ROOT/'artifacts/venus-iphone17-prelink-probe'
out.mkdir(parents=True,exist_ok=True)
result={'native_sha256':hashlib.sha256(NATIVE.read_bytes()).hexdigest(),
        'original_sha256':hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
        'roots':ROOTS,'relaxed_parser':True}
try:
    plan_result=plan(NATIVE.read_bytes(),ORIGINAL.read_bytes(),ROOTS,-0x1000000)
    result.update(passed=True,components=plan_result['components'],codeless=plan_result['codeless_components'],
                  pointer_counts=plan_result['pointer_counts'],extents=len(plan_result['extents']),
                  loadable=plan_result['loadable'])
    (out/'plan.json').write_text(json.dumps(plan_result,indent=2)+'\n')
except Exception as error:
    result.update(passed=False,error=type(error).__name__,detail=str(error),
                  traceback=traceback.format_exc().splitlines()[-8:])
(out/'probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
