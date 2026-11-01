#!/usr/bin/env python3
"""Compare retained Data startup preferences with the common sheng seed recipe."""
import argparse
import json
from pathlib import Path
import plistlib
import sys

ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus'
sys.path.insert(0,str(DEVICE/'scripts'))
import data_store_view as store

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True);args=parser.parse_args()
expected={
 'com.apple.migration':{'LastSystemVersion':'21H461'},
 'com.apple.springboard':{'BKNoWatchdogs':True,'MCForceShowCloudConfigurationUI':False},
 'com.apple.purplebuddy':{'SetupDone':True,'SetupFinishedAllSteps':True,'SetupVersion':11,'daemonizeNeedsToRun':False},
 'com.apple.purplebuddy.notbackedup':{'ShouldRunDiagnosticsMiniBuddy':False,'ShouldRunHSA2MiniBuddy':False,
   'ShouldRunKeychainSyncMiniBuddy':False,'ShouldRunMesaMiniBuddy':False,'ShouldRunPaymentMiniBuddy':False,
   'ShouldRunStandardMiniBuddy':False,'SilentICDPUpgrade':False},
 'com.apple.managedconfiguration.notbackedup':{'LockdownActivationIndicatesCloudConfigurationAvailable':False}}
view,apfs,volume=store.open_volume(args.run,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT)
try:
    out=args.run/'sheng-startup-prefs';out.mkdir(exist_ok=False);result={}
    for name,keys in expected.items():
        path='/mobile/Library/Preferences/'+name+'.plist'
        try:
            data=store.read_file(view,apfs,volume,path);decoded=plistlib.loads(data)
            (out/(name+'.plist')).write_bytes(data)
            extra=('FBLaunchWatchdogExceptions','SBDisableAutoDim','SBDontDimOrLockOnAC','SBDisableIdleSleep') if name=='com.apple.springboard' else ()
            result[name]={'state':'parsed','bytes':len(data),'sha256':store.sha(out/(name+'.plist')),
                'expected':keys,'actual':{k:decoded.get(k) for k in (*keys,*extra)},
                'mismatches':[k for k,v in keys.items() if decoded.get(k)!=v]}
        except ValueError as error:result[name]={'state':'absent' if 'has 0 directory records' in str(error) else 'error','detail':str(error)}
    report={'run':str(args.run),'preferences':result,'scope':'Retained Data plist values versus common seed-data-skip-setup.py recipe; no phone edits or proof of UI startup.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
finally:view.close()
