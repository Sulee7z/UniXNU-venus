#!/usr/bin/env python3
"""Read only cached FTS version nodes and the current kernel's immutable FDT."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'artifacts/venus-touch-identity'/datetime.now(timezone.utc).strftime('board-%Y%m%dT%H%M%SZ');OUT.mkdir(exist_ok=False)
env={**os.environ,'HOME':str(ROOT/'home'),'USERPROFILE':str(ROOT/'home'),'ANDROID_USER_HOME':str(ROOT/'home/.android'),'ANDROID_SDK_HOME':str(ROOT/'home')}
def adb(args):return subprocess.run([str(ROOT/'tools/platform-tools/adb.exe'),'-P','5037','-s','55870427',*args],env=env,capture_output=True,timeout=90)
if adb(['shell','getprop','ro.product.device']).stdout.strip()!=b'venus':raise ValueError('Wrong device')
facts={}
for name,command in {'cached-version':"su -c 'cat /proc/tp_fw_version /sys/bus/spi/devices/spi1.0/appid /sys/bus/spi/devices/spi1.0/mode_active'",
                     'node-names':"su -c 'ls -l /sys/bus/spi/devices/spi1.0/'"}.items():
    result=adb(['shell',command]);data=result.stdout+result.stderr;(OUT/(name+'.txt')).write_bytes(data)
    facts[name]={'returncode':result.returncode,'command':command,'sha256':hashlib.sha256(data).hexdigest()}
result=adb(['exec-out',"su -c 'cat /sys/firmware/fdt'"]);data=result.stdout
if not data.startswith(bytes.fromhex('d00dfeed')) or len(data)>4<<20:raise ValueError('Invalid live FDT capture')
(OUT/'live.dtb').write_bytes(data)
record={'device':'venus','serial':'55870427','run':str(OUT),'facts':facts,'fdt_bytes':len(data),'fdt_sha256':hashlib.sha256(data).hexdigest(),
        'scope':'Only source-verified cached show nodes and immutable FDT read; no register/control/firmware write or reboot.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record,indent=2))
