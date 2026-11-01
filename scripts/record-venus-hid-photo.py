#!/usr/bin/env python3
"""Record the supplied HID photograph and its independently checked cache mapping."""
import hashlib
import json
from pathlib import Path
import re

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[1]
PHOTO = ROOT.parent / '20261028_091241.JPG'
RECORD = DEVICE / 'evidence/hid-phone.json'
SYMBOLICATION = ROOT / 'artifacts/venus-hid-fault-symbolication/symbolication.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


record = json.loads(RECORD.read_text())
mapping = json.loads(SYMBOLICATION.read_text())
need_sha = '96a2c7476da6946261e08993014d96ab866e7e602644a76ad76049afaef5c456'
assert record['image_sha256']==need_sha==sha(ROOT / 'artifacts/venus-hid-phone/phone/boot-venus-unixnu.img')
assert sha(PHOTO)==mapping['photo_sha256']
assert mapping['original_pc_is_brk_zero'] and mapping['esr_is_aarch64_brk_zero']
assert mapping['addresses'][0]['unslid_va']=='0x19f3d0744'
previous = json.loads((DEVICE / 'evidence/a660-live-phone.json').read_text())
previous_text = previous['faults']['crash_record']
old_pc = int(re.search(r'PC([0-9a-fA-F]+)', previous_text)[1],16)
old_slide = int(re.search(r'\+([0-9a-fA-F]+)', previous_text)[1],16)
same = old_pc-old_slide == int(mapping['addresses'][0]['unslid_va'],16)
record.update(photos=['G:/20261028_091241.JPG'], photo_sha256=sha(PHOTO), observed={
    'screen_seconds':132,
    'aks':{'stage':3,'status':0,'opens':4,'calls':110},
    'hid':{'stage':3,'load_status':0,'matching_load_status':0,'resource_found':1,
           'meta_status':0,'start_count':1,'start_result':0},
    'gpu':{'stage':'0xa4','probe_calls':1},
    'display':{'stage':10,'swap_calls':0,'copy_calls':0,'client_calls':3,'lock_screen_visible':False},
    'springboard_sigtrap_visible':True,'watchdogd_sigtrap_visible':True,
    'springboard_crash_pid':152,
}, fault_mapping=mapping, fault_mapping_report_sha256=sha(SYMBOLICATION),
    earlier_photo_comparison={'previous_photo':'G:/20261028_074705.JPG','pc':hex(old_pc),
        'slide':hex(old_slide),'unslid_pc':hex(old_pc-old_slide),'same_as_current':same,
        'input_kind':'Two manual photograph transcriptions; current mapping checked against exact deployed SystemOS'},
    conclusion='AKS is initialized and has received opens/calls; the offline HID device is initialized and started; GPU retains its successful bring-up stage. SpringBoard still takes SIGTRAP and no display swaps/copies are observed. Missing initialization of these components is not an adequate explanation. The transcribed PC maps to a real BRK #0 in FrontBoardServices at unslid 0x19f3d0744, matching the earlier A660 photograph after slide removal.',
    pending='Identify the FrontBoardServices failure path and capture its error/termination context and persistent logs before another component-based hypothesis or phone test.',
    limits=[
        'Input values are manually transcribed from one photograph, not live debugger reads.',
        'The exact SystemOS/cache mapping verifies the BRK instruction and containing framework; no local function symbol or runtime assertion text has been recovered.',
        'AKS open/call counts do not prove every selector or dependent daemon is healthy.',
        'HID device start does not demonstrate physical touch, buttons, input delivery or a working SpringBoard session.',
        'The photo does not establish long-term GPU rendering stability or frame presentation.',
    ])
RECORD.write_text(json.dumps(record,indent=2)+'\n')
print('Recorded HID photo:', sha(PHOTO))
print('FrontBoardServices BRK #0 at 0x19f3d0744; previous photograph agrees:', same)
