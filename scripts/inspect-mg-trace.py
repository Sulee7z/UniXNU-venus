#!/usr/bin/env python3
"""Decode strict tracev3 chunks from saved Data and search query startup strings.

Decoded strings do not establish event PID/time/boot attribution.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import data_store_view as store
from tracev3_chunks import chunks,chunkset

KEYWORDS=['org.unixnu.venus.mg-query','venus-mg-query','adrenoprobed','ngpu',
          'LaunchDaemons','launchd_cache','bindfs','FBSDisplayMode']
ROOT=Path(__file__).resolve().parents[3]


def scan(blob,source):
    hits={}
    for key in KEYWORDS:
        at=0;rows=[]
        while len(rows)<12:
            at=blob.find(key.encode(),at)
            if at<0:break
            text=''.join(chr(c) if 32<=c<127 else '.' for c in blob[max(0,at-120):at+240])
            rows.append({'source':source,'offset':at,'context':text});at+=len(key)
        if rows:hits[key]=rows
    return hits


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--keyword',action='append',default=[])
    args=parser.parse_args();run=args.run.resolve()
    if args.keyword:KEYWORDS.extend(args.keyword)
    if sys.platform=='win32' and run.drive.upper()!='G:':parser.error('Use G:')
    if sys.platform!='win32' and not run.is_relative_to(Path('/mnt/g')):parser.error('Use G: mount')
    view,apfs,volume=store.open_volume(run,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT)
    try:
        out=run/'mg-trace-chunks';out.mkdir(exist_ok=False)
        report={'run':str(run),'files':{},'keywords':KEYWORDS,
                'scope':'Strict preamble/bv41/LZ4/footer decoding. String context only; no event PID/time/boot attribution.'}
        for entry in store.list_directory(apfs,volume,'/db/diagnostics/Persist'):
            if entry['kind']!='file' or not entry['name'].endswith('.tracev3'):continue
            name=entry['name'];blob=store.read_file(view,apfs,volume,'/db/diagnostics/Persist/'+name)
            if len(blob)>16<<20:raise ValueError('Unexpected trace size')
            (out/name).write_bytes(blob)
            row={'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),'chunks':[],'decoded_bytes':0,'hits':{}}
            report['files'][name]=row
            try:
                for at,tag,sub,body in chunks(blob):
                    item={'offset':at,'tag':hex(tag),'subtag':sub,'bytes':len(body)};row['chunks'].append(item)
                    if tag!=0x600d:continue
                    try:
                        payload=chunkset(body)
                        item.update(decoded_bytes=len(payload),decoded_sha256=hashlib.sha256(payload).hexdigest())
                        output=f'{name}-{at:08x}.decoded';(out/output).write_bytes(payload)
                        row['decoded_bytes']+=len(payload)
                        for key,hits in scan(payload,output).items():row['hits'].setdefault(key,[]).extend(hits)
                    except ValueError as error:item['decode_error']=str(error)
            except ValueError as error:row['preamble_error']=str(error)
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'files':len(report['files']),
            'decoded_bytes':sum(r['decoded_bytes'] for r in report['files'].values()),
            'hits':{k:sum(len(r['hits'].get(k,[])) for r in report['files'].values()) for k in KEYWORDS},
            'preamble_errors':{k:r['preamble_error'] for k,r in report['files'].items() if 'preamble_error' in r},
            'decode_errors':[c for r in report['files'].values() for c in r['chunks'] if 'decode_error' in c],
            'report':str(out/'report.json')},indent=2))
    finally:view.close()


if __name__=='__main__':main()
