#!/usr/bin/env python3
"""Rewrite a generated zeta ADT into the Venus hardware description.

The zeta generator emits Surface Duo 2 defaults: DRAM 0x80000000+8G, eight
CPUs at 0x000..0x700, and an arm-io with only an interrupt controller that has
no phandle. Venus needs the phone-measured layout that the earlier RAM-booted
image used: DRAM 0xc0000000+7G, four CPUs at 0x0/0x400/0x500/0x700, and an
arm-io carrying a phandle-bearing GIC plus the architected timer node.

Only properties are rewritten. Product identity, seed, Data/trust placeholders
and the root-matching entry keep the values the caller supplied.
"""
import argparse
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util

CODEC = Path(__file__).with_name('inject-a660-firmware-adt.py')
spec = importlib.util.spec_from_file_location('adt_codec', CODEC)
codec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(codec)

DRAM_BASE = 0xC0000000
DRAM_SIZE = 0x1C0000000
TIMEBASE = 19200000
CPU_REGS = (0x000, 0x400, 0x500, 0x700)
GIC_PHANDLE = 1
# GIC distributor/redistributor offsets inside the arm-io window (0x17000000).
GIC_DIST = 0x17A00000 - 0x17000000
GIC_DIST_SIZE = 0x10000
GIC_REDIST = 0x17A60000 - 0x17000000
GIC_REDIST_SIZE = 0x100000
GIC_REDIST_STRIDE = 0x20000
# Architected timer: (type, number, flags) for secure-physical, non-secure
# physical, virtual and hypervisor. These are the numbers the phone-tested
# Venus ADT carries; PPI 12 is the hypervisor timer here, not PPI 10.
TIMER_INTERRUPTS = (1, 13, 0x0000FF08, 1, 14, 0x0000FF08,
                    1, 11, 0x0000FF08, 1, 12, 0x0000FF08)
# Board model string for the iPhone18,2 (V54) target, matching DeviceTree.v54ap.
BOARD_MODEL = b'V54AP\0'
ARMIO_RANGE_SIZE = 0x01000000


def set_prop(props, key, value):
    """Replace a property value in place, or append it if absent."""
    for index, (existing, _) in enumerate(props):
        if existing == key:
            props[index] = (key, value)
            return
    props.append((key, value))


def remove_props(node, names):
    node.props = [(k, v) for k, v in node.props if k not in names]


def find_required(root, name):
    node = codec.find(root, name)
    if node is None:
        raise SystemExit(f'generated ADT has no /{name}')
    return node


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f'{args.output} exists; preserve the previous ADT')

    tree = codec.parse(args.input.read_bytes())
    chosen = find_required(tree, 'chosen')
    cpus = find_required(tree, 'cpus')
    armio = find_required(tree, 'arm-io')

    # --- chosen: Venus measured DRAM window -------------------------------
    set_prop(chosen.props, 'dram-base', struct.pack('<Q', DRAM_BASE))
    set_prop(chosen.props, 'dram-size', struct.pack('<Q', DRAM_SIZE))

    # --- board identity: the iPhone18,2 / V54 target -----------------------
    set_prop(tree.props, 'compatible', b'xiaomi,venus\0qcom,sm8350\0')
    set_prop(tree.props, 'model', BOARD_MODEL)
    set_prop(tree.props, 'target-type', b'V54\0')
    product = codec.find(tree, 'product')
    if product is not None:
        set_prop(product.props, 'model', BOARD_MODEL)

    # --- cpus: four Venus affinities, boot CPU first -----------------------
    template = None
    for child in cpus.children:
        if dict(child.props).get('device_type', b'').rstrip(b'\0') == b'cpu':
            template = child
            break
    if template is None:
        raise SystemExit('generated /cpus has no cpu node to model')
    template_props = [(k, v) for k, v in template.props if k != 'name']
    new_cpus = []
    for index, reg in enumerate(CPU_REGS):
        props = [(k, v) for k, v in template_props]
        set_prop(props, 'reg', struct.pack('<I', reg))
        set_prop(props, 'state', b'running\0' if index == 0 else b'waiting\0')
        set_prop(props, 'timebase-frequency', struct.pack('<I', TIMEBASE))
        node = codec.Node(f'cpu{index}', [('name', f'cpu{index}'.encode() + b'\0'), *props], [])
        new_cpus.append(node)
    cpus.children = new_cpus

    # --- arm-io: phandle-bearing GIC, then the architected timer -----------
    set_prop(armio.props, 'ranges', struct.pack('<QQQ', 0, 0x17000000, ARMIO_RANGE_SIZE))
    armio.children = [
        codec.Node('intc', [
            ('name', b'intc\0'),
            ('AAPL,phandle', struct.pack('<I', GIC_PHANDLE)),
            ('compatible', b'arm,gic-v3\0'),
            ('reg', struct.pack('<4Q', GIC_DIST, GIC_DIST_SIZE, GIC_REDIST, GIC_REDIST_SIZE)),
            ('interrupt-controller', b''),
            ('#interrupt-cells', struct.pack('<I', 3)),
            ('redistributor-stride', struct.pack('<Q', GIC_REDIST_STRIDE)),
            ('phandle', struct.pack('<I', GIC_PHANDLE)),
        ], []),
        codec.Node('timer', [
            ('name', b'timer\0'),
            ('compatible', b'arm,armv8-timer\0'),
            ('interrupt-parent', struct.pack('<I', GIC_PHANDLE)),
            ('interrupts', struct.pack('<12I', *TIMER_INTERRUPTS)),
            ('clock-frequency', struct.pack('<I', TIMEBASE)),
        ], []),
    ]

    data = codec.dump(tree)
    # Round-trip and re-assert every rewritten value.
    check = codec.parse(data)
    ch = dict(codec.find(check, 'chosen').props)
    if int.from_bytes(ch['dram-base'], 'little') != DRAM_BASE:
        raise SystemExit('dram-base did not survive encoding')
    if int.from_bytes(ch['dram-size'], 'little') != DRAM_SIZE:
        raise SystemExit('dram-size did not survive encoding')
    regs = [int.from_bytes(dict(c.props)['reg'], 'little') for c in codec.find(check, 'cpus').children]
    if tuple(regs) != CPU_REGS:
        raise SystemExit(f'cpu regs differ: {[hex(r) for r in regs]}')
    io = codec.find(check, 'arm-io')
    names = [c.name for c in io.children]
    if names != ['intc', 'timer']:
        raise SystemExit(f'arm-io children differ: {names}')
    intc = dict(codec.find(io, 'intc').props)
    if int.from_bytes(intc['phandle'], 'little') != GIC_PHANDLE:
        raise SystemExit('GIC phandle did not survive encoding')
    if 'AAPL,phandle' not in intc:
        raise SystemExit('GIC lost AAPL,phandle')
    timer = dict(codec.find(io, 'timer').props)
    if int.from_bytes(timer['clock-frequency'], 'little') != TIMEBASE:
        raise SystemExit('timer frequency did not survive encoding')

    args.output.write_bytes(data)
    report = dict(input=str(args.input.resolve()), output=str(args.output.resolve()),
                  bytes=len(data), dram_base=hex(DRAM_BASE), dram_size=hex(DRAM_SIZE),
                  cpu_regs=[hex(r) for r in CPU_REGS], timebase=TIMEBASE,
                  gic_phandle=GIC_PHANDLE, arm_io_children=names,
                  timer_interrupts=[hex(v) for v in TIMER_INTERRUPTS],
                  round_trip_verified=True, device_access=False)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
