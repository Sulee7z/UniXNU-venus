#!/usr/bin/env python3
"""Extract original target HID personalities, not a guessed device class match."""
import hashlib
import json
from pathlib import Path
import plistlib
import struct
import sys
ROOT=Path(__file__).resolve().parents[3];SOURCE=ROOT/'artifacts/venus-guide/ipsw/21H461/kernelcache.decompressed'
data=SOURCE.read_bytes();at=32;raw=None
for _ in range(struct.unpack_from('<I',data,16)[0]):
    cmd,size=struct.unpack_from('<II',data,at)
    if cmd==0x19:
        for i in range(struct.unpack_from('<I',data,at+64)[0]):
            s=at+72+i*80;section=data[s:s+16].rstrip(b'\0');segment=data[s+16:s+32].rstrip(b'\0')
            if segment==b'__PRELINK_INFO' and section==b'__info':
                length=struct.unpack_from('<Q',data,s+40)[0];offset=struct.unpack_from('<I',data,s+48)[0];raw=data[offset:offset+length].rstrip(b'\0')
    at+=size
sys.path.insert(0,str(ROOT/'sources/UniXNU-guide/kits/XnuPrelink'))
from native_prelink import unserialize_xml
assert raw;info=unserialize_xml(raw);selected=[]
for row in info['_PrelinkInfoDictionary']:
    if any(name in row.get('CFBundleIdentifier','') for name in ('IOHID','HIDEvent')):
        selected.append({k:row[k] for k in ('CFBundleIdentifier','IOKitPersonalities','OSBundleLibraries') if k in row})
out=ROOT/'artifacts/venus-st-touch/original-hid-personalities.json'
out.write_text(json.dumps({'kernelcache_sha256':hashlib.sha256(data).hexdigest(),'modules':selected},indent=2,default=str)+'\n',encoding='utf-8')
print(json.dumps({'output':str(out),'matching':[{k:p[k] for k in ('IOClass','IOProviderClass','DeviceUsagePairs') if k in p}
    for row in selected if row['CFBundleIdentifier'] in ('com.apple.iokit.IOHIDEventDriver','com.apple.iokit.IOHIDEventDriverSafeBoot')
    for p in row.get('IOKitPersonalities',{}).values()]},indent=2))
