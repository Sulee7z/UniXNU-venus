#!/usr/bin/env python3
"""Audit the tested Venus image's board stubs and record the latest photograph.

Only reads host artifacts/source. No device commands or hardware writes.
"""
import hashlib
import json
from pathlib import Path
import sys
import tomllib

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[1]
WORK = Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
CANDIDATE = ROOT / 'artifacts/venus-frontboard-mode-phone'
PHOTO = ROOT.parent / '20261028_102002.JPG'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text())


candidate = load(CANDIDATE/'candidate.json')
kernel = CANDIDATE/'kernel/kernel.macho'
assert sha(kernel)==candidate['kernel_sha256']
assert sha(CANDIDATE/'phone/boot-venus-unixnu.img')==candidate['boot_sha256']
build = load(WORK/'tree/build/native-legacy-display/build-report.json')
stubs = DEVICE/'package/DisplayProbeStubs.c'
assert sha(stubs)==build['source_sha256']['kits/venus/DisplayProbeStubs.c']
sys.path.insert(0,str(WORK/'tree/kits/XnuPrelink'))
from native_prelink import macho, backed_offset, exports
blob = kernel.read_bytes()
image = macho(blob)
names = {n:a for a,group in exports(blob,image).items() for n in group}
empty = ['native_touch_probe','sheng_cpufreq_probe','sheng_wifi_probe','sheng_adsp_probe',
         'sheng_battery_probe','sheng_audio_probe','sheng_buttons_probe','sheng_backlight_probe','sheng_dpu_probe',
         'native_touch_set_sink','native_buttons_set_sink']
stub_symbols = {}
for name in empty:
    addr = names.get('_'+name)
    assert addr, 'Missing expected board hook: '+name
    offset = backed_offset(image['segments'],addr,4,len(blob))
    assert blob[offset:offset+4]==bytes.fromhex('c0035fd6'), 'Hook no longer an empty return: '+name
    stub_symbols[name] = {'address':hex(addr),'instruction':'ret','bytes':'c0035fd6'}
board = tomllib.loads((DEVICE/'board.toml').read_text())
photo_sha = sha(PHOTO)
report = {
    'date':'2026-10-28','device':'venus','kernel_sha256':candidate['kernel_sha256'],
    'boot_sha256':candidate['boot_sha256'],'components':board['components']['include'],
    'boot_args':candidate['args'],'empty_hooks_verified_in_final_kernel':stub_symbols,
    'stub_source_sha256':sha(stubs),
    'coverage':{
        'ufs':'Capacity/GPT/known reads and owner-root/userspace observed on phone; current snapshot reports zero I/O/integrity failures. Not full storage qualification.',
        'persistent_data':'Bounded store implementation and mode2 selected; a defined cross-reboot write/readback test remains unverified.',
        'display':'Firmware scanout and native service initialization observed; zero OS swaps/copies and no lock screen. FrontBoardServices rejects a display mode.',
        'hid':'Offline keyboard/Home service initialized; no physical touch/button producer or event-delivery proof.',
        'a660':'GMU/GX/CP/ZAP/publication and two bounded client submission checks observed; Metal and rendered-frame presentation incomplete.',
        'motion_light_proximity_magnetic_sensors':'No board-specific sensor backend selected/implemented in this port, and no physical samples or OS sensor events verified.',
        'battery_thermal_charging_telemetry':'Board battery probe is empty; no OS battery/thermal sensor qualification. Firmware charging behavior is separate.',
        'wifi_bluetooth_audio_camera_gnss':'No working board-to-OS integration verified; Wi-Fi/ADSP/audio entry points are empty.',
        'cpu_power':'Single boot CPU/timer active; CPU DVFS callback empty, secondary CPU and suspend/resume qualification incomplete.',
        'watchdog':'No verified Venus hardware-watchdog backend; watchdogd SIGTRAP is visible.',
        'kernel_log_export':'Reserved region/interfaces verified on host; writer/reader/manual retrieval not completed.'
    },
    'evidence':{'ufs':'evidence/ufs-read-device-verified.json','gpu':'evidence/a660-live-phone.json',
                'hid_aks':'evidence/hid-phone.json','latest_photo':'G:/20261028_102002.JPG',
                'latest_photo_sha256':photo_sha},
    'sensor_assessment_scope':'Current selected components, board package, final no-op hooks and recorded observations; no claim that a DT node or generic Apple framework constitutes a working sensor driver.',
    'device_commands_executed':False,
}
(DEVICE/'evidence/driver-coverage.json').write_text(json.dumps(report,indent=2)+'\n')

record_path = DEVICE/'evidence/frontboard-mode-phone.json'
record = load(record_path)
assert record['image_sha256']==candidate['boot_sha256']
record.update(photos=['G:/20261028_102002.JPG'],photo_sha256=photo_sha,observed={
    'screen_seconds':129,'root_accepted':1,'ufs_verified_4k_blocks':897260,
    'ufs_failures':0,'ufs_integrity_failures':0,'gpu_stage':'0xa4',
    'aks':{'stage':3,'status':0,'opens':35,'calls':121},
    'hid':{'stage':3,'load_status':0,'match_status':0,'resource_found':1,'meta_status':0,'start_count':1,'start_result':0},
    'swap_calls':0,'copy_calls':0,'latest_detailed_crash_process':'watchdogd',
    'latest_detailed_crash_pid':121,'latest_detailed_esr':'0xf2000001',
    'springboard_sigtrap_pids_in_recent_failures':[145,150],
    'mode_fields_visible':False,'mode_capture_succeeded':None,'lock_screen_visible':False,
},pending='Retain the targeted SpringBoard mode record independently of later crashes, and complete reliable log retrieval. This photo does not reveal the rejected mode values.',
    conclusion='The ordinary CRASH page shows the newest crash (watchdogd), while SpringBoard SIGTRAP remains in the recent-exit list. No MODE values are visible. This does not demonstrate that the SpringBoard mode copy failed or that its parameters were valid.')
record['limits'].append('The detailed-crash display selects the newest entry; earlier SpringBoard details may still exist in the bounded ring but are not visible in this photograph.')
record_path.write_text(json.dumps(record,indent=2)+'\n')
print('Audited',len(stub_symbols),'empty board hooks in the exact tested kernel')
print('UFS is partially device-verified; physical sensor/input coverage remains incomplete')
print('Recorded photo:',photo_sha,'(watchdogd detailed crash; MODE unavailable)')
