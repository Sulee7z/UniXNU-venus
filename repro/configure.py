#!/usr/bin/env python3
"""Prepare the pinned UniXNU checkout and local-only build input files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib
import io
import urllib.request
import zipfile

def run(argv):
    subprocess.run(list(map(str, argv)), check=True, timeout=600)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--local', type=Path, required=True)
    args = parser.parse_args()
    repo = args.repository.resolve()
    board = tomllib.loads((repo / 'board.toml').read_text())
    inputs = tomllib.loads((repo / 'repro/inputs.toml').read_text())
    local_path = args.local.resolve()
    local = tomllib.loads(local_path.read_text())
    required = ('sdk', 'kdk_headers', 'kdk_extensions', 'kdk_reference', 'uefi', 'clang', 'ld',
                'llvm_source', 'libc_source', 'libdispatch_source', 'xnu_source', 'corecrypto2023', 'corecrypto2026')
    repro = local.get('repro', {})
    for key in required:
        value = repro.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError('Local [repro] input required: ' + key)
        path = Path(os.path.expandvars(value)).expanduser()
        path = path if path.is_absolute() else local_path.parent / path
        if not path.exists():
            raise ValueError('Local build input missing: ' + key)
    uefi = Path(os.path.expandvars(repro['uefi'])).expanduser()
    uefi = (uefi if uefi.is_absolute() else local_path.parent / uefi).resolve()
    revision = subprocess.check_output(['git', '-C', str(uefi), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != inputs['uefi']['commit']:
        raise ValueError('Exact source Mu-Silicium commit required')
    run(['git', '-C', uefi, 'submodule', 'update', '--init', '--recursive', '--', *board['firmware']['submodules']])
    checkout = Path(board['package']['unixnu'])
    checkout = checkout if checkout.is_absolute() else repo / checkout
    checkout = checkout.resolve()
    pin = inputs['unixnu']
    if not checkout.exists():
        checkout.mkdir(parents=True)
        run(['git', 'init', '-q', checkout])
        run(['git', '-C', checkout, 'remote', 'add', 'origin', pin['repository']])
        run(['git', '-C', checkout, 'fetch', '--depth=1', 'origin', pin['commit']])
        run(['git', '-C', checkout, 'checkout', '--detach', pin['commit']])
    revision = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != pin['commit']:
        raise ValueError('Do not modify an unrelated UniXNU checkout; use the pinned build checkout')
    profile_name = board['board']['os_profile']
    source = repo / 'profiles/os' / profile_name
    target = checkout / 'profiles/os' / profile_name
    if not source.is_dir():
        raise ValueError('Device OS profile source is missing: ' + profile_name)
    for path in source.rglob('*'):
        if not path.is_file():
            continue
        destination = target / path.relative_to(source)
        if destination.exists():
            if destination.read_bytes() != path.read_bytes():
                raise ValueError('Existing OS profile differs; do not overwrite it: ' + str(destination))
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    options = dict(local.get('build', {}))
    options.setdefault('kernelcache', repro['kdk_reference'])
    dependency = repo / '.cache/repro-python'
    if not dependency.exists():
        distribution = inputs['decoder']
        with urllib.request.urlopen(distribution['url'], timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != distribution['sha256']:
            raise ValueError('Source decoder distribution hash mismatch')
        dependency.mkdir(parents=True)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                if not (dependency / member.filename).resolve().is_relative_to(dependency.resolve()):
                    raise ValueError('Decoder distribution escapes build cache')
            archive.extractall(dependency)
        (dependency / 'source-distribution.json').write_text(json.dumps(distribution, indent=2) + '\n')
    elif json.loads((dependency / 'source-distribution.json').read_text()) != inputs['decoder']:
        raise ValueError('Preserve a different decoder installation')
    text = '[build]\n'
    path_options = ('uefi', 'edk2', 'kernelcache', 'kernel', 'trust_cache', 'owner_trust_cache', 'data_ramdisk', 'gpu_addon', 'dtb', 'out')
    for key, value in options.items():
        if key in path_options:
            path = Path(os.path.expandvars(value)).expanduser()
            value = str((path if path.is_absolute() else local_path.parent / path).resolve())
        text += key + ' = ' + json.dumps(value) + '\n'
    build_local = checkout / 'unixnu.local.toml'
    if build_local.exists() and build_local.read_text() != text:
        raise ValueError('Existing build input file differs; preserve it')
    build_local.write_text(text)
    receipt = repo / '.cache/repro-configure.json'
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(dict(unixnu_commit=revision, profile=profile_name,
        local_input_path=str(local_path), local_input_sha256=hashlib.sha256(local_path.read_bytes()).hexdigest(),
        build_options_not_published=True), indent=2) + '\n')
    print('Pinned UniXNU and source OS profile prepared; local input files remain ignored')

if __name__ == '__main__':
    main()
