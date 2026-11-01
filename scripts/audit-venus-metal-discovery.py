#!/usr/bin/env python3
"""Check the actual Venus prelink against the recorded iOS17 accelerator ABI."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path('/mnt/g/UniXNU-Port')
TREE = Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root/tree')
sys.path.insert(0, str(TREE / 'kits/XnuPrelink'))
from native_prelink import macho, backed_offset, exports


def audit(directory):
    raw = (directory / 'kernel.macho').read_bytes()
    image = macho(raw)
    plan = json.loads((directory / 'kernel.json').read_text())
    abi = json.loads((ROOT / 'sources/UniXNU-guide/scripts/data/ioaccelerator-base-abi.json').read_text())

    def read(address, size):
        offset = backed_offset(image['segments'], address, size, len(raw))
        return raw[offset:offset + size]

    def digest(data):
        return hashlib.sha256(data).hexdigest()

    assert digest(raw) == plan['candidate_sha256'], 'Candidate/prelink report mismatch'
    extent = next(e for e in plan['extents'] if e['module'] == 'com.apple.iokit.IOGPUFamily' and e['segment'] == '__TEXT_EXEC')
    assert digest(read(extent['va'], extent['size'])) == abi['original_iogpu_text_sha256'], 'Different original IOGPU executable'
    entries = {}
    for address, expected in abi['original_entry_sha256'].items():
        actual = digest(read(int(address, 16), 32))
        assert actual == expected, 'Different original accelerator entry: ' + address
        entries[address] = actual
    names = {n: a for a, group in exports(raw, image).items() for n in group}
    native_table = struct.unpack('<168Q', read(names['__ZTV9IOService'] + 16, 168 * 8))
    parent_table = struct.unpack('<168Q', read(int(abi['vptr'], 16), 168 * 8))
    overrides = [i for i, (a, b) in enumerate(zip(native_table, parent_table)) if a != b]
    assert overrides == [0, 1, 7], 'Different original IOService inheritance'
    assert read(int(abi['vptr'], 16) + 168 * 8, 24) == bytes(24), 'Parent vtable extent changed'
    adapter_overrides = None
    if '_native_adreno_accelerator_allocate' in names:
        adapter_table = struct.unpack('<168Q', read(names['__ZTV14AGXAccelerator'] + 16, 168 * 8))
        reverse = exports(raw, image)
        adapter_overrides = {str(i): reverse.get(a, []) for i, (a, b) in enumerate(zip(adapter_table, native_table)) if a != b}
        assert sorted(map(int,adapter_overrides)) == [0,1,7,39,40,41,140], 'Adapter may override only lifetime/meta, property reads and newUserClient'
        assert all(any('AGXAccelerator' in name for name in group) for group in adapter_overrides.values())
        for name, address in {
            '__ZN15IOAcceleratorESC2EPK11OSMetaClass': abi['protected_compatible_constructor_aliases'][0],
            '__ZN15IOAcceleratorESD2Ev': abi['nondeleting_destructor'],
            '__ZN15IOAcceleratorES10gMetaClassE': abi['metaclass'],
        }.items():
            assert names[name] == int(address, 16), 'Incorrect original-base binding'
    return {
        'kernel_sha256': digest(raw),
        'original_iogpu_text_sha256': abi['original_iogpu_text_sha256'],
        'original_entries_verified': entries,
        'instance_bytes': abi['instance_bytes'],
        'virtual_entries': 168,
        'parent_overrides': overrides,
        'adapter_overrides': adapter_overrides,
        'bindings': {
            '__ZN15IOAcceleratorESC2EPK11OSMetaClass': abi['protected_compatible_constructor_aliases'][0],
            '__ZN15IOAcceleratorESD2Ev': abi['nondeleting_destructor'],
            '__ZN15IOAcceleratorES10gMetaClassE': abi['metaclass'],
        },
        'private_gpu_service_present': '__ZN24NativeAdrenoGpuPublished10gMetaClassE' in names,
        'metal_accelerator_allocate_present': '_native_adreno_accelerator_allocate' in names,
        'phone_operations': False,
        'hardware_rendering_verified': False,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.kernel_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
