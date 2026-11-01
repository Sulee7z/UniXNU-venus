#!/usr/bin/env python3
"""Verify linked UFS matching with default-off and rejected-operation QEMU controls."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess
import struct

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--block-read', action='store_true')
parser.add_argument('--suffix', choices=('', '-banks', '-init'), default='', help='Retain a separate candidate revision')
parser.add_argument('--check-existing', action='store_true', help='Validate retained same-kernel observations without rerunning QEMU')
args = parser.parse_args()
root = Path('/mnt/g/UniXNU-Port')
stem = ('ufs-read' if args.block_read else 'ufs-survey') + args.suffix
artifact = root / ('artifacts/venus-' + stem)
kernel = artifact / 'kernel/kernel.macho'
digest = hashlib.sha256(kernel.read_bytes()).hexdigest()
def need(ok, message):
    if not ok:
        raise SystemExit(message)
off = json.loads((artifact / 'qemu-off/gdb-stop.json').read_text())
need(off['kernel_sha256'] == digest and off['stop_symbol'] == '_IOFindBSDRoot' and
     not off['bounded_timeout_interrupted'], 'Default-off kernel did not reach the real root finder')
need(off['native_ufs']['probe_calls'] > 0 and off['native_ufs']['matched'] == 1 and
     off['native_ufs']['mapped'] == 0 and off['native_ufs']['probe_requested'] == 0, 'Default-off UFS path was not idle')
cases = {'off': {'stop': off['stop_symbol'], 'ufs': off['native_ufs']}}
tests = [('reject-transfer', 'native-ufs-probe=10'), ('reject-root', 'native-ufs-root=1')]
if args.block_read:
    tests.append(('preflight-refusal', 'native-ufs-probe=3 native-ufs-root=0'))
for name, extra in tests:
    out = artifact / ('qemu-' + name)
    out.mkdir(exist_ok=True)
    command = ['python3', root / 'ports/UniXNU-venus/scripts/probe-venus-prelinked.py',
               '--fixture-adt', root / 'artifacts/venus-guide-virtual-timer/qemu-shared-after.adt',
               '--kernel', kernel, '--output', out, '--armvirt', '--armdt-platform', '--armcpu',
               '--nvram-proxy', '--qemu-ramfb', '--kernel-extra-args', 'sheng-pmgr=2 ' + extra,
               '--break-symbol', '_panic', '--timeout', '60']
    if not args.check_existing:
        result = subprocess.run([str(v) for v in command], capture_output=True, text=True)
        (out / 'observer.log').write_text(result.stdout + result.stderr)
        need(result.returncode == 0, name + ': observer failed')
    report = json.loads((out / 'gdb-stop.json').read_text())
    need(report['kernel_sha256'] == digest and report['stop_symbol'] == '_panic' and
         not report['bounded_timeout_interrupted'], name + ': missing real refusal')
    prefix = 'VENUS_UFS block-read build refused' if args.block_read else 'VENUS_UFS readonly build refused'
    if name == 'preflight-refusal':
        prefix = 'VENUS UFS BLOCK READ preflight refused'
    need(report['argument_memory']['x0'].startswith(prefix), name + ': unexpected panic')
    # Darwin ARM64 variadic arguments are stack-passed, unlike generic AAPCS64.
    stack = bytes.fromhex(report['stack_bytes'])
    values = [struct.unpack_from('<I', stack, i * 8)[0] for i in range(3)]
    if name == 'preflight-refusal':
        # QEMU's unimplemented MMIO reads as all ones, so GCC can appear on
        # and allow a read-only HC mapping. Geometry/error checks must still
        # refuse before hostBringUp/DMA/queue configuration, at this exact site.
        need(values[0] & 8 and values[2] == 0 and
             report['native_ufs']['probe_requested'] == 1, name + ': missing geometry rejection')
    else:
        need(report['native_ufs']['mapped'] == 0 and report['native_ufs']['status'] == 0xe00002c7,
             name + ': operation was not rejected before mapping the controller')
        need(values[:2] == ([10, 0] if name == 'reject-transfer' else [0, 1]), name + ': wrong refused arguments')
    cases[name] = {'stop': report['stop_symbol'], 'ufs': report['native_ufs'], 'format': report['argument_memory']['x0']}
    cases[name]['variadic_values'] = values[:3 if name == 'preflight-refusal' else 2]
output = {'upstream_revision': '16e592abee8a550dec8154ed1f38b5ebc4f16213', 'kernel_sha256': digest,
           'configuration': 'venus_ufs_read_defconfig' if args.block_read else 'venus_ufs_defconfig', 'cases': cases, 'physical_hardware_read': False,
          'device_storage_write': False, 'readonly_survey_implementation': 'package/VenusUfsSurvey.h'}
(root / ('ports/UniXNU-venus/evidence/' + stem + '-controls.json')).write_text(json.dumps(output, indent=2) + '\n')
print('PASS: linked UFS default-off matching and root/transfer refusal before controller mapping')
