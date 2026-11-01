#!/usr/bin/env python3
"""Run raw STM gesture, GPIO, startup and SPI lifetime regressions on host."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('/mnt/g/UniXNU-Port')
DEVICE = ROOT/'ports/UniXNU-venus'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--regression-control',type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True,exist_ok=False)
core = DEVICE/'package/VenusStTouch'
tests = DEVICE/'tests'
firmware = ROOT/'artifacts/venus-touch-identity/details-20261029T103528Z/st_fts_k2.ftb'
vendor = ROOT/'artifacts/venus-touch-audit-035/vendor/drivers/input/touchscreen/fts_spi/fts_lib'
software = (vendor/'ftsSoftware.h').read_text()
hardware = (vendor/'ftsHardware.h').read_text()
for text in ('EVT_ID_MOTION_POINT','0x23','EVT_ID_LEAVE_POINT','0x33'):
    assert text in software
assert 'STMicroelectronics' in hardware and 'FTS_CMD_HW_REG_R' in hardware and '0xFB' in hardware
base = ['gcc','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fno-pie','-no-pie',
        '-fsanitize=address,undefined','-I',str(core),'-I',str(ROOT/'sources/UniXNU-guide/drivers/QcomGeniSpi')]
rows=[]
def check(name,sources,argv=(),expect_fail=False):
    binary=args.output/name
    command=base+[str(x) for x in sources]+['-o',str(binary)]
    build=subprocess.run(command,capture_output=True,text=True,timeout=180)
    (args.output/(name+'.build.log')).write_text(build.stdout+build.stderr)
    if build.returncode:raise SystemExit('Compile failed: '+name)
    result=subprocess.run([str(binary),*[str(x) for x in argv]],capture_output=True,text=True,timeout=120)
    (args.output/(name+'.run.log')).write_text(result.stdout+result.stderr)
    if bool(result.returncode)!=expect_fail:raise SystemExit('Unexpected test result: '+name)
    if expect_fail and 'report[1]==tips[calls]' not in result.stderr:
        raise SystemExit('Control did not fail at the expected motion-as-lift assertion')
    rows.append({'name':name,'returncode':result.returncode,'expected_failure':expect_fail,
                 'sources':{str(s):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},
                 'result':(result.stderr if expect_fail else result.stdout).strip()})

if args.regression_control:
    check('old-motion-control',[args.regression_control,tests/'venus_st_motion_regression.c'],expect_fail=True)
check('motion',[core/'VenusStProtocol.c',tests/'venus_st_motion_regression.c'])
check('protocol',[core/'VenusStProtocol.c',tests/'venus_st_protocol.c'],[firmware])
check('transport',[core/'VenusStGeniTransport.c',tests/'venus_st_transport.c'])
record={'passed':True,'phone_operations':False,'hardware_verified':False,'tests':rows,
        'headers':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(core.glob('*.h'))},
        'firmware_sha256':hashlib.sha256(firmware.read_bytes()).hexdigest()}
(args.output/'report.json').write_text(json.dumps(record,indent=2)+'\n')
for row in rows:print(row['name']+': '+('expected regression reproduced' if row['expected_failure'] else row['result']))
