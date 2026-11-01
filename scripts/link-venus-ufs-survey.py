#!/usr/bin/env python3
"""Install the checked UFS archive and, for root, its audit-bound support providers."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

survey = os.environ.get('XNU_VENUS_UFS_SURVEY') == '1'
block_read = os.environ.get('XNU_VENUS_UFS_READ_PROBE') == '1'
root_boot = os.environ.get('XNU_VENUS_UFS_ROOT') == '1'
if sum((survey, block_read, root_boot)) > 1:
    raise SystemExit('Choose exactly one UFS build mode')
if not survey and not block_read and not root_boot:
    print('Venus UFS diagnostic/root mode not selected')
    raise SystemExit(0)
if os.environ.get('XNU_NATIVE_UFS') != '1':
    raise SystemExit('UFS configuration must select the native UFS personality')
root = Path(__file__).resolve().parents[1]
stem = 'venus-ufs-root-' if root_boot else 'venus-ufs-read-' if block_read else 'venus-ufs-survey-'
source = Path('/mnt/g/UniXNU-Port/artifacts') / (stem + 'unixnu')
report = json.loads((source / 'venus-build.json').read_text())
archive = source / 'libShengUfs.a'
same_mode = (bool(report['readonly_survey']) == survey and bool(report.get('block_read_probe')) == block_read and
             bool(report.get('root_boot')) == root_boot)
if (not same_mode or report['unresolved_kernel_imports'] or
        hashlib.sha256(archive.read_bytes()).hexdigest() != report['archive_sha256']):
    raise SystemExit('UFS archive does not match the selected qualified mode')
device = Path('/mnt/g/UniXNU-Port/ports/UniXNU-venus')
if block_read or root_boot:
    expected = 5 if block_read else 2
    if len(report.get('host_tests', {})) < expected or not report.get('device_inputs'):
        raise SystemExit('UFS qualification record is incomplete')
    for name, digest in report['device_inputs'].items():
        if hashlib.sha256((device / name).read_bytes()).hexdigest() != digest:
            raise SystemExit('UFS source changed after qualification: ' + name)
if root_boot:
    support = source / 'support'
    root_record = json.loads((source / 'root-support.json').read_text())
    if root_record != report.get('root_support'):
        raise SystemExit('Root archive and support receipts describe different builds')
    for name, digest in root_record['files'].items():
        if hashlib.sha256((support / name).read_bytes()).hexdigest() != digest:
            raise SystemExit('Root support provider changed: ' + name)
    deployment = json.loads((Path('/mnt/g/UniXNU-Port/artifacts/venus-deployment/unixnu-root.json')).read_text())
    if root_record['root_image_sha256'] != deployment['image_sha256']:
        raise SystemExit('Root providers do not cover the qualified root image')
    virtio = support / 'VirtioMmioBlock'
    ram = support / 'RamBlock'
    verified = support / 'VerifiedRoot'
    for target, files in [(root / 'build/virtio-mmio-block', ('libVirtioMmioBlock.a', 'NativeVirtioBlock.o', 'bindings.json')),
                          (root / 'build/ram-block', ('libRamBlock.a', 'NativeRamBlock.o', 'bindings.json')),
                          (root / 'build/verified-root-xnu', ('libVerifiedRootProbe.a',))]:
        target.mkdir(parents=True, exist_ok=True)
        origin = virtio if target.name == 'virtio-mmio-block' else ram if target.name == 'ram-block' else verified
        for name in files:
            relative = str((origin / name).relative_to(support))
            if relative not in root_record['files']:
                raise SystemExit('Unqualified root support input: ' + relative)
            shutil.copy2(origin / name, target / name)
    # The legacy base's binding audit expects the component-name object next
    # to the archive (it strips "lib" from the archive stem). The format-2
    # support build names the same compiled object after its source file.
    shutil.copy2(virtio / 'NativeVirtioBlock.o', root / 'build/virtio-mmio-block' / 'VirtioMmioBlock.o')
    shutil.copy2(ram / 'NativeRamBlock.o', root / 'build/ram-block' / 'RamBlock.o')
    # Build the device's publication-order patch from the original RamBlock
    # source after checking the historical support, preserving those inputs.
    subprocess.run(['python3', device / 'scripts/build-venus-ram-block.py',
                    '--tree', root, '--support', support], check=True)
out = root / 'build/sheng-ufs'
out.mkdir(parents=True, exist_ok=True)
for name in ('libShengUfs.a', 'bindings.json', 'venus-build.json'):
    shutil.copy2(source / name, out / name)
print('Installed checked UFS mode:', 'root' if root_boot else 'block-read' if block_read else 'register-survey',
      report['archive_sha256'])
