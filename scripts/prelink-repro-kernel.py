#!/usr/bin/env python3
"""Bridge the fixed UniXNU prelink interface to the validated KDK source recipe."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib

parser = argparse.ArgumentParser(description=__doc__)
for name in ('kernel', 'prelinked', 'output', 'repro-config'):
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('--slide', required=True)
parser.add_argument('--root', action='append', default=[])
args = parser.parse_args()
if args.output.exists():
    parser.error('Preserve an existing candidate')
os.environ['XNU_REPRO_CONFIG'] = str(args.repro_config.resolve())
spec = importlib.util.spec_from_file_location('source_kernel_context', Path(__file__).with_name('build-repro-kernel.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
repo, marker, inputs = module.context()
dependency = repo / '.cache/repro-python'
os.environ['PYTHONPATH'] = str(dependency) + os.pathsep + os.environ.get('PYTHONPATH', '')
board = tomllib.loads((repo / 'board.toml').read_text())
config = board['kernel']['prelink']
if args.slide != config['slide'] or set(args.root) != set(config['roots']):
    raise ValueError('Selected source provider plan differs from board.toml')
if hashlib.sha256(args.prelinked.read_bytes()).hexdigest() != config['kernelcache_sha256']:
    raise ValueError('Exact KDK reference input required')
source_receipt = json.loads(args.kernel.with_suffix(args.kernel.suffix + '.source.json').read_text())
if source_receipt['result'] != 'source-built' or source_receipt['kernel_sha256'] != hashlib.sha256(args.kernel.read_bytes()).hexdigest():
    raise ValueError('Newly source-built kernel receipt required')
work = Path(source_receipt['build']) / 'work'
tools = repo / 'repro/prelink'
layout = marker['layout']
args.output.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='provider-rebuild-', dir=args.output.parent) as temporary:
    temporary = Path(temporary)
    prelink = temporary / 'prelink'
    bound = temporary / 'bound'
    command = [sys.executable, '-B', str(tools / 'build_prelink.py'), '--native', str(args.kernel),
        '--hmac-seal', str(args.kernel.with_suffix(args.kernel.suffix + '.crypto-hmac.json')),
        '--extensions', str(inputs['kdk_extensions']), '--reference', str(args.prelinked),
        '--xnu-source', str(work / layout['xnu']), '--storage-source', str(work / layout['storage']),
        '--crypto-source', str(inputs['corecrypto2023']), '--display-source', str(work / layout['display']),
        '--hid-source', str(work / layout['hid']), '--osaction-header', str(work / layout['osaction']), '--output', str(prelink)]
    subprocess.run(command, check=True, timeout=1800)
    subprocess.run([sys.executable, '-B', str(tools / 'bind_amfi.py'), '--prelink', str(prelink), '--output', str(bound)],
                   check=True, timeout=300)
    final = bound / 'kernel.macho'
    base = (repo / board['package']['unixnu']).resolve()
    environment = dict(os.environ, UNIXNU_SOURCE_BASE=str(base), UNIXNU_UEFI=str(inputs['uefi']))
    subprocess.run([sys.executable, '-B', str(tools / 'patch_source_panic.py'), str(final), '--panic-screen',
        '--no-reset', '--usb-panic', '--compact-no-reset-caves', '--relocate-native-entry-caves'],
        env=environment, check=True, timeout=600)
    subprocess.run([sys.executable, '-B', str(work / layout['seal_tool']), str(final), '--static-if-defaults'], check=True, timeout=120)
    shutil.copyfile(final, args.output)
    summary = json.loads((bound / 'summary.json').read_text())
    summary.update(source_build=source_receipt, output_sha256=hashlib.sha256(final.read_bytes()).hexdigest(),
                   prelinked_sha256=hashlib.sha256(final.read_bytes()).hexdigest(),
                   source_runtime_verified=False, phone_operations=False)
    args.output.with_suffix('.json').write_text(json.dumps(summary, indent=2) + '\n')
    args.output.with_suffix('.map.json').write_text((prelink / 'prelink-report.json').read_text())
