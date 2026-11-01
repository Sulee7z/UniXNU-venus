"""Execute one explicitly authorized unixnu flash and matching RAM boot."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

root = Path('G:/UniXNU-Port')
device = root/'ports/UniXNU-venus'
inputs = root/'artifacts/venus-deployment'
boot_dir = root/'artifacts/venus-ufs-root/phone'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--execute-authorized', action='store_true')
args = parser.parse_args()
plan = json.loads((inputs/'root-flash-plan.json').read_text())
boot = json.loads((boot_dir/'verification.json').read_text())
sparse = inputs/'unixnu-root.sparse.img'
boot_image = boot_dir/'boot-venus-unixnu.img'
def need(ok, message):
    if not ok: raise RuntimeError(message)
def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
need(plan['partition'] == 'unixnu' and plan['dont_care_blocks'] == 0 and
     plan['independent_expanded_sha256'] == plan['expanded_sha256'] ==
     '08bd7c4cdbe9519f75025fad65deb683d7dc2891339cd1e3e6dfb26852227bdc', 'Wrong complete root transfer plan')
need(sparse.stat().st_size == plan['sparse_bytes'] and sha(sparse) == plan['sparse_sha256'], 'Sparse image changed')
need(boot_image.stat().st_size == boot['bytes'] and sha(boot_image) == boot['sha256'], 'Boot image changed')
if not args.execute_authorized:
    print('PASS: exact full-root sparse and boot image identities; no device operations')
    raise SystemExit(0)
authorization = json.loads((device/'evidence/root-flash-authorization.json').read_text())
need(authorization.get('approved_by_user') is True and authorization.get('serial') == '55870427' and
     authorization.get('target_partition') == 'unixnu' and
     authorization.get('sparse_sha256') == plan['sparse_sha256'] and
     authorization.get('boot_sha256') == boot['sha256'], 'No matching authorization')
journal = device/'evidence/root-flash-execution.json'
need(not journal.exists(), 'Execution journal exists; inspect the previous operation before any repeat')
adb = [str(root/'tools/platform-tools/adb.exe'), '-P','5037','-s','55870427']
fastboot = [str(root/'tools/platform-tools/fastboot.exe'), '-s','55870427']
log_path = root/'logs/venus-ios-root-device-commands.log'
record = {'serial':'55870427','sparse_sha256':plan['sparse_sha256'],'boot_sha256':boot['sha256'],
          'root_flash_started':False,'root_flash_completed':False,'ram_boot_completed':False,
          'root_mount_verified':False,'raw_readback_verified':False,'commands':[],'command_log':str(log_path)}
def save(phase):
    record['phase'] = phase; record['updated_at'] = datetime.now(timezone.utc).isoformat()
    temporary = journal.with_suffix('.new')
    with temporary.open('w',encoding='utf-8') as f:
        json.dump(record,f,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(temporary,journal)
    print(phase,flush=True)
def command(argv, timeout=30, capture=True):
    with log_path.open('ab') as log:
        log.write(('\nCOMMAND '+json.dumps(argv)+'\n').encode()); log.flush()
        if capture:
            result = subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
            log.write(result.stdout); text=result.stdout.decode('utf-8','replace')
        else:
            result = subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=timeout); text=''
        log.flush(); os.fsync(log.fileno())
    record['commands'].append({'argv':argv,'exit_code':result.returncode,'output':text if capture else 'see command log'})
    need(result.returncode == 0, 'Device command failed: '+json.dumps(argv))
    return text
def variable(name):
    text = command([*fastboot,'getvar',name])
    match = re.search(r'(?:^|\n)\s*(?:\(bootloader\)\s*)?'+re.escape(name)+r':\s*(\S+)',text)
    need(match is not None,'Missing fastboot variable: '+name)
    return match.group(1)
try:
    need(command([*adb,'shell','getprop','ro.product.device']).strip() == 'venus','Unexpected Android device')
    need(command([*adb,'shell','getprop','sys.boot_completed']).strip() == '1','Android boot is not confirmed')
    save('android-verified')
    save('reboot-to-bootloader-requested')
    command([*adb,'reboot','bootloader'])
    deadline = time.monotonic()+90
    while time.monotonic() < deadline:
        result = subprocess.run([*fastboot,'devices'],capture_output=True,timeout=10)
        if result.returncode == 0 and any(line.split()[:1] == [b'55870427'] for line in result.stdout.splitlines()): break
        time.sleep(2)
    else: raise RuntimeError('Bootloader did not reconnect; no automatic reboot/flash retry')
    need(variable('product') == 'venus','Wrong bootloader product')
    need(variable('current-slot').lstrip('_') == 'a','Prepared firmware inputs require slot a')
    userdata = int(variable('partition-size:userdata'),0)
    unixnu = int(variable('partition-size:unixnu'),0)
    need(userdata == 172426788864 and unixnu == 68719476736,'Post-reset partition sizes differ from applied plan')
    need(variable('partition-type:unixnu') == 'raw','Unexpected unixnu partition type')
    record['post_reset_geometry'] = {'userdata_bytes':userdata,'unixnu_bytes':unixnu,'matched_plan':True}
    save('post-reset-geometry-verified')
    need(plan['expanded_bytes'] <= unixnu,'Root exceeds unixnu')
    record['root_flash_started'] = True
    save('root-flash-started')
    command([*fastboot,'-S','128M','flash','unixnu',str(sparse)],timeout=1800,capture=False)
    record['root_flash_completed'] = True
    save('root-flash-completed')
    need(sha(boot_image) == authorization['boot_sha256'],'Boot input changed before RAM boot')
    save('root-ram-boot-requested')
    command([*fastboot,'boot',str(boot_image)],timeout=120)
    record['ram_boot_completed'] = True
    save('root-ram-boot-completed-awaiting-screen')
except Exception as error:
    record['error'] = str(error)
    save('stopped-review-required')
    raise
