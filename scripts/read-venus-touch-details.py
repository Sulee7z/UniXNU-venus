#!/usr/bin/env python3
"""Readonly exact FTS SPI module/input capabilities; validate existing FTB files."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'artifacts/venus-touch-identity'/datetime.now(timezone.utc).strftime('details-%Y%m%dT%H%M%SZ');OUT.mkdir(exist_ok=False)
env={**os.environ,'HOME':str(ROOT/'home'),'USERPROFILE':str(ROOT/'home'),'ANDROID_USER_HOME':str(ROOT/'home/.android'),
     'ANDROID_SDK_HOME':str(ROOT/'home'),'TEMP':str(ROOT/'tmp'),'TMP':str(ROOT/'tmp')}
commands=[]
def adb(arguments):
    command=[str(ROOT/'tools/platform-tools/adb.exe'),'-P','5037','-s','55870427',*arguments]
    result=subprocess.run(command,capture_output=True,env=env,timeout=90)
    commands.append({'command':command,'returncode':result.returncode,'stderr':result.stderr.decode('utf-8','replace')})
    return result
if adb(['shell','getprop','ro.product.device']).stdout.strip()!=b'venus':raise ValueError('Wrong Android device')
facts={}
queries={
 'fts-sysfs-names':"su -c 'ls -l /sys/bus/spi/devices/spi1.0'",
 'fts-binding':"su -c 'ls -l /sys/bus/spi/devices/spi1.0/driver /sys/bus/spi/devices/spi1.0/driver/module'",
 'fts-uevent':"su -c 'cat /sys/bus/spi/devices/spi1.0/uevent /sys/bus/spi/devices/spi1.0/modalias'",
 'fts-input-caps':"su -c 'getevent -lp /dev/input/event4'",
 'fts-module-version':"su -c 'cat /sys/module/fts_touch_spi/version /sys/module/fts_touch_spi/srcversion /sys/module/fts_touch_spi/taint'"}
for name,query in queries.items():
    result=adb(['shell',query]);data=result.stdout+result.stderr;(OUT/(name+'.txt')).write_bytes(data)
    facts[name]={'file':name+'.txt','returncode':result.returncode,'sha256':hashlib.sha256(data).hexdigest()}
binaries={}
for path in ('/vendor/lib/modules/fts_touch_spi.ko','/vendor/firmware/st_fts_k2.ftb','/vendor/firmware/st_fts_k2_htp.ftb'):
    result=adb(['exec-out',"su -c 'cat "+path+"'"]);data=result.stdout
    valid=data.startswith(b'\x7fELF') if path.endswith('.ko') else len(data)>=68 and struct.unpack_from('<I',data)[0]==0xaa55aa55
    if not valid:raise ValueError('Invalid module/FTB capture '+path)
    name=path.rsplit('/',1)[1];(OUT/name).write_bytes(data)
    row={'file':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    if path.endswith('.ftb'):row['header_words']=list(struct.unpack_from('<16I',data))
    binaries[path]=row
(OUT/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
record={'device':'venus','serial':'55870427','run':str(OUT),'facts':facts,'binaries':binaries,
        'scope':'Readonly module/FTB/input-cached metadata. No debug/control sysfs, reset or hardware firmware writes.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record,indent=2))
