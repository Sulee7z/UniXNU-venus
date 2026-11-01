#!/usr/bin/env python3
"""Inspect the readonly captured module's actual codec and firmware identity."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path('/mnt/g/UniXNU-Port');INPUT=ROOT/'artifacts/venus-touch-identity/details-20261029T103528Z'
OUT=ROOT/'artifacts/venus-touch-identity/module-analysis';OUT.mkdir(exist_ok=False)
module=INPUT/'fts_touch_spi.ko';symbols=subprocess.check_output(['/usr/bin/llvm-nm','-a',str(module)],text=True)
(OUT/'symbols.txt').write_text(symbols)
selected=[]
for line in symbols.splitlines():
    parts=line.split()
    if len(parts)==3 and parts[1].lower()=='t' and re.search('enter_pointer|leave_pointer|motion_pointer|appid_show|fw.*show|version.*show',parts[2]):selected.append(parts[2])
for name in selected:
    result=subprocess.run(['/usr/bin/llvm-objdump','--disassemble-symbols='+name,str(module)],capture_output=True,text=True,check=True,timeout=60)
    (OUT/(name+'.txt')).write_text(result.stdout)
strings=[s.decode() for s in re.findall(rb'[\x20-\x7e]{5,}',module.read_bytes()) if re.search(rb'FTS|5\.[0-9]|version|SALIX|WALNUT|appid|FTM5|Firmware',s)]
record={'module_sha256':hashlib.sha256(module.read_bytes()).hexdigest(),'selected_functions':selected,'strings':strings,
    'scope':'Actual loaded module source/codec identity inspection, no execution/control hardware writes.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
