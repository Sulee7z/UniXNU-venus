#!/usr/bin/env python3
"""Record015 readback and measured matching failure/fix without physical claims."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];DEVICE=ROOT/'ports/UniXNU-venus';ART=ROOT/'artifacts'
run=ART/'venus-data-forensics/read-20261029T181433Z';index=json.loads((run/'index.json').read_text());assert index['complete'] and index['metadata_stable']
files=json.loads((run/'forensics-v2/report.json').read_text());logs=run/'mg-launch-logs/log_com.apple.xpc.launchd_launchd.log'
assert 'sheng-build-tag=touch-015' in logs.read_text(encoding='utf-8')
before=json.loads((ART/'venus-st-touch/qemu-hid-fixed-r2/report.json').read_text());after=json.loads((ART/'venus-st-touch/qemu-hid-matching/report.json').read_text())
assert not before['passed'] and before['state']['_venus_st_hid_reports']==0 and before['state']['_venus_st_hid_ticks']>0
assert after['passed'] and after['state']['_venus_st_hid_reports']==3 and after['state']['_venus_st_hid_ready']==1
report={'device':'venus','observation':'015欢迎页可显示，点击/滑动无反应','readback':{'run':str(run),'data_bytes':index['present_pages']*4096,
    'total_block_read_bytes':index['present_pages']*4096+2*index['geometry']['metadata_bytes'],'segments':len(index['runs']),
    'checkpoint':files['volume_checkpoint_xid'],'metadata_stable':True,'coverage_and_sha_verified':True,
    'launchd_log_sha256':hashlib.sha256(logs.read_bytes()).hexdigest(),'exact015_args_matched':True,
    'trace_scope':'28 files decoded valid prefixes, final1c incomplete tail retained. One VenusHidTouch/IOHIDInterface string context, no runtime ST register/status values or attributed HID event stream.'},
    'correction':'Previous mode1 returns before HID metaclass construction. status0 was an untouched initializer, not an executed registration/report result.014 hardware last marker does not prove a fault PC or duplicate registration cause.',
    'matching_defect':'Original21H461 IOHIDEventDriver codeless bundle contains keyboard/buttons/sensor personalities. Generic digitizer page13 personality is in omitted IOHIDEventDriverSafeBoot.',
    'before':before,'after':after,
    'fix':'Include/load original codeless IOHIDEventDriverSafeBoot; own HID provides workloop before base start, HIDDefaultBehavior and DigitizerCollectionDispatch. Meta/start/match/report states now distinct and initialized -1.',
    'startup_diagnostic':json.loads((ART/'venus-st-touch/qemu-startup-report/report.json').read_text()),
    'candidate':json.loads((ART/'venus-touch-017/candidate.json').read_text()),
    'scope':'QEMU uses separate authored producer, same compiled HID/codec as production. Matching/handleReport success is measured; ST power/firmware/GENI transfer/physical UIKit interaction still require phone results.'}
(DEVICE/'evidence/touch015-review.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'readback':report['readback'],'fixed_hid':after['state'],'image':report['candidate']['image_sha256']},indent=2,ensure_ascii=False))
