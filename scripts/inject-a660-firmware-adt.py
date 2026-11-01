#!/usr/bin/env python3
"""Inject the Mi 11 A660 firmware blobs into an Apple-format Venus ADT.

The probe reads /chosen/zeta-gpu-gmu, -sqe and -zap (GpuPowerProbe.cpp). The
existing ADT already carries the root/Data/trust hand-off; this only appends
the three properties to /chosen and preserves every other node byte-for-byte
at the semantic level.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path('/mnt/g/UniXNU-Port')
FIRMWARE = ROOT / 'artifacts/venus-a660-firmware'
EXPECTED = {
    'a660_gmu.bin': '6bb9360a1601253a86ee3ae1b9b916f5f1832a72d55e9b8573567f1740c94e2b',
    'a660_sqe.fw': 'f911a4badf7b56719cb130492bc39f9edb85335f54e8b4983b5c67eb9e6204bb',
    'a660_zap.elf': 'af16bbc1d443e250fc9c4e75aebd9e5af41abf894f1ed45a7b406164a150e851',
}
PROPERTIES = {'zeta-gpu-gmu': 'a660_gmu.bin', 'zeta-gpu-sqe': 'a660_sqe.fw', 'zeta-gpu-zap': 'a660_zap.elf'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class Node:
    def __init__(self, name, props, children):
        self.name = name
        self.props = props
        self.children = children


def parse(data):
    def visit(at):
        count, children_count = struct.unpack_from('<II', data, at)
        at += 8
        props = []
        for _ in range(count):
            key, size = struct.unpack_from('<32sI', data, at)
            at += 36
            if size > len(data) - at:
                raise SystemExit('truncated ADT property')
            key = key.split(b'\0')[0].decode()
            props.append((key, data[at:at + size]))
            at += (size + 3) & ~3
        names = [key for key, _ in props]
        if not names or names[0] != 'name' or len(set(names)) != len(names):
            raise SystemExit('invalid ADT node property table')
        node = Node(props[0][1].rstrip(b'\0').decode(), props, [])
        for _ in range(children_count):
            child, at = visit(at)
            node.children.append(child)
        return node, at

    node, end = visit(0)
    if end != len(data):
        raise SystemExit('unexpected ADT tail')
    return node


def dump(node):
    props = [(key, value) for key, value in node.props if key != 'name']
    props = [('name', node.name.encode() + b'\0'), *props]
    out = struct.pack('<II', len(props), len(node.children))
    for key, value in props:
        if len(key.encode()) > 31:
            raise SystemExit('ADT property name too long: ' + key)
        out += struct.pack('<32sI', key.encode(), len(value))
        out += value + bytes(-len(value) % 4)
    for child in node.children:
        out += dump(child)
    return out


def find(node, name):
    for child in node.children:
        if child.name == name:
            return child
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adt', type=Path, required=True)
    parser.add_argument('--firmware-dir', type=Path, default=FIRMWARE)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    before = args.adt.read_bytes()
    root = parse(before)
    chosen = find(root, 'chosen')
    if chosen is None:
        raise SystemExit('ADT has no /chosen')
    existing = {key for key, _ in chosen.props}
    firmware = {}
    for prop, name in PROPERTIES.items():
        path = args.firmware_dir / name
        digest = sha(path)
        if digest != EXPECTED[name]:
            raise SystemExit(f'{name}: unexpected SHA-256 {digest}')
        if prop in existing:
            raise SystemExit(f'/chosen already has {prop}')
        firmware[prop] = path.read_bytes()
        chosen.props.append((prop, firmware[prop]))

    after = dump(root)
    reparsed = parse(after)
    reparsed_chosen = find(reparsed, 'chosen')
    if reparsed_chosen is None:
        raise SystemExit('rebuilt ADT lost /chosen')
    for prop, data in firmware.items():
        if next((value for key, value in reparsed_chosen.props if key == prop), None) != data:
            raise SystemExit(f'rebuilt ADT lost {prop}')
    # Remove only the new properties and compare every original node/property,
    # preserving order and values while ignoring binary padding bytes.
    reparsed_chosen.props = [(key, value) for key, value in reparsed_chosen.props if key not in PROPERTIES]
    if dump(reparsed) != dump(parse(before)):
        raise SystemExit('rebuilt ADT changed pre-existing nodes or properties')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(after)
    report = {
        'input_adt': str(args.adt), 'input_sha256': hashlib.sha256(before).hexdigest(),
        'output_adt': str(args.output), 'output_sha256': hashlib.sha256(after).hexdigest(),
        'input_bytes': len(before), 'output_bytes': len(after),
        'pre_existing_nodes_verified': True,
        'properties': {prop: {'file': name, 'bytes': len(firmware[prop]), 'sha256': EXPECTED[name]}
                       for prop, name in PROPERTIES.items()},
        'scope': 'A660 GMU/SQE/ZAP firmware appended to /chosen; all pre-existing ADT nodes preserved.',
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
