#!/usr/bin/env python3
"""Decode all target touch/bus/provider properties from the newly read FDT."""
import hashlib
import json
from pathlib import Path
import struct
import sys
ROOT=Path('/mnt/g/UniXNU-Port');INPUT=ROOT/'artifacts/venus-touch-identity/board-20261029T113459Z/live.dtb'
sys.path.insert(0,'/root/unixnu-build/UniXNU-sheng-base/scripts')
from unixnu.devicetree import read_fdt
nodes={};phandles={}
def walk(node,parent=''):
    path=parent+'/'+node.name if node.parent else '';nodes[path]=node
    for key in ('phandle','linux,phandle'):
        raw=node.properties.get(key)
        if raw:phandles[int.from_bytes(raw,'big')]=path
    for child in node.children:walk(child,path)
walk(read_fdt(INPUT.read_bytes()))
selected={'/soc/spi@a8c000','/soc/spi@a8c000/fts@0'}
for path in list(selected):
    for key,raw in nodes[path].properties.items():
        if key.endswith(('-supply','-gpio')) or key in ('pinctrl-0','pinctrl-1','qcom,wrapper-core','interrupt-parent'):
            if len(raw)%4==0:
                for value in struct.unpack('>'+str(len(raw)//4)+'I',raw):
                    if value in phandles:selected.add(phandles[value])
record={}
for path in sorted(selected):
    record[path]={key:{'hex':raw.hex(),'cells':list(struct.unpack('>'+str(len(raw)//4)+'I',raw)) if raw and len(raw)%4==0 else [],
                    'strings':raw.rstrip(b'\0').decode('utf-8','replace').split('\0') if raw.endswith(b'\0') else []}
                  for key,raw in nodes[path].properties.items()}
out=INPUT.parent/'touch-resources.json';out.write_text(json.dumps({'fdt_sha256':hashlib.sha256(INPUT.read_bytes()).hexdigest(),'nodes':record},indent=2)+'\n')
print(json.dumps({'output':str(out),'touch':record['/soc/spi@a8c000/fts@0'],'bus':record['/soc/spi@a8c000']},indent=2))
