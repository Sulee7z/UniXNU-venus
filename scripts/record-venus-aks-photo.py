#!/usr/bin/env python3
"""Bind the supplied AKS-run photograph to the existing one-shot boot record."""
import hashlib
import json
from pathlib import Path

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[1]
PHOTO = ROOT.parent / '20261028_082939.JPG'
RECORD = ROOT / 'evidence/aks-phone.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


record = json.loads(RECORD.read_text())
image = ROOT / 'artifacts/venus-aks-phone/phone/boot-venus-unixnu.img'
assert sha(image)==record['image_sha256']=='998bc56ec42e32ec7c161b0a704ee417d111ddf6886a0641fbc1a1ad9f5a989c'
assert record['ram_boot']['attempts_executed']==1
record.update(
    photos=['G:/20261028_082939.JPG'], photo_sha256=sha(PHOTO),
    observed={
        'screen_seconds':150, 'root_accepted':1, 'gpu_stage':'0xa4', 'gpu_probe_calls':1,
        'display_stage':10, 'swap_validation_calls':0, 'display_client_calls':3,
        'recent_springboard_sigtrap_pids':[152,153,154], 'lock_screen_or_desktop_visible':False,
        'aks_runtime_state':None, 'liveactivitiesd_health':None, 'watchdogd_health':None,
        'pc_lr_slide_machine_verified':False,
    },
    conclusion='AKS-enabled image still shows repeated SpringBoard SIGTRAP and zero display swaps at 150 s. The bounded recent-exit list cannot prove liveactivitiesd/watchdogd recovered. The previous claim that AKS had broken part of the wait chain was unsupported; AKS runtime counters were not visible in this image.',
    pending='Observe explicit AKS/HID state in the new HID candidate after its separately authorized boot; retain the no-Metal CPU-display investigation.',
    limits=[
        'Single manually read photograph; PC/LR/slide transcription is not machine-verified.',
        'No usable USB serial/ADB after XNU entry. No complete per-process exit history was retrieved.',
        'AKS is an offline state/notification service, not key storage.',
        'Correction: the actual bsd_autoconf/late probe precedes root acceptance. Earlier QEMU runs did not read AKS counters; the new HID QEMU controls do.',
    ])
text = json.dumps(record, indent=2)+'\n'
RECORD.write_text(text)
(DEVICE / 'evidence/aks-phone.json').write_text(text)
print('Recorded photograph:', PHOTO, sha(PHOTO))
print('Result: SpringBoard still SIGTRAP; no verified recovery of other daemons')
