#!/usr/bin/env python3
"""Copy SDK headers and rebuild its kernel runtime libraries from source."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib

PROFILE_SOURCES = ('InstrProfiling', 'InstrProfilingBuffer', 'InstrProfilingPlatformDarwin',
                   'InstrProfilingWriter', 'InstrProfilingInternal', 'InstrProfilingVersionVar')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--llvm-source', type=Path, required=True)
    parser.add_argument('--libc-source', type=Path, required=True)
    parser.add_argument('--libdispatch-source', type=Path, required=True)
    parser.add_argument('--xnu-source', type=Path, required=True)
    parser.add_argument('--clang', type=Path, required=True)
    parser.add_argument('--ar', default='llvm-ar-18')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inputs = tomllib.loads(args.config.read_text())
    config = inputs['sdk_runtime']
    out = args.output.resolve()
    if out.exists():
        parser.error('A fresh SDK runtime output is required')
    for path in (args.sdk, args.llvm_source, args.libc_source, args.libdispatch_source, args.xnu_source, args.clang):
        if not path.exists():
            parser.error('Missing build input: ' + str(path))
    revisions = {}
    for name, path in (('llvm', args.llvm_source), ('libc', args.libc_source), ('libdispatch', args.libdispatch_source)):
        revision = subprocess.check_output(['git', '-c', 'safe.directory=' + str(path.resolve()),
            '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != inputs[name]['commit']:
            raise ValueError('Source revision mismatch: ' + name)
        revisions[name] = revision
    out.mkdir(parents=True)
    sdk = out / 'sdk'
    # The previous SDK supplies headers, not object files or static libraries.
    shutil.copytree(args.sdk, sdk, symlinks=True,
                    ignore=shutil.ignore_patterns('*.a', '*.o', '*.cpo', '*.macho', '*.dylib'))
    objects = out / 'objects'
    objects.mkdir()
    library = sdk / 'usr/local/lib/kernel'
    library.mkdir(parents=True, exist_ok=True)
    report = dict(source_only_runtime=True, previous_sdk_archives_copied=False,
                  commands=[], source_sha256={}, libraries={}, source_revisions=revisions)
    def run(label, command):
        with (out / (label + '.log')).open('xb') as log:
            result = subprocess.run(list(map(str, command)), cwd=out, stdout=log,
                stderr=subprocess.STDOUT, timeout=300,
                env={k: v for k, v in os.environ.items() if k != 'CCC_OVERRIDE_OPTIONS'})
        report['commands'].append(dict(label=label, argv=list(map(str, command)), returncode=result.returncode))
        (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        if result.returncode:
            raise RuntimeError(label + ' failed: ' + str(out / (label + '.log')))
    runtime = args.llvm_source / 'compiler-rt'
    built = []
    for name in PROFILE_SOURCES:
        source = runtime / ('lib/profile/' + name + '.c')
        target = objects / (name + '.o')
        command = [args.clang, *config.get('profile_extra_flags', []), '-target', config['profile_target'],
            '-arch', 'arm64', '-isysroot', sdk, '-mkernel', '-DKERNEL_USE', '-O3', '-fPIC', '-w',
            '-I', runtime / 'include', '-I', sdk / 'System/Library/Frameworks/Kernel.framework/Headers',
            '-idirafter', args.libc_source / 'include', '-idirafter', args.xnu_source / 'libsyscall/wrappers',
            '-c', source, '-o', target]
        report['source_sha256']['compiler-rt/lib/profile/' + name + '.c'] = sha(source)
        run('compile-' + name, command)
        built.append(target)
    destination = library / 'libcc_kext.a'
    run('archive-libcc_kext', [args.ar, 'rcs', destination, *built])
    report['libraries'][destination.name] = sha(destination)
    dispatch = args.libdispatch_source
    source = dispatch / 'src/firehose/firehose_buffer.c'
    target = objects / 'firehose_buffer.o'
    command = [args.clang, *config.get('firehose_extra_flags', []), '-target', config['kernel_target'],
        '-std=gnu11', '-Os', '-g', '-mkernel', '-nostdinc', '-Wno-packed',
        '-DKERNEL=1', '-DDISPATCH_USE_DTRACE=0', '-DOS_ATOMIC_CONFIG_MEMORY_ORDER_DEPENDENCY=1',
        '-DOS_ATOMIC_CONFIG_STARVATION_FREE_ONLY=0']
    for folder in (dispatch, sdk / 'System/Library/Frameworks/Kernel.framework/PrivateHeaders',
                   sdk / 'System/Library/Frameworks/Kernel.framework/Headers', sdk / 'usr/local/include/os',
                   sdk / 'usr/local/include/firehose', sdk / 'usr/include', sdk / 'usr/local/include',
                   args.xnu_source / 'EXTERNAL_HEADERS'):
        command += ['-I', folder]
    command += ['-c', source, '-o', target]
    report['source_sha256']['libdispatch/src/firehose/firehose_buffer.c'] = sha(source)
    run('compile-firehose_buffer', command)
    destination = library / 'libfirehose_kernel.a'
    run('archive-libfirehose_kernel', [args.ar, 'rcs', destination, target])
    report['libraries'][destination.name] = sha(destination)
    report.update(result='runtime-built', sdk=str(sdk), source_units=7)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('result', 'sdk', 'source_units', 'libraries')}, indent=2))

if __name__ == '__main__':
    main()
