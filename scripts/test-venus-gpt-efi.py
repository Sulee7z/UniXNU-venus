"""Execute the compiled GPT tool on a sparse synthetic disk in QEMU, never a phone."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

root = Path('/mnt/g/UniXNU-Port')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--menu-chain', action='store_true', help='Boot exact UniXNU and discover the actual separate payload')
args = parser.parse_args()
inputs = root / 'artifacts/venus-deployment'
tool = inputs / ('gpt-apply-label' if args.menu_chain else 'gpt-apply')
plan = json.loads((inputs / 'partition-preview.json').read_text())
work = Path('/root/unixnu-build/venus-gpt-efi-test' + ('-menu' if args.menu_chain else ''))
work.mkdir(exist_ok=True)
disk = work / 'synthetic-lun0.raw'
if disk.exists(): raise SystemExit('Preserve the existing synthetic run before another test')
primary = (inputs / 'gpt-primary.before').read_bytes()
backup = (inputs / 'gpt-backup.before').read_bytes()
backup_offset = plan['disk_bytes'] - len(backup)
with disk.open('xb') as f:
    f.truncate(plan['disk_bytes']); f.write(primary); f.seek(backup_offset); f.write(backup)
stage = work / 'esp/EFI/BOOT'; stage.mkdir(parents=True, exist_ok=True)
shutil.copy2(tool / ('UniXNU.efi' if args.menu_chain else 'VenusPartition.efi'), stage / 'BOOTAA64.EFI')
sys.path.insert(0, str(root / 'sources/UniXNU-guide/scripts'))
from unixnu.payload import write_volume
esp = work / 'esp.img'
write_volume(work / 'esp', esp, 'GPTTEST', 64)
log = work / 'serial.log'
command = ['qemu-system-aarch64', '-machine', 'virt,gic-version=3', '-cpu', 'cortex-a710', '-accel', 'tcg',
           '-m', '512', '-bios', '/root/unixnu-build/qemu-firmware/edk2-aarch64-code.fd',
           '-nic', 'none', '-display', 'none', '-monitor', 'none', '-serial', 'file:' + str(log), '-no-reboot',
           '-global', 'virtio-mmio.force-legacy=false',
           '-drive', f'if=none,id=esp,file={esp},format=raw,readonly=on', '-device', 'virtio-blk-device,drive=esp',
           '-drive', f'if=none,id=target,file={disk},format=raw',
           '-device', 'virtio-blk-device,drive=target,logical_block_size=4096,physical_block_size=4096']
if args.menu_chain:
    command += ['-device', 'ramfb', '-drive', f'if=none,id=payload,file={tool / "payload.img"},format=raw,readonly=on',
                '-device', 'virtio-blk-device,drive=payload']
(work / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
with (work / 'qemu.log').open('w') as errors:
    process = subprocess.Popen(command, stdout=errors, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            text = log.read_text(errors='replace') if log.exists() else ''
            if 'VENUS_GPT_COMMITTED_AND_READBACK_OK' in text: break
            if 'REFUSED:' in text or 'STOP: failed' in text or process.poll() is not None:
                raise SystemExit('EFI test refused or exited; inspect ' + str(log))
            time.sleep(1)
        else: raise SystemExit('EFI test timed out; inspect ' + str(log))
    finally:
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
with disk.open('rb') as f:
    if f.read(len(primary)) != (inputs / 'gpt-primary.preview').read_bytes(): raise SystemExit('Primary writeback mismatch')
    f.seek(backup_offset)
    if f.read(len(backup)) != (inputs / 'gpt-backup.preview').read_bytes(): raise SystemExit('Backup writeback mismatch')
    # Inspect allocated extents only; all bytes outside GPT regions must stay zero.
    position = 0; scanned = 0
    while position < plan['disk_bytes']:
        try: start = os.lseek(f.fileno(), position, os.SEEK_DATA)
        except OSError: break
        end = os.lseek(f.fileno(), start, os.SEEK_HOLE)
        lo, hi = max(start, len(primary)), min(end, backup_offset)
        if hi > lo:
            scanned += hi-lo
            if scanned > 16 << 20: raise SystemExit('Unexpected allocation outside GPT')
            f.seek(lo)
            if any(f.read(hi-lo)): raise SystemExit('Unexpected non-GPT write')
        position = end
record = {'efi_sha256': hashlib.sha256((tool / 'VenusPartition.efi').read_bytes()).hexdigest(),
          'boot_image_sha256': json.loads((tool / 'gpt-tool.json').read_text())['image_sha256'],
          'synthetic_disk_bytes': plan['disk_bytes'], 'block_bytes': 4096,
          'compiled_efi_executed': True, 'unixnu_menu_chain_executed': args.menu_chain,
          'actual_payload_sha256': hashlib.sha256((tool / 'payload.img').read_bytes()).hexdigest() if args.menu_chain else None,
          'primary_and_backup_match_preview': True,
          'non_gpt_allocated_bytes_zero': True, 'serial_log': str(log), 'phone_tested': False}
(root / ('ports/UniXNU-venus/evidence/gpt-efi-' + ('menu-' if args.menu_chain else '') + 'host-test.json')).write_text(json.dumps(record, indent=2) + '\n')
os.sync()
print(json.dumps(record, indent=2))
