"""Keep the actual DarwinBoot allocation congruence and dense kext scan intact."""
import copy
import hashlib
import re
import struct

BLOCK = 0x200000
ROW = struct.Struct('<32sQQ4IQ')


def segments(data):
    if len(data) < 32 or struct.unpack_from('<III', data) != (0xfeedfacf, 0x100000c, 0):
        raise ValueError('Expected ordinary ARM64 Mach-O')
    count, size = struct.unpack_from('<II', data, 16)
    end, at, result = 32 + size, 32, []
    if end > len(data):
        raise ValueError('Truncated load commands')
    for _ in range(count):
        if at + 8 > end:
            raise ValueError('Truncated load command')
        kind, length = struct.unpack_from('<II', data, at)
        if length < 8 or length % 8 or at + length > end:
            raise ValueError('Invalid load command')
        if kind == 0x19:
            if length < 72:
                raise ValueError('Truncated segment')
            name, va, size, fileoff, filesize = struct.unpack_from('<16s4Q', data, at + 8)
            sections = struct.unpack_from('<I', data, at + 64)[0]
            if 72 + sections * 80 > length or fileoff + filesize > len(data) or filesize > size:
                raise ValueError('Invalid segment extent')
            result.append(dict(name=name.rstrip(b'\0').decode('ascii'), va=va, size=size,
                               fileoff=fileoff, filesize=filesize, command=at, sections=sections))
        at += length
    if at != end or not any(row['size'] for row in result):
        raise ValueError('Invalid or empty segment inventory')
    return result


def firmware_rows(data):
    """Read the named SEC descriptor array, not a manually edited receipt."""
    marker = b'Kernel RAM High\0' + bytes(16)
    matches = list(re.finditer(re.escape(marker), data))
    if len(matches) != 1:
        raise ValueError('Expected one actual high-memory descriptor')

    def row(at):
        if at < 0 or at + ROW.size > len(data):
            raise ValueError('Descriptor outside FD')
        name, address, size, hob, resource, attributes, memory, arm = ROW.unpack_from(data, at)
        if b'\0' not in name or not re.fullmatch(rb'[A-Za-z0-9 _()./-]{1,31}', name.split(b'\0', 1)[0]) or not size:
            raise ValueError('Not a named descriptor')
        if address + size > (1 << 64) or address % 4096 or size % 4096:
            raise ValueError('Invalid descriptor geometry')
        return dict(name=name.split(b'\0', 1)[0].decode(), address=address, bytes=size,
                    hob=hob, resource=resource, memory_type=memory, offset=at)

    first = matches[0].start()
    while first >= ROW.size:
        try:
            row(first - ROW.size)
        except ValueError:
            break
        first -= ROW.size
    rows, at = [], first
    while at + ROW.size <= len(data):
        try:
            rows.append(row(at))
        except ValueError:
            break
        at += ROW.size
    if len(rows) < 20:
        raise ValueError('Incomplete actual SEC map')
    return rows


def window_geometry(kernel, firmware, requested):
    if requested < 0x10000000 or requested > 0x200000000 or requested % BLOCK:
        raise ValueError('Invalid DarwinBoot window request')
    base = min(row['va'] for row in segments(kernel) if row['size'])
    rows = firmware_rows(firmware)
    free = sorted((row['address'], row['address'] + row['bytes']) for row in rows
                  if (row['hob'], row['resource'], row['memory_type']) == (1, 0, 7))
    runs = []
    for start, end in free:
        if runs and start < runs[-1][1]:
            raise ValueError('Overlapping conventional-memory descriptors')
        if runs and start == runs[-1][1]:
            runs[-1] = (runs[-1][0], end)
        else:
            runs.append((start, end))
    candidates = []
    for start, end in runs:
        candidate = ((start + BLOCK - 1) & -BLOCK) + (base & (BLOCK - 1))
        candidates.append(dict(start=start, end=end, candidate=candidate,
                               available=max(0, end - candidate),
                               fits=start <= candidate <= end and requested <= end - candidate))
    return dict(kernel_sha256=hashlib.sha256(kernel).hexdigest(),
                firmware_sha256=hashlib.sha256(firmware).hexdigest(), kernel_base=hex(base),
                congruence_offset=base & (BLOCK - 1), requested_bytes=requested,
                candidates=candidates, fits=any(row['fits'] for row in candidates),
                scope='Actual SEC static map and DarwinBoot geometry; not a live UEFI allocation',
                phone_operations=False, runtime_allocation_verified=False)


def align_layout(layout, native):
    """Add leading parent padding without rebasing any child/provider address."""
    result = copy.deepcopy(layout)
    group = result['groups'][0]
    if group['segment'] != '__PRELINK_TEXT' or group['va'] != result['vm_base']:
        raise ValueError('Expected the lowest readonly kext-header group')
    old, padding = group['va'], group['va'] & (BLOCK - 1)
    reserved = next(row['va'] for row in native.segments if row['name'] == '__PRELINK_TEXT')
    if old - padding < reserved or group['protection'] != 1:
        raise ValueError('Alignment exceeds the existing readonly prelink reservation')
    group.update(va=old - padding, size=group['size'] + padding)
    result.update(vm_base=old - padding, vm_span_bytes=result['vm_span_bytes'] + padding,
                  owned_window_alignment=dict(alignment=BLOCK, padding_bytes=padding,
                      old_base=old, new_base=old - padding,
                      scan_address=old, scan_bytes=group['size'] - padding,
                      child_addresses_unchanged=True, native_addresses_unchanged=True))
    if result['vm_span_bytes'] > 0x10000000 - BLOCK:
        raise ValueError('Aligned image exceeds the DarwinBoot kernel-span limit')
    return result


def preserve_header_scan(data, layout):
    """kalloc_type_view_parse scans the section, which must not start in padding."""
    proof = layout['owned_window_alignment']
    output = bytearray(data)
    row = next(row for row in segments(data) if row['name'] == '__PRELINK_TEXT')
    if row['sections'] != 1 or row['va'] != proof['new_base']:
        raise ValueError('Unexpected emitted kext-header segment')
    at = row['command'] + 72
    address, size, fileoff = struct.unpack_from('<QQI', data, at + 32)
    if (address, size, fileoff) != (row['va'], row['size'], row['fileoff']):
        raise ValueError('Unexpected emitted header-scan section')
    padding = proof['padding_bytes']
    if any(data[row['fileoff']:row['fileoff'] + padding]):
        raise ValueError('Prelink alignment padding is not zero')
    struct.pack_into('<QQI', output, at + 32, proof['scan_address'], proof['scan_bytes'], fileoff + padding)
    if output[fileoff + padding:fileoff + padding + 4] != b'\xcf\xfa\xed\xfe':
        raise ValueError('Dense header scan no longer begins at a real Mach-O')
    return bytes(output)
