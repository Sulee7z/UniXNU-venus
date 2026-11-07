"""Portable exact-address helpers for the source-backed AMFI binding checks."""
import hashlib
from pathlib import Path
import re
import shutil
import struct
import subprocess

import capstone

ROOT = Path.cwd()
AMFI = 'com.apple.driver.AppleMobileFileIntegrity'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def thin(data):
    if data[:4] == b'\xcf\xfa\xed\xfe':
        return data
    if data[:4] != b'\xca\xfe\xba\xbe':
        raise ValueError('Unsupported Mach-O container')
    selected = []
    for index in range(struct.unpack_from('>I', data, 4)[0]):
        cpu, subtype, offset, size, _ = struct.unpack_from('>5I', data, 8 + index * 20)
        if cpu == 0x100000C and subtype & 0xFFFFFF == 2:
            selected.append(data[offset:offset + size])
    if len(selected) != 1:
        raise ValueError('Expected one ARM64e KDK slice')
    return selected[0]

def segments(data):
    offset = 32
    result = []
    for _ in range(struct.unpack_from('<I', data, 16)[0]):
        command, size = struct.unpack_from('<II', data, offset)
        if size < 8 or offset + size > len(data):
            raise ValueError('Invalid Mach-O load command')
        if command == 0x19:
            result.append(struct.unpack_from('<4Q', data, offset + 24))
        offset += size
    return result

def read_va(data, address, size):
    rows = [row for row in segments(data) if row[0] <= address and address + size <= row[0] + row[3]]
    if len(rows) != 1:
        raise ValueError('Address is not uniquely file-backed')
    va, _, offset, _ = rows[0]
    return data[offset + address - va:offset + address - va + size]

def nm(path):
    executable = shutil.which('llvm-nm') or shutil.which('llvm-nm-18')
    if not executable:
        raise ValueError('llvm-nm is required for exact source-symbol binding')
    text = subprocess.check_output([executable, '--defined-only', str(path)], text=True)
    return sorted((int(address, 16), name) for address, kind, name in
        re.findall(r'^([0-9a-fA-F]+)\s+(\S)\s+(.+)$', text, re.M) if kind.upper() != 'A')
