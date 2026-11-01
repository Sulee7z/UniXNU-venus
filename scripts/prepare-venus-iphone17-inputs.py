#!/usr/bin/env python3
"""Fetch the selected iPhone17 root/SystemOS/trust inputs with full ZIP CRC and SHA checks."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import sys
import urllib.request
import zipfile
import zlib

ROOT=Path('/mnt/g/UniXNU-Port')
sys.path.insert(0,str(ROOT/'sources/UniXNU-guide/scripts'))
from unixnu.ipsw import RangeFile

BASE=ROOT/'artifacts/venus-iphone17-compat/21H16'
COMPAT=json.loads((BASE/'report.json').read_text())
URL=COMPAT['source']
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--resume',action='store_true')
parser.add_argument('--components',default='OS;Cryptex1,SystemOS;DeviceTree;StaticTrustCache;Cryptex1,SystemTrustCache')
args=parser.parse_args()
out=args.output;out.mkdir(parents=True,exist_ok=True)


class CheckedRangeFile(RangeFile):
    def _block(self,index):
        if index in self.cache:return self.cache[index]
        start=index*self.block;end=min(start+self.block,self.size)-1
        request=urllib.request.Request(self.url,headers={'Range':f'bytes={start}-{end}','Accept-Encoding':'identity'})
        with urllib.request.urlopen(request,timeout=120) as response:
            assert response.status==206 and response.headers['Content-Range']==f'bytes {start}-{end}/{self.size}','Unmatched range response'
            data=response.read(end-start+2)
        assert len(data)==end-start+1,'Short/oversized range response'
        if len(self.cache)>=4:self.cache.pop(next(iter(self.cache)))
        self.cache[index]=data
        return data


with CheckedRangeFile(URL,block=64<<20) as remote,zipfile.ZipFile(remote) as archive:
    manifest_bytes=archive.read('BuildManifest.plist')
    manifest=plistlib.loads(manifest_bytes)
    assert manifest['ProductVersion']=='17.7' and manifest['ProductBuildVersion']=='21H16'
    assert 'iPhone11,8' in manifest['SupportedProductTypes']
    identities=[row for row in manifest['BuildIdentities'] if row['Info']['DeviceClass']=='n841ap' and row['Info']['RestoreBehavior']=='Erase']
    assert len(identities)==1
    identity=identities[0]
    available={name:{'member':item['Info']['Path'],'bytes':archive.getinfo(item['Info']['Path']).file_size,
                     'zip_crc32':f'{archive.getinfo(item["Info"]["Path"]).CRC:08x}'}
               for name,item in identity['Manifest'].items() if 'Path' in item.get('Info',{})}
    extracted={}
    for component in [value for value in args.components.split(';') if value]:
        row=available.get(component)
        if row is None:raise SystemExit('Missing component: '+component)
        path=out/Path(row['member']).name
        receipt=path.with_suffix(path.suffix+'.json')
        if receipt.exists() and path.exists():
            previous=json.loads(receipt.read_text())
            assert previous['source']==URL and previous['member']==row['member']
            with path.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==previous['sha256']
            extracted[component]=previous;continue
        assert not path.exists(),'Unrecorded existing input: '+str(path)
        partial=path.with_suffix(path.suffix+'.partial')
        existing=partial.stat().st_size if partial.exists() else 0
        if partial.exists():assert args.resume and archive.getinfo(row['member']).compress_type==zipfile.ZIP_STORED,'Resume requires a stored member'
        assert existing<=row['bytes']
        digest=hashlib.sha256();size=0;crc=0
        if existing:
            with partial.open('rb') as previous:
                while chunk:=previous.read(8<<20):digest.update(chunk);crc=zlib.crc32(chunk,crc);size+=len(chunk)
        print('Extracting',component,row['member'],row['bytes'],flush=True)
        with archive.open(row['member']) as source,partial.open('ab' if partial.exists() else 'xb') as target:
            if existing:source.seek(existing)
            while chunk:=source.read(8<<20):
                target.write(chunk);digest.update(chunk);crc=zlib.crc32(chunk,crc);size+=len(chunk)
                if size%(512<<20)==0:print(component,size>>20,'MiB',flush=True)
        assert size==row['bytes'] and crc==archive.getinfo(row['member']).CRC,'Complete member CRC mismatch'
        partial.rename(path)
        record={**row,'source':URL,'path':str(path),'sha256':digest.hexdigest(),'zip_crc_verified':True}
        receipt.write_text(json.dumps(record,indent=2)+'\n');extracted[component]=record
    report={'product':COMPAT['product'],'version':COMPAT['version'],'build':COMPAT['build'],
        'device_class':COMPAT['device_class'],'source':URL,'source_zip_bytes':remote.size,
        'manifest_sha256':hashlib.sha256(manifest_bytes).hexdigest(),'available_components':available,
        'extracted':extracted,'phone_operations':False,'root_replaced':False,'native_kernel_built':False,
        'current_xnu':'10063.141.1','target_kernel_xnu':'10063.142.1.700.5'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'extracted':{k:{'bytes':v['bytes'],'sha256':v['sha256']} for k,v in extracted.items()}},indent=2))
