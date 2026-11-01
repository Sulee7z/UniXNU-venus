#!/usr/bin/env python3
"""Audit the current Venus prelink for the original mobile-graphics family ABI.

This is the sheng audit logic applied to the full Venus kernel. It only claims
static original-code/vtable layout; it does not claim a runtime class instance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
DEFAULT_KERNEL = ROOT / 'kernel/kernel.macho'
DEFAULT_PLAN = ROOT / 'kernel/kernel.json'
OUT = Path('/mnt/g/UniXNU-Port/artifacts/venus-exit-fault/display-analysis/mobile-graphics-legacy-abi.json')
FAMILY = 'com.apple.iokit.IOMobileGraphicsFamily'
FAMILY_TEXT_SHA = '2e044ee68c1650397e1435234ca6459206262e4c7ed709cb7131c6f664f9bd9b'
SHENG_CLASS = {
    'base_vptr_pc': 0xfffffff00577b324,
    'service_vptr_pc': 0xfffffff00577b51c,
    'legacy_vptr_pc': 0xfffffff0057865d8,
    'legacy_ctor_branch': 0xfffffff0057865fc,
    'service_ctor': 0xfffffff00577b510,
    'base_ctor': 0xfffffff00577b318,
    'base_ctor_branch': 0xfffffff00577b540,
    'legacy_new_user_client': 0xfffffff006b35940,
    'legacy_parent': 0xfffffff006b31400,
    'legacy_size': 0x18a0,
}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--kernel', type=Path, default=DEFAULT_KERNEL)
parser.add_argument('--plan', type=Path, default=DEFAULT_PLAN)
parser.add_argument('--output', type=Path, default=OUT)
args = parser.parse_args()
sys.path.insert(0, str(ROOT / 'tree/kits/XnuPrelink'))
from native_prelink import macho, backed_offset, exports


def need(value, why):
    if not value:
        raise SystemExit(why)


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


blob = args.kernel.read_bytes()
plan = json.loads(args.plan.read_text())
image = macho(blob)
need(sha(blob) == plan.get('native_sha256') or sha(blob) == plan.get('candidate_sha256'),
     'Kernel bytes do not match the prelink plan')
text = next((entry for entry in plan['extents'] if entry['module'] == FAMILY and entry['segment'] == '__TEXT_EXEC'), None)
need(text is not None, 'No IOMobileGraphicsFamily __TEXT_EXEC extent')


def read(va, size):
    at = backed_offset(image['segments'], va, size, len(blob))
    return blob[at:at + size]


family_text = read(text['va'], text['size'])
need(sha(family_text) == FAMILY_TEXT_SHA,
     'The Venus original IOMobileGraphicsFamily text differs from the sheng reference')
names = {name: value for value, group in exports(blob, image).items() for name in group}


def vptr(pc):
    a, b, c = struct.unpack('<3I', read(pc, 12))
    need(a & 0x9f00001f == 0x90000008 and b & 0xffc003ff == 0x91000108 and c == 0x91004108,
         'Actual constructor ADRP/ADD/vptr header differs at ' + hex(pc))
    imm = ((a >> 5) & 0x7ffff) * 4 + ((a >> 29) & 3)
    if imm & (1 << 20):
        imm -= 1 << 21
    return (pc & ~4095) + (imm << 12) + ((b >> 10) & 4095) + 16


def branch(pc):
    word = struct.unpack('<I', read(pc, 4))[0]
    need(word & 0xfc000000 == 0x94000000, 'Actual direct constructor call expected at ' + hex(pc))
    value = word & 0x3ffffff
    return pc + 4 * (value - (1 << 26) if value & (1 << 25) else value)


base_vptr = vptr(SHENG_CLASS['base_vptr_pc'])
service_vptr = vptr(SHENG_CLASS['service_vptr_pc'])
legacy_vptr = vptr(SHENG_CLASS['legacy_vptr_pc'])
need(branch(SHENG_CLASS['legacy_ctor_branch']) == SHENG_CLASS['service_ctor'] and
     branch(SHENG_CLASS['base_ctor_branch']) == SHENG_CLASS['base_ctor'],
     'The original Legacy -> Service -> Framebuffer constructor chain differs')
base = struct.unpack('<262Q', read(base_vptr, 262 * 8))
service = struct.unpack('<262Q', read(service_vptr, 262 * 8))
legacy = struct.unpack('<358Q', read(legacy_vptr, 358 * 8))
need([i for i, (a, b) in enumerate(zip(base, service)) if a != b] == [0, 1, 7],
     'Service adds unexpected operational overrides')
need(all(legacy) and read(legacy_vptr + 358 * 8, 24) == bytes(24),
     'Legacy vtable does not have the qualified 358-entry extent')
pure = [i for i, va in enumerate(legacy) if va == names['___cxa_pure_virtual']]
need(pure == [211, 213, 245, 246, 306, 307, 337, 338, 345],
     'The original abstract method slots differ')
changed = [i for i, (a, b) in enumerate(zip(base, legacy)) if a != b]
need(len(changed) == 103 and [i for i in changed if i < 168] ==
     [0, 1, 7, 14, 21, 44, 79, 85, 86, 87, 111, 141, 155],
     'The original generic implementation override set differs')
need(names['__ZN9IOService13newUserClientEP4taskPvjPP12IOUserClient'] == base[141],
     'The original newUserClient slot does not match the native ABI')
for i, va in enumerate(legacy):
    if i >= 168 and i not in pure:
        need(text['va'] <= va < text['va'] + text['size'],
             'An inherited generic method is outside the original family text')
args.output.parent.mkdir(parents=True, exist_ok=True)
result = {
    'kernel_sha256': sha(blob),
    'original_sha256': plan.get('original_sha256'),
    'shas': {'family_text': sha(family_text)},
    'family_text_extent': {'va': hex(text['va']), 'size': text['size']},
    'base_vptr': hex(base_vptr), 'service_vptr': hex(service_vptr), 'legacy_vptr': hex(legacy_vptr),
    'legacy_instance_bytes': SHENG_CLASS['legacy_size'], 'legacy_virtual_entries': 358,
    'abstract_slots': pure, 'inherited_generic_changes': changed,
    'source_service_operation_overrides': 0,
    'original_new_user_client': hex(legacy[141]),
    'original_init': hex(legacy[21]), 'original_start': hex(legacy[86]),
    'original_stop': hex(legacy[87]),
    'new_user_client_abi': 'IOService::newUserClient(task_t,void*,UInt32,IOUserClient**)',
    'original_client_initializer': hex(0xfffffff005776810),
    'methods': [dict(slot=i, address=hex(va), abstract=i in pure, prototype_qualified=False)
                for i, va in enumerate(legacy)],
    'static_dispatch_audit': True,
    'legacy_runtime_instance_created': False,
    'backend_contract_complete': False,
    'original_instructions_modified': False,
    'desktop': False,
    'scope': 'Static audit only: the original family text and method table match the previously qualified reference. It does not prove that the current Venus kernel creates the class, publishes a display service or scans out a frame.',
}
args.output.write_text(json.dumps(result, indent=2) + '\n')
print('PASS: current Venus original family text and 358-slot Legacy layout match the static reference')
print('PASS: original constructor chain, pure slots and generic overrides verified')
print('NOT CLAIMED: runtime instance, display publication, scanout or desktop')
