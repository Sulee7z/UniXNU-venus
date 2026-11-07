#!/usr/bin/env python3
"""Build the selected source closure and SDK runtimes from declared local inputs."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

def context():
    value = os.environ.get('XNU_REPRO_CONFIG')
    if not value:
        raise ValueError('This source publication requires the declared replay defconfig')
    marker = Path(value).resolve()
    document = tomllib.loads(marker.read_text())
    repo = (marker.parent / document['device_directory']).resolve()
    local_file = repo / document['local_inputs']
    local = tomllib.loads(local_file.read_text())['repro']
    paths = {}
    for key, value in local.items():
        if isinstance(value, str):
            path = Path(os.path.expandvars(value)).expanduser()
            paths[key] = (path if path.is_absolute() else local_file.parent / path).resolve()
    return repo, document, paths

def main():
    repo, marker, inputs = context()
    tree = Path(__file__).resolve().parents[1]
    outputs = marker['outputs']
    runtime = tree / outputs['sdk_runtime']
    native = tree / outputs['native']
    staged = tree / outputs['kernel']
    if any(path.exists() for path in (runtime, native, staged)):
        raise ValueError('Preserve an earlier build; choose a fresh --out for this source rebuild')
    manifest = repo / marker['source_manifest']
    source_config = repo / marker['source_inputs']
    subprocess.run([sys.executable, '-B', str(repo / 'repro/check_source.py'), str(manifest.parent)], check=True)
    args = [sys.executable, '-B', str(repo / 'repro/build_sdk_runtime.py'), '--config', str(source_config),
        '--sdk', str(inputs['sdk']), '--clang', str(inputs['clang']), '--llvm-source', str(inputs['llvm_source']),
        '--libc-source', str(inputs['libc_source']), '--libdispatch-source', str(inputs['libdispatch_source']),
        '--xnu-source', str(inputs['xnu_source']), '--output', str(runtime)]
    subprocess.run(args, check=True, timeout=1800)
    args = [sys.executable, '-B', str(repo / 'repro/build_native.py'), '--manifest', str(manifest),
        '--output', str(native), '--sdk', str(runtime / 'sdk'), '--sdk-runtime-report', str(runtime / 'report.json'),
        '--kdk', str(inputs['kdk_headers']), '--clang', str(inputs['clang']), '--ld', str(inputs['ld']),
        '--source', 'CORECRYPTO2023=' + str(inputs['corecrypto2023']),
        '--source', 'CORECRYPTO2026=' + str(inputs['corecrypto2026']),
        '--source', 'XNU_SOURCE=' + str(inputs['xnu_source']), '-j', os.environ.get('JOBS', '8')]
    subprocess.run(args, check=True, timeout=10800)
    result = json.loads((native / 'objects.json').read_text())
    if not result['complete_source_link'] or not result['link_performed']:
        raise ValueError('Full source link did not complete')
    source = json.loads(manifest.read_text())['native_output']
    if not source.startswith('${WORK}/'):
        raise ValueError('Native output must belong to this fresh source build')
    kernel = native / 'work' / source[len('${WORK}/'):]
    staged.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(kernel, staged)
    seal = kernel.with_suffix(kernel.suffix + '.crypto-hmac.json')
    shutil.copyfile(seal, staged.with_suffix(staged.suffix + '.crypto-hmac.json'))
    receipt = dict(result='source-built', kernel_sha256=hashlib.sha256(staged.read_bytes()).hexdigest(),
        source_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        build=str(native), source_sdk_runtime=str(runtime), native_compilation_units=len(result['objects']),
        prior_native_objects_or_driver_archives_used=False)
    staged.with_suffix(staged.suffix + '.source.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))

if __name__ == '__main__':
    main()
