#!/usr/bin/env python3
"""Compare the source-provider HMAC with the final ordinary ARM64 kernel bytes."""
import argparse
import hashlib
import hmac
import json
from pathlib import Path
import struct


MH_MAGIC_64 = 0xFEEDFACF
LC_SEGMENT_64 = 0x19


def audit(kernel: Path, seal: Path | None = None) -> dict:
    data = kernel.read_bytes()
    magic, cpu, subtype, filetype, ncmds, sizeofcmds = struct.unpack_from('<6I', data)
    if (magic, cpu, subtype & 0xFFFFFF, filetype) != (MH_MAGIC_64, 0x100000C, 0, 2):
        raise ValueError('Expected ARM64 subtype-0 MH_EXECUTE')
    at = 32
    text = None
    hmac_section = None
    for _ in range(ncmds):
        command, size = struct.unpack_from('<II', data, at)
        if size < 8 or at + size > 32 + sizeofcmds:
            raise ValueError('Invalid load-command size')
        if command == LC_SEGMENT_64:
            segment_name = data[at + 8:at + 24].split(b'\0', 1)[0]
            nsects = struct.unpack_from('<I', data, at + 64)[0]
            if 72 + nsects * 80 > size:
                raise ValueError('Invalid section table size')
            for index in range(nsects):
                section = at + 72 + index * 80
                sect_name, seg_name, address, length, offset = struct.unpack_from('<16s16sQQI', data, section)
                sect_name, seg_name = sect_name.rstrip(b'\0'), seg_name.rstrip(b'\0')
                if sect_name == b'__text' and seg_name in (b'__TEXT', b'__TEXT_EXEC'):
                    if text is not None:
                        raise ValueError('Multiple eligible text sections')
                    text = (offset, length, address, seg_name.decode())
                if sect_name == b'__fips_hmacs':
                    if hmac_section is not None or length != 32:
                        raise ValueError('Expected one 32-byte __fips_hmacs field')
                    hmac_section = (offset, length, address, seg_name.decode())
        at += size
    if at != 32 + sizeofcmds or text is None or hmac_section is None:
        raise ValueError('Missing text section or required __fips_hmacs field')
    text_offset, text_size, text_va, text_segment = text
    if text_offset + text_size > len(data) or hmac_section[0] + 32 > len(data):
        raise ValueError('Text section exceeds the file')
    audit_code = bytearray(data[text_offset:text_offset + text_size])
    expected_patches = []
    if seal:
        seal_data = json.loads(seal.read_text())
        if (seal_data['kernel_sha256'] != hashlib.sha256(data).hexdigest() or
                int(seal_data['code_file_offset'], 0) != text_offset or
                seal_data['code_bytes'] != text_size or
                int(seal_data['hmac_file_offset'], 0) != hmac_section[0]):
            raise ValueError('Seal identity or section extents differ from the kernel')
        seen = set()
        for patch in seal_data.get('expected_runtime_instruction_changes', []):
            va = int(patch['va'], 0)
            relative = va - text_va
            if relative < 0 or relative + 4 > text_size or relative % 4 or relative in seen:
                raise ValueError('Expected static-if patch is outside hashed text')
            seen.add(relative)
            file_at = text_offset + relative
            original = data[file_at:file_at + 4]
            wanted = int(patch['file_instruction'], 0).to_bytes(4, 'little')
            if original != wanted:
                raise ValueError('Static-if instruction no longer matches its source seal')
            final = int(patch['post_startup_instruction'], 0).to_bytes(4, 'little')
            audit_code[relative:relative + 4] = final
            expected_patches.append({'va': patch['va'], 'file': wanted.hex(), 'post_startup': final.hex()})
    calculated = hmac.digest(b'\0', audit_code, 'sha256')
    raw_calculated = hmac.digest(b'\0', data[text_offset:text_offset + text_size], 'sha256')
    stored = data[hmac_section[0]:hmac_section[0] + 32] if hmac_section else b''
    result = {
        'kernel': str(kernel.resolve()), 'kernel_bytes': len(data),
        'kernel_sha256': hashlib.sha256(data).hexdigest(),
        'text': {'segment': text_segment, 'address': hex(text_va), 'offset': hex(text_offset),
         'bytes': text_size, 'sha256': hashlib.sha256(data[text_offset:text_offset + text_size]).hexdigest()},
        'expected_post_startup_text_sha256': hashlib.sha256(audit_code).hexdigest(),
        'expected_runtime_static_if_changes_applied': expected_patches,
        'hmac_field': ({'segment': hmac_section[3], 'address': hex(hmac_section[2]), 'offset': hex(hmac_section[0]),
                        'stored_hex': stored.hex(), 'post_startup_calculated_hex': calculated.hex(),
                         'raw_file_text_calculated_hex': raw_calculated.hex(),
                         'calculated_hex': raw_calculated.hex(),
                         'matches': hmac.compare_digest(stored, raw_calculated),
                        'matches_expected_post_startup_text': hmac.compare_digest(stored, calculated),
                        'raw_file_text_matches': hmac.compare_digest(stored, raw_calculated)} if hmac_section else
                       {'present': False, 'calculated_hex': calculated.hex(), 'matches': None}),
    }
    if seal:
        seal_data = json.loads(seal.read_text())
        result['build_seal'] = seal_data
        result['stored_matches_build_seal'] = stored.hex() == seal_data['hmac_sha256']
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel', type=Path, required=True)
    parser.add_argument('--seal', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a new output report path')
    report = audit(args.kernel, args.seal)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if (report['hmac_field']['matches_expected_post_startup_text'] is True and
                 report.get('stored_matches_build_seal', True) is True) else 1


if __name__ == '__main__':
    raise SystemExit(main())
