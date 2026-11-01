#!/usr/bin/env python3
"""Check format-2 hardware against the retained, hash-pinned Venus live FDT."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--unixnu', type=Path, required=True)
parser.add_argument('--evidence', type=Path, required=True)
parser.add_argument('--soc', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--import-reservations', action='store_true')
args = parser.parse_args()
sys.path.insert(0, str(args.unixnu / 'scripts'))
from unixnu.devicetree import read_fdt, registers, number

board = Path(__file__).resolve().parents[1]
live = args.evidence / 'live.dtb'
digest = hashlib.sha256(live.read_bytes()).hexdigest()
if digest != 'f0f1e0d1d9fc16ee520cceec87487523afc576cfb4b6b4f73ef58bc9ae3f3b2c':
    raise SystemExit('The input is not the retained Venus FDT')

def paths(root):
    result = {}
    def visit(entry, parent):
        path = parent + '/' + entry.name if entry.parent else ''
        result[path or '/'] = entry
        for child in entry.children:
            visit(child, path)
    visit(root, '')
    return result

source = paths(read_fdt(live.read_bytes()))
if source['/'].strings('model') != ['Venus based on Qualcomm Technologies, Inc SM8350']:
    raise SystemExit('Unexpected live FDT model')
reservations = []
for entry in source['/reserved-memory'].children:
    if 'reg' not in entry.properties:
        continue
    for index, (address, size) in enumerate(registers(entry)):
        if size:
            reservations.append({'name': entry.name, 'index': index, 'address': address,
                                 'size': size, 'no_map': 'no-map' in entry.properties})
if len(reservations) != 21:
    raise SystemExit('Live reservations differ from the reviewed inventory')

if args.import_reservations:
    target = board / 'dts/venus-reserved.dtsi'
    lines = ['// Generated from the hash-pinned Venus live FDT.', '/ {',
             '    reserved-memory {', '        #address-cells = <2>;',
             '        #size-cells = <2>;', '        ranges;']
    for item in reservations:
        address, size = item['address'], item['size']
        lines += [f'        region@{address:x} {{',
                  f'            reg = <0x{address >> 32:x} 0x{address & 0xffffffff:x} 0x{size >> 32:x} 0x{size & 0xffffffff:x}>;']
        if item['no_map']:
            lines.append('            no-map;')
        lines.append('        };')
    text = '\n'.join([*lines, '    };', '};', ''])
    if target.exists() and target.read_text() != text:
        raise SystemExit('Existing reservation description differs; review it before replacing')
    target.write_text(text)

args.output.mkdir(parents=True, exist_ok=True)
dtb = args.output / 'hardware.dtb'
command = ['dtc', '-I', 'dts', '-O', 'dtb', '-i', str(args.soc / 'dts'),
           '-i', str(board / 'dts'), '-o', str(dtb), str(board / 'dts/venus.dts')]
run = subprocess.run(command, capture_output=True, text=True)
(args.output / 'dtc.log').write_text(run.stdout + run.stderr)
if run.returncode:
    raise SystemExit(run.stderr)
target = paths(read_fdt(dtb.read_bytes()))
errors = []
def require(condition, message):
    if not condition:
        errors.append(message)

cpu_paths = [path for path in source if path.startswith('/cpus/cpu@') and path.count('/') == 2]
for path in cpu_paths:
    require(path in target, f'Missing CPU {path}')
    if path in target:
        require(registers(target[path]) == registers(source[path]), f'CPU affinity mismatch: {path}')
        require(target[path].strings('compatible') == source[path].strings('compatible'), f'CPU identity mismatch: {path}')
enabled = [path for path in cpu_paths if path in target and target[path].enabled()]
require(enabled == ['/cpus/cpu@0'], 'The bring-up description must enable only the measured boot CPU')
for key in ('reg', 'compatible', 'redistributor-stride'):
    path = '/soc/interrupt-controller@17a00000'
    a, b = target[path], source[path]
    require((registers(a) == registers(b)) if key == 'reg' else a.properties[key] == b.properties[key], f'GIC {key} mismatch')
for key in ('clock-frequency', 'interrupts', 'compatible'):
    require(target['/timer'].properties[key] == source['/soc/timer'].properties[key], f'Timer {key} mismatch')
require(target['/cpus'].scalar('timebase-frequency') == source['/soc/timer'].scalar('clock-frequency'), 'CPU timebase mismatch')
require(target['/psci'].properties == source['/soc/psci'].properties or
        all(target['/psci'].properties[key] == source['/soc/psci'].properties[key] for key in ('method', 'compatible')), 'PSCI mismatch')
dram = [span for entry in source.values() if entry.strings('device_type') == ['memory'] for span in registers(entry)]
handoff = registers(target['/memory@c0000000'])
require(handoff == [(0xc0000000, 0x1c0000000)] and handoff[0] in dram, 'Handoff DRAM must be the measured second bank')
actual = sorted((a, s, 'no-map' in entry.properties) for entry in target['/reserved-memory'].children for a, s in registers(entry))
expected = sorted((r['address'], r['size'], r['no_map']) for r in reservations)
require(actual == expected, 'Reserved ranges or no-map attributes differ')
result = {'live_fdt_sha256': digest, 'reference_kernel_revision': 'df169d0b934bd8e372c5c5e2ffab5f9c50f3d052',
          'dram_banks': dram, 'adt_handoff_bank': handoff, 'cpu_affinities': [registers(source[p])[0][0] for p in cpu_paths],
          'enabled_cpu_paths': enabled, 'gic': registers(source['/soc/interrupt-controller@17a00000']),
          'redistributor_stride': number(source['/soc/interrupt-controller@17a00000'].cells('redistributor-stride')),
          'timebase_hz': source['/soc/timer'].scalar('clock-frequency'), 'psci_method': 'smc',
          'reservations': reservations, 'hardware_dtb_sha256': hashlib.sha256(dtb.read_bytes()).hexdigest(),
          'dtc_command': command, 'dtc_diagnostics': run.stderr, 'errors': errors,
          'new_adt_phone_tested': False}
(args.output / 'hardware.json').write_text(json.dumps(result, indent=2) + '\n')
if errors:
    raise SystemExit('; '.join(errors))
print(f'Venus hardware checked: {len(cpu_paths)} affinities, 1 enabled CPU, {len(reservations)} reservations, GIC/timer/PSCI match')
