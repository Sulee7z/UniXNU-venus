#!/usr/bin/env python3
"""Create the iOS26 Data seed and pin its APFS volume UUID for the kernel build."""
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path('/root/unixnu-build')
PLAN = ROOT / 'venus-ios26-data-plan.json'
SEED = ROOT / 'venus-ios26-data.dbr'
TOOLS = ROOT / 'venus-apfs-tools'
OS_ROOT = ROOT / 'venus-ios26-inputs/mount-OS/root'
SCRIPTS = Path('/mnt/g/UniXNU-Port/sources/UniXNU-zeta-none24smu/scripts')
PY = ROOT / 'venus-zeta-audit-venv/bin/python'

if not PLAN.exists():
    PLAN.write_text(json.dumps({
        'volume_uuid': str(uuid.uuid4()).upper(),
        'size_mib': 1024,
        'persistent': True,
        'source': str(OS_ROOT / 'private/var'),
        'note': 'Local APFS Data seed for the iOS26 candidate; excludes staged_system_apps.'
    }, indent=2) + '\n')
plan = json.loads(PLAN.read_text())
if SEED.exists():
    print('Data seed already built:', SEED, SEED.stat().st_size)
    sys.exit(0)
command = [str(PY), str(SCRIPTS / 'make-zeta-data-seed.py'),
           '--os-root', str(OS_ROOT), '--volume-uuid', plan['volume_uuid'],
           '--output', str(SEED), '--raw', str(ROOT / 'venus-ios26-data.apfs'),
           '--size-mib', str(plan['size_mib']),
           '--kernel', str(TOOLS / 'guest/boot/vmlinuz-6.8.0-147-generic'),
           '--module', str(TOOLS / 'guest/lib/modules/6.8.0-147-generic/extra/apfs.ko'),
           '--module-tree', str(TOOLS / 'guest/lib/modules/6.8.0-147-generic/kernel'),
           '--busybox', '/usr/bin/busybox',
           '--mkapfs', str(TOOLS / 'apfsprogs/mkapfs/mkapfs'),
           '--skip-setup']
print('RUN', ' '.join(command), flush=True)
import os
environment = dict(os.environ, ZETA_QEMU_ACCEL='tcg')
result = subprocess.run(command, env=environment)
if result.returncode:
    raise SystemExit(f'Data seed failed: {result.returncode}')
print('PASS: Data seed', SEED, SEED.stat().st_size)
