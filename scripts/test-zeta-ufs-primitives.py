#!/usr/bin/env python3
"""Apply the pinned SM8350 UFS patch in isolation and run its host primitive tests."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

root = Path('/mnt/g/UniXNU-Port')
core = root / 'sources/UniXNU-zeta-core'
source = core / 'drivers/NativeUfs'
revision = 'af785c1777161a62931425c2faaa536ce0bebd5b'
core_revision = '68c513467bb6c44106c053c410582c1d14f96dd7'
def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args])
if git(source, 'rev-parse', 'HEAD').decode().strip() != revision or git(core, 'rev-parse', 'HEAD').decode().strip() != core_revision:
    raise SystemExit('Unexpected UFS reference revision')
out = root / 'artifacts/venus-ufs-primitives'
out.mkdir(parents=True, exist_ok=True)
patch = git(core, 'show', 'HEAD:patches/drivers/NativeUfs-sm8350.patch')
results = {}
with tempfile.TemporaryDirectory(prefix='venus-ufs-', dir='/root/unixnu-build') as temporary:
    work = Path(temporary)
    with tarfile.open(fileobj=io.BytesIO(git(source, 'archive', '--format=tar', revision))) as archive:
        archive.extractall(work, filter='data')
    patch_file = work / 'sm8350.patch'
    patch_file.write_bytes(patch)
    subprocess.run(['git', 'apply', '--check', patch_file], cwd=work, check=True)
    subprocess.run(['git', 'apply', patch_file], cwd=work, check=True)
    subprocess.run(['git', 'apply', '--reverse', '--check', patch_file], cwd=work, check=True)
    for test in ('SmmuTakeover', 'RootLayout'):
        binary = work / (test + '-test')
        command = ['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                   '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                   str(work / 'tests' / (test + '.cpp')), '-o', str(binary)]
        if test == 'RootLayout':
            command += ['-lcrypto']
        build = subprocess.run(command, cwd=work, capture_output=True, text=True)
        (out / (test + '-build.log')).write_text(build.stdout + build.stderr)
        if build.returncode:
            raise SystemExit(f'{test} build failed; see {out}')
        run = subprocess.run([binary], cwd=work, capture_output=True, text=True)
        (out / (test + '.log')).write_text(run.stdout + run.stderr)
        if run.returncode:
            raise SystemExit(f'{test} failed; see {out}')
        results[test] = {'exit_code': run.returncode, 'output': run.stdout.strip()}
        print(run.stdout, end='')
    hashes = {name: hashlib.sha256((work / name).read_bytes()).hexdigest()
              for name in ('GccUfs.h', 'NativeUfs.cpp', 'SmmuTakeover.h', 'RootLayout.h', 'RootQueue.h')}
record = {'native_ufs_revision': revision, 'zeta_core_revision': core_revision,
          'sm8350_patch_sha256': hashlib.sha256(patch).hexdigest(), 'patched_sources_sha256': hashes,
          'sanitizers': ['address', 'undefined'], 'results': results,
          'scope': 'Host tests of patched SMMU and GPT/manifest logic only',
          'xnu_storage_abi_verified': False, 'physical_ufs_tested': False}
(root / 'ports/UniXNU-venus/evidence/zeta-ufs-primitives.json').write_text(json.dumps(record, indent=2) + '\n')
