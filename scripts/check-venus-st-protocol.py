#!/usr/bin/env python3
"""ASan/UBSan qualification of the actual own ST C core against retained FTB."""
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus';OUT=ROOT/'artifacts/venus-st-touch/host-tests';OUT.mkdir(parents=True,exist_ok=True)
source=DEVICE/'package/VenusStTouch/VenusStProtocol.c';test=DEVICE/'tests/venus_st_protocol.c';binary=OUT/'protocol-test'
command=['gcc','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fno-pie','-no-pie','-fsanitize=address,undefined','-I',str(source.parent),str(source),str(test),'-o',str(binary)]
result=subprocess.run(command,capture_output=True,text=True,timeout=180);(OUT/'build.log').write_text(result.stdout+result.stderr)
if result.returncode:raise SystemExit(result.stdout+result.stderr)
firmware=ROOT/'artifacts/venus-touch-identity/details-20261029T103528Z/st_fts_k2.ftb'
result=subprocess.run([str(binary),str(firmware)],capture_output=True,text=True,timeout=180);(OUT/'test.log').write_text(result.stdout+result.stderr)
if result.returncode:raise SystemExit(result.stdout+result.stderr)
record={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'test_sha256':hashlib.sha256(test.read_bytes()).hexdigest(),
        'firmware_sha256':hashlib.sha256(firmware.read_bytes()).hexdigest(),'result':result.stdout.strip(),'scope':'Own actual C protocol/HID core; not hardware transport/event qualification.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
