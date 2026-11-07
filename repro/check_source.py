#!/usr/bin/env python3
"""Verify portable source hashes, object coverage and publication exclusions."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

BINARY_EXTENSIONS = {'.o', '.cpo', '.a', '.so', '.dylib', '.efi', '.fd', '.img', '.macho', '.dbr', '.im4p'}

def check(root):
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema') != 2 or not manifest.get('source_only'):
        raise ValueError('Expected a portable source-only manifest')
    errors = []
    for name, digest in manifest['files'].items():
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or path.suffix.lower() in BINARY_EXTENSIONS:
            errors.append('Not a repository-relative source file: ' + name)
            continue
        source = root / 'sources' / name
        if not source.is_file():
            errors.append('Missing source: ' + name)
            continue
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            errors.append('Source hash mismatch: ' + name)
        if data[:4] in (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\x7fELF') or data[:2] == b'MZ':
            errors.append('Binary input: ' + name)
        if b'corecrypto is licensed under Apple' in data or b'CORECRYPTO INTERNAL USE LICENSE' in data:
            errors.append('Restricted external source was bundled: ' + name)
        if b'/work/' in data or b'C:\\Users\\' in data:
            errors.append('Historical host path: ' + name)
        if re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', data):
            errors.append('Private key: ' + name)
    external = manifest.get('external_files', {})
    if set(external) & set(manifest['files']):
        errors.append('External files were also declared as repository files')
    products = set(manifest['recipes']) | set(manifest.get('transforms', {}))
    archives = set()
    for archive in manifest['archives']:
        archives.add(archive['output'])
        for name in archive['objects']:
            if name not in products:
                errors.append('Archive member lacks a source recipe: ' + name)
    for name in manifest['link_filelist']:
        if name not in products:
            errors.append('Link object lacks a source recipe: ' + name)
    # Every direct object/archive on the link line needs a recipe or an explicit
    # compiler-runtime input. The latter remain visible until source rebuilding
    # of those libraries is integrated.
    runtime_inputs = []
    for value in manifest['link_command']:
        if value == '-lfirehose_kernel':
            runtime_inputs.append('${SDK}/usr/local/lib/kernel/libfirehose_kernel.a')
        operand = value.split(',')[-1] if value.startswith('-Wl,-force_load,') else value
        if operand.endswith(('.o', '.cpo', '.a')) and operand not in products | archives:
            if operand.startswith('${SDK}/'):
                runtime_inputs.append(operand)
            else:
                errors.append('Link input lacks a source recipe: ' + operand)
    if errors:
        raise ValueError('\n'.join(errors))
    return dict(files=len(manifest['files']), external_files=len(external),
                compile_units=len(manifest['recipes']), archives=len(archives),
                external_sdk_archives=runtime_inputs, source_hashes_verified=True,
                full_package_verified=False)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.snapshot.resolve()), indent=2))

if __name__ == '__main__':
    main()
