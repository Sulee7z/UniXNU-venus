#!/usr/bin/env python3
"""Read actual Android touch binding and existing firmware, without control writes."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import struct

ROOT=Path(__file__).resolve().parents[3];ADB=ROOT/'tools/platform-tools/adb.exe'
OUT=ROOT/'artifacts/venus-touch-identity'/datetime.now(timezone.utc).strftime('read-%Y%m%dT%H%M%SZ')
OUT.mkdir(parents=True,exist_ok=False)
env={**os.environ,'HOME':str(ROOT/'home'),'USERPROFILE':str(ROOT/'home'),
    'ANDROID_USER_HOME':str(ROOT/'home/.android'),'ANDROID_SDK_HOME':str(ROOT/'home'),
    'APPDATA':str(ROOT/'home/AppData/Roaming'),'LOCALAPPDATA':str(ROOT/'home/AppData/Local'),
    'TEMP':str(ROOT/'tmp'),'TMP':str(ROOT/'tmp')}
commands=[]
def adb(arguments):
    command=[str(ADB),'-P','5037','-s','55870427',*arguments]
    result=subprocess.run(command,env=env,capture_output=True,timeout=90)
    commands.append({'command':command,'returncode':result.returncode,'stderr':result.stderr.decode('utf-8','replace')})
    (OUT/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
    return result
for prop,want in (('ro.product.device','venus'),('sys.boot_completed','1')):
    result=adb(['shell','getprop',prop])
    if result.returncode or result.stdout.decode().strip()!=want:raise ValueError('Android identity/boot check failed')
facts={}
queries={
 'kernel':['shell','uname','-a'],
 'fingerprint':['shell','getprop','ro.build.fingerprint'],
 'input-devices':['shell',"su -c 'cat /proc/bus/input/devices'"],
 'modules':['shell',"su -c 'cat /proc/modules'"],
 'input-sysfs':['shell',"su -c 'ls -l /sys/class/input'"],
 'spi-devices':['shell',"su -c 'ls -l /sys/bus/spi/devices'"],
 'spi-drivers':['shell',"su -c 'ls -l /sys/bus/spi/drivers'"],
 'touch-classes':['shell',"su -c 'ls -l /sys/class/touch /sys/class/touchscreen /sys/class/touchpanel'"],
 'firmware-candidates':['shell',"su -c 'ls -l /vendor/firmware/st_fts* /vendor/firmware_mnt/image/st_fts* /vendor/etc/firmware/st_fts* /odm/firmware/st_fts*'"],
 'vendor-module-list':['shell',"su -c 'ls /vendor/lib/modules'"],
}
for name,arguments in queries.items():
    result=adb(arguments);(OUT/(name+'.txt')).write_bytes(result.stdout+result.stderr)
    facts[name]={'returncode':result.returncode,'file':name+'.txt','sha256':hashlib.sha256(result.stdout+result.stderr).hexdigest()}
firmware={}
for path in ('/vendor/firmware/st_fts_k2.ftb','/vendor/firmware/st_fts_k2_htp.ftb',
             '/vendor/firmware_mnt/image/st_fts_k2.ftb','/vendor/etc/firmware/st_fts_k2.ftb'):
    result=adb(['exec-out',"su -c 'cat "+path+"'"])
    if result.returncode or result.stderr or len(result.stdout)<68 or struct.unpack_from('<I',result.stdout)[0]!=0xaa55aa55:continue
    if len(result.stdout)>4<<20:raise ValueError('Unexpected firmware size')
    name=path.lstrip('/').replace('/','_');(OUT/name).write_bytes(result.stdout)
    firmware[path]={'file':name,'bytes':len(result.stdout),'sha256':hashlib.sha256(result.stdout).hexdigest()}
record={'device':'venus','serial':'55870427','run':str(OUT),'facts':facts,'firmware':firmware,
        'scope':'Readonly Android identity/proc/bus binding and existing firmware bytes. No control/debug sysfs attributes read and no register/firmware/device writes.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record,indent=2))
