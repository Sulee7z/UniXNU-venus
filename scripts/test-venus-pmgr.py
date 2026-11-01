#!/usr/bin/env python3
"""Exercise the reused PMGR lifecycle, publication, unsupported-call and AMFI paths."""
import argparse
import json
import os
from pathlib import Path
import subprocess

root = Path('/mnt/g/UniXNU-Port')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--artifacts', type=Path, default=root / 'artifacts/venus-guide-pmgr')
parser.add_argument('--mode', choices=('lifecycle', 'publish', 'refusal', 'amfi'), action='append')
args = parser.parse_args()
kernel = args.artifacts / 'kernel/kernel.macho'
prelink = kernel.with_suffix('.json')
observer = root / 'ports/UniXNU-venus/scripts/probe-venus-prelinked.py'
checker = root / 'sources/UniXNU-sheng-reference/scripts/check-sheng-pmgr-observation.py'
env = dict(os.environ, PYTHONPATH=str(root / 'sources/UniXNU-guide/kits/XnuPrelink'))
for mode in args.mode or ('lifecycle', 'publish', 'refusal', 'amfi'):
    out = args.artifacts / ('qemu-' + mode)
    out.mkdir(parents=True, exist_ok=True)
    command = ['python3', str(observer), '--kernel', str(kernel), '--prelink-report', str(prelink),
        '--fixture-adt', str(root / 'artifacts/venus-guide-virtual-timer/qemu-shared-after.adt'),
        '--output', str(out), '--armvirt', '--armdt-platform', '--armcpu', '--nvram-proxy',
        '--qemu-ramfb', '--inspect-sheng-pmgr', '--timeout', '90', '--kernel-extra-args',
        'sheng-pmgr=' + {'lifecycle': '1', 'publish': '2', 'refusal': '3', 'amfi': '2'}[mode]]
    if mode == 'amfi':
        command += ['--break-address', '0xfffffff004aaeb54']
    elif mode != 'refusal':
        command += ['--break-symbol', '_sheng_pmgr_checkpoint']
    (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    (out / 'observer.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise SystemExit(f'{mode}: observer failed; see {out / "observer.log"}')
    check = ['python3', str(checker), '--kernel', str(kernel), '--observation', str(out / 'gdb-stop.json'), '--mode', mode]
    result = subprocess.run(check, capture_output=True, text=True, env=env)
    (out / 'check.log').write_text(result.stdout + result.stderr)
    print(result.stdout, end='')
    if result.returncode:
        raise SystemExit(f'{mode}: verification failed; see {out / "check.log"}')
