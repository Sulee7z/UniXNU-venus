#!/usr/bin/env python3
"""Pin original AMFI calls to an observation wrapper that returns the original result."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).parent))
from macho_support import ROOT, AMFI, nm, thin, read_va, segments, sha, capstone

TARGET = 0x476c8
MAGIC = 0x414d464930353152


def branch(source, target):
    delta = target - source
    if delta % 4 or not -(1 << 27) <= delta < 1 << 27:
        raise ValueError('Actual AMFI call is out of branch range')
    return struct.pack('<I', 0x94000000 | ((delta // 4) & 0x3ffffff))


def fileoff(data, address, size):
    matches = [row for row in segments(data) if row[0] <= address and address + size <= row[0] + row[3]]
    if len(matches) != 1:
        raise ValueError('Ambiguous emitted address')
    va, _, offset, _ = matches[0]
    return offset + address - va


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prelink', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    directory, output = args.prelink.resolve(), args.output.resolve()
    if output.exists():
        parser.error('Fresh binding output required')
    summary = json.loads((directory / 'summary.json').read_text())
    plan = json.loads((directory / 'prelink-report.json').read_text())
    kernel = directory / 'kernel.macho'
    if summary['result'] != 'passed' or not summary['emitter_gates_passed'] or summary['prelinked_sha256'] != sha(kernel):
        raise ValueError('Successful exact emission gates are required')
    module = Path(plan['layout']['modules'][AMFI]['path'])
    if sha(module) != '839a8702636914425c613c4d1d988d71aac99d5232417aad5e4b05b7a2067f98':
        raise ValueError('AMFI trace is pinned to the actual25F84 provider')
    original = thin(module.read_bytes())
    mapping = plan['layout']['mapping'][AMFI]
    def translate(address):
        rows = [row for row in mapping.values() if row['original_va'] <= address < row['original_va'] + row['size']]
        if len(rows) != 1:
            raise ValueError('AMFI original address not uniquely mapped')
        return address - rows[0]['original_va'] + rows[0]['new_va']
    callsites = []
    for va, size, offset, filesize in segments(original):
        if va != 0x20000:
            continue
        for position in range(0, filesize, 4):
            address = va + position
            word = struct.unpack_from('<I', original, offset + position)[0]
            if word & 0xfc000000 != 0x94000000:
                continue
            immediate = word & 0x3ffffff
            if immediate & (1 << 25):
                immediate -= 1 << 26
            if address + 4 * immediate == TARGET:
                callsites.append(address)
    if len(callsites) != 3:
        raise ValueError('Expected three pinned actual CE conversion callsites, got ' + str(callsites))
    native = dict((name, address) for address, name in nm(kernel))
    wrapper, slot = native['_venus_amfi051_convert'], native['_venus_amfi051_original']
    data = bytearray(kernel.read_bytes())
    slot_offset = fileoff(data, slot, 8)
    if struct.unpack_from('<Q', data, slot_offset)[0] != MAGIC:
        raise ValueError('Original converter slot does not contain its unbound sentinel')
    changes = []
    for address in callsites:
        source = translate(address)
        offset = fileoff(data, source, 4)
        old = bytes(data[offset:offset + 4])
        if old != branch(source, translate(TARGET)):
            raise ValueError('Emitted original CE call differs from its pinned target')
        new = branch(source, wrapper)
        data[offset:offset + 4] = new
        changes.append(dict(original_va=hex(address), final_va=hex(source), fileoff=offset, old=old.hex(), new=new.hex()))
    struct.pack_into('<Q', data, slot_offset, translate(TARGET))
    callback_binding = None
    if summary.get('amfi_callback063_enabled'):
        callback_plan = summary['amfi_callback063']['callback_plan']
        if callback_plan['original_amfi_sha256'] != sha(module) or callback_plan['environment_bytes'] != 80 or len(callback_plan['callbacks']) != 10:
            raise ValueError('Original063 callback environment plan differs')
        table = native['_venus_amfi063_originals']
        table_offset = fileoff(data, table, 80)
        environment = translate(0x68130)
        environment_offset = fileoff(data, environment, 80)
        targets = []
        for index, row in enumerate(callback_plan['callbacks']):
            if row['index'] != index or struct.unpack_from('<Q', data, table_offset + index * 8)[0] != 0x414d463036330000 + index:
                raise ValueError('063 callback target slot lacks its exact unbound sentinel')
            target = translate(int(row['original_va'], 16))
            if struct.unpack_from('<Q', data, environment_offset + index * 8)[0] != target:
                raise ValueError('Emitted original CE environment callback differs from the qualified target')
            struct.pack_into('<Q', data, table_offset + index * 8, target)
            targets.append(dict(index=index, original_va=row['original_va'], target=hex(target), symbol=row['symbol']))
        callback_binding = dict(result='bound-original-callbacks', environment=hex(environment),
            table=hex(table), table_fileoff=table_offset, environment_bytes=80, targets=targets,
            original_callbacks_and_results_preserved=True, phone_operations=False)
    iterator_binding = None
    if summary.get('amfi_iterator064_enabled'):
        expected = dict(original_call='0x477b8', original_word='49fbff97', iterator='0x464dc', key_callback='0x4787c',
            original_returns_and_iteration_arguments_preserved=True)
        if not callback_binding or summary['amfi_iterator064']['plan'] != expected:
            raise ValueError('064 requires its exact original iterator plan and bound063 callbacks')
        address = 0x477b8
        if read_va(original, address, 4) != bytes.fromhex(expected['original_word']):
            raise ValueError('Original064 iterator call preimage differs')
        source = translate(address); offset = fileoff(data, source, 4)
        before = bytes(data[offset:offset + 4])
        if before != branch(source, translate(0x464dc)):
            raise ValueError('Emitted064 call no longer targets the original iterator')
        wrapper064 = native['_venus_amfi064_dictionary_iterate']
        after = branch(source, wrapper064); data[offset:offset + 4] = after
        slots = []
        for index, (name, original_va) in enumerate((('iterator', 0x464dc), ('key_callback', 0x4787c))):
            slot064 = native['_venus_amfi064_' + name]; off = fileoff(data, slot064, 8)
            if struct.unpack_from('<Q', data, off)[0] != 0x414d463036340000 + index:
                raise ValueError('064 original target slot lacks its exact sentinel')
            target064 = translate(original_va); struct.pack_into('<Q', data, off, target064)
            slots.append(dict(name=name, original_va=hex(original_va), slot=hex(slot064), fileoff=off, target=hex(target064)))
        iterator_binding = dict(result='bound-original-iterator', original_call=hex(address), final_call=hex(source),
            fileoff=offset, old=before.hex(), new=after.hex(), wrapper=hex(wrapper064), slots=slots,
            original_returns_and_iteration_arguments_preserved=True, phone_operations=False)
    stack_binding = None
    if summary.get('amfi_stack065_enabled'):
        start = translate(0x462ec); offset = fileoff(data, start, 40)
        expected = bytes.fromhex('a80000d008ad44f9080140b9090080122821c81ae803282ae90300910801098a1f0102f1430c0054')
        before = read_va(data, start, 40)
        if read_va(original, 0x462ec, 40) != expected or before[8:] != expected[8:]:
            raise ValueError('CE stack-guard instructions differ from the exact original')
        decoder = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM); decoder.detail = True
        ins = list(decoder.disasm(before, start))
        got = (ins[0].operands[1].imm + ins[1].operands[1].mem.disp) & ((1 << 64) - 1)
        if got != translate(0x5c958) or struct.unpack('<Q', read_va(data, got, 8))[0] != native['_PAGE_SHIFT_CONST']:
            raise ValueError('CE stack estimate does not use the qualified native page shift')
        helper = native['_venus_amfi065_stack_guard']; refusal = translate(0x46498)
        after = bytes.fromhex('e8030091') + branch(start + 4, helper) + bytes.fromhex('1f0102f1')
        after += struct.pack('<I', 0x54000003 | (((refusal - start - 12) // 4 & 0x7ffff) << 5))
        after += bytes.fromhex('1f2003d5') * 6
        data[offset:offset + 40] = after
        stack_binding = dict(result='bound-native-stack-extent', start=hex(start), helper=hex(helper),
            refusal=hex(refusal), old=before.hex(), new=after.hex(), threshold=128,
            original_refusal_preserved=True, extra_observations=False, phone_operations=False)
    output.mkdir()
    (output / 'kernel.macho').write_bytes(data)
    binding = dict(result='bound', original_emitted_sha256=sha(kernel), output_sha256=hashlib.sha256(data).hexdigest(),
                   real_function=hex(translate(TARGET)), observation_wrapper=hex(wrapper), pointer_slot=hex(slot),
                   pointer_slot_fileoff=slot_offset, callsites=changes, original_return_preserved=True,
                   security_checks_removed=False, phone_operations=False)
    summary.update(prelinked_sha256=binding['output_sha256'], amfi_trace_binding=binding)
    if callback_binding:
        summary['amfi_callback_binding063'] = callback_binding
        (output / 'callback-binding063.json').write_text(json.dumps(callback_binding, indent=2) + '\n')
    if iterator_binding:
        summary['amfi_iterator_binding064'] = iterator_binding
        (output / 'iterator-binding064.json').write_text(json.dumps(iterator_binding, indent=2) + '\n')
    if stack_binding:
        summary['amfi_stack_binding065'] = stack_binding
        (output / 'stack-binding065.json').write_text(json.dumps(stack_binding, indent=2) + '\n')
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (output / 'binding.json').write_text(json.dumps(binding, indent=2) + '\n')
    print(json.dumps(binding, indent=2))


if __name__ == '__main__':
    main()
