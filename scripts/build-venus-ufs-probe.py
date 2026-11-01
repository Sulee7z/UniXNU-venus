#!/usr/bin/env python3
"""Compile the pinned SM8350 UFS transport for the audited iOS17 block ABI; no deployment."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

root = Path('/mnt/g/UniXNU-Port')
upstream = root / 'sources/UniXNU-guide'
device = root / 'ports/UniXNU-venus'
sys.path.insert(0, str(upstream / 'scripts'))
from unixnu.cli import parser as cli_parser
from unixnu.config import Context
from unixnu.kernel import linux_env

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--partition', choices=('userdata', 'unixnu'), required=True)
mode = parser.add_mutually_exclusive_group()
mode.add_argument('--readonly-survey', action='store_true', help='Compile only the bounded read-only start path')
mode.add_argument('--block-read-probe', action='store_true', help='Compile the isolated capacity/GPT command probe')
mode.add_argument('--root-boot', action='store_true', help='Build verified unixnu root transport with real policy/RAM providers')
args = parser.parse_args()
if args.root_boot and args.partition != 'unixnu':
    parser.error('The selected deployment target is unixnu')
ctx = Context(cli_parser().parse_args(['status', '-D', str(device)]))
os.environ['UNIXNU_TOOLCHAIN'] = '/root/unixnu-toolchain'
env = dict(os.environ)
env.update(linux_env(ctx))
subprocess.run(['python3', upstream / 'unixnu', 'tree'], env=env, check=True)
stem = 'venus-ufs-root-' if args.root_boot else 'venus-ufs-read-' if args.block_read_probe else 'venus-ufs-survey-' if args.readonly_survey else 'venus-ufs-probe-'
out = ctx.tree / ('build/' + stem + args.partition)
out.mkdir(parents=True, exist_ok=True)
core = root / 'sources/UniXNU-zeta-core'
reference = core / 'drivers/NativeUfs'
revision = 'af785c1777161a62931425c2faaa536ce0bebd5b'
def git(path, *arguments):
    return subprocess.check_output(['git', '-C', str(path), *arguments])
if (git(reference, 'rev-parse', 'HEAD').decode().strip() != revision or
        git(core, 'rev-parse', 'HEAD').decode().strip() != '68c513467bb6c44106c053c410582c1d14f96dd7'):
    raise SystemExit('Wrong UFS source revision')
audit = json.loads((ctx.tree / 'build/storage-abi/interface-audit.json').read_text())
if not audit['live_native_4k'] or audit['method_slots'] != 190:
    raise SystemExit('Storage runtime ABI audit is missing')
partition_define = '-DNATIVE_UFS_ROOT_PARTITION="' + args.partition + '"'
with tempfile.TemporaryDirectory(prefix='venus-ufs-build-', dir='/root/unixnu-build') as temporary:
    work = Path(temporary)
    with tarfile.open(fileobj=io.BytesIO(git(reference, 'archive', '--format=tar', revision))) as archive:
        archive.extractall(work, filter='data')
    patch = work / 'sm8350.patch'
    patch.write_bytes(git(core, 'show', 'HEAD:patches/drivers/NativeUfs-sm8350.patch'))
    patches = [patch, device / 'patches/ufs/root-partition.patch']
    if args.readonly_survey or args.block_read_probe or args.root_boot:
        patches.append(device / 'patches/ufs/readonly-survey.patch')
        shutil.copy2(device / 'package/VenusUfsSurvey.h', work / 'VenusUfsSurvey.h')
    if args.block_read_probe or args.root_boot:
        patches.append(device / 'patches/ufs/block-read-probe.patch')
        for name in ('VenusUfsReadPlan.h', 'VenusUfsReadCommands.h', 'VenusUfsGptRead.h', 'VenusUfsReadProbe.h'):
            shutil.copy2(device / 'package' / name, work / name)
    if args.root_boot:
        patches.append(device / 'patches/ufs/root-boot.patch')
        shutil.copy2(device / 'package/VenusUfsRootReport.h', work / 'VenusUfsRootReport.h')
    for patch_file in patches:
        subprocess.run(['git', 'apply', '--check', patch_file], cwd=work, check=True)
        subprocess.run(['git', 'apply', patch_file], cwd=work, check=True)
    # XNU 12377 moved these declarations; the existing XNU10063 vm_kern.h
    # already provides the API used by this transport. Do not invent prototypes.
    src = work / 'NativeUfs.cpp'
    contents = src.read_text()
    marker = '#include <vm/vm_kern_xnu.h>'
    if not (ctx.tree / '.cache/xnu-work/osfmk/vm/vm_kern_xnu.h').exists():
        if contents.count(marker) != 1:
            raise SystemExit('Unexpected SM8350 header adaptation site')
        src.write_text(contents.replace(marker, '// XNU10063: declarations are in vm/vm_kern.h.'))
    # Preserve the exact tested source beside the object for later review.
    source_out = out / 'source'
    shutil.copytree(work, source_out, dirs_exist_ok=True)
    record = json.loads((ctx.tree / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json').read_text().strip().rstrip(','))
    command, index = [], 0
    arguments = record['arguments']
    while index < len(arguments):
        value = arguments[index]
        if value == record['file']:
            command.append(str(source_out / 'NativeUfs.cpp'))
        elif value == '-o':
            command += ['-o', str(out / 'NativeUfs.o')]
            index += 1
        elif value in ('-MF', '-MJ', '-MT', '-MQ'):
            index += 1
        elif value == '-Xclang' and arguments[index + 1].startswith('-W'):
            index += 1
        elif value not in ('-MD', '-MMD', '-MP') and not value.startswith('-W'):
            command.append(value)
        index += 1
    command += ['-I', str(ctx.tree / 'build/storage-abi/include'), '-I', str(ctx.tree / '.cache/xnu-work/osfmk'),
                '-DNATIVE_UFS_SM8350=1', '-DNATIVE_UFS_PROGRESS_OBSERVER=0',
                '-DNATIVE_VERIFIED_BLOCK=' + ('1' if args.root_boot else '0'),
                partition_define, '-mgeneral-regs-only', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                '-Wno-c99-designator', '-Wno-reorder-init-list', '-Wno-deprecated-enum-enum-conversion',
                '-Wno-unnecessary-virtual-specifier']
    if args.readonly_survey or args.block_read_probe:
        command.append('-DNATIVE_UFS_READONLY_SURVEY=1')
    if args.block_read_probe:
        command.append('-DNATIVE_UFS_BLOCK_READ_PROBE=1')
    if args.root_boot:
        command += ['-DNATIVE_UFS_ROOT_BOOT=1', '-DNATIVE_UFS_POLICY_FROM_DISK=1',
                    '-DNATIVE_VERIFIED_BLOCK_MULTI_POLICY=1', '-I', str(upstream / 'kits/VerifiedRoot/include'),
                    '-I', str(upstream / 'drivers/VirtioMmioBlock')]
    result = subprocess.run(command, cwd=record['directory'], env=env, capture_output=True, text=True)
    (out / 'compile.log').write_text(result.stdout + result.stderr)
    (out / 'compile-command.json').write_text(json.dumps(command, indent=2) + '\n')
    if result.returncode:
        raise SystemExit(f'UFS compile failed: {out / "compile.log"}')
    subprocess.run(['python3', ctx.tree / 'scripts/build-virtio-mmio-bindings.py', '--component', 'ShengUfs',
                    '--directory', out], cwd=ctx.tree, env=env, check=True)
    support_report = None
    if args.root_boot:
        from venus_root_support import build as build_support
        support, support_report = build_support(ctx, env, out)
    test = out / 'partition-test'
    # Our test includes the upstream fixture with main renamed. Give that
    # ordinary int function an explicit return (only real main gets implicit 0).
    fixture = source_out / 'tests/RootLayout.cpp'
    fixture_text = fixture.read_text()
    tail = '  puts("PASS: GPT CRC/geometry/partition faults, manifest hashes/names/attributes/overlap/overflow, 2048 bounded mutations");\n}'
    if fixture_text.count(tail) != 1:
        raise SystemExit('Upstream GPT test fixture changed')
    fixture.write_text(fixture_text.replace(tail, tail[:-1] + '  return 0;\n}'))
    subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined', partition_define,
                    '-I', source_out / 'tests', device / 'tests/ufs_partition.cpp', '-lcrypto', '-o', test], check=True)
    subprocess.run([test], check=True)
    if args.readonly_survey or args.block_read_probe:
        survey_test = out / 'survey-test'
        subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', device / 'tests/ufs_survey.cpp', '-o', survey_test], check=True)
        subprocess.run([survey_test], check=True)
    host_tests = {}
    if args.block_read_probe:
        for name, source_file in [
            ('smmu-reference', source_out / 'tests/SmmuTakeover.cpp'),
            ('commands-reference', source_out / 'tests/RootCommands.cpp'),
            *[(name, device / 'tests' / (name + '.cpp')) for name in ('ufs_read_smmu', 'ufs_read_commands', 'ufs_read_gpt')],
        ]:
            executable = out / (name + '-test')
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            '-I', source_out, '-I', source_out / 'tests', source_file, '-o', executable], check=True)
            run = subprocess.run([executable], capture_output=True, text=True)
            (out / (name + '-test.log')).write_text(run.stdout + run.stderr)
            if run.returncode:
                raise SystemExit(name + ': host test failed; see ' + str(out))
            host_tests[name] = run.stdout.strip()
            print(run.stdout, end='')
    if args.root_boot:
        for name, path in [('ufs_root_commands', device / 'tests/ufs_root_commands.cpp'),
                           ('ufs_read_smmu', device / 'tests/ufs_read_smmu.cpp')]:
            binary = out / (name + '-test')
            subprocess.run(['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                            '-I',source_out,'-I',source_out/'tests',path,'-o',binary],check=True)
            result = subprocess.run([binary], capture_output=True, text=True)
            (out / (name + '-test.log')).write_text(result.stdout + result.stderr)
            if result.returncode: raise SystemExit('Root host test failed: ' + name)
            host_tests[name] = result.stdout.strip()
def names(path, option):
    text = subprocess.check_output(['xcrun', 'nm', '-g', option, '-j', path], env=env, text=True)
    return {line.strip() for line in text.splitlines() if line.startswith('_')}
archive_path = out / 'libShengUfs.a'
kernel = root / 'artifacts/venus-guide-pmgr/kernel/kernel.macho'
missing_in_image = names(archive_path, '-u') - names(archive_path, '-U') - names(kernel, '-U') - {'___dso_handle'}
if args.root_boot:
    archives = [archive_path, *support.rglob('*.a')]
    missing_in_image = set().union(*(names(a, '-u') for a in archives)) - set().union(*(names(a, '-U') for a in archives)) - names(kernel, '-U') - {'___dso_handle'}
# Kernel-private definitions such as nprocs and the real UBSan runtime lose
# public visibility in the linked image. Check the actual global definitions
# in its native link inputs, rather than inventing a provider or disabling checks.
object_dir = ctx.tree / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
link_file = object_dir / 'link.filelist'
object_paths = [line.strip() for line in link_file.read_text().splitlines() if line.strip()]
object_names = set()
for first in range(0, len(object_paths), 200):
    text = subprocess.check_output(['xcrun', 'nm', '-g', '-U', '-j', *object_paths[first:first + 200]], env=env, text=True)
    object_names.update(line.strip() for line in text.splitlines() if line.startswith('_'))
missing = sorted(missing_in_image - object_names)
if missing:
    (out / 'missing-imports.json').write_text(json.dumps(missing, indent=2) + '\n')
    raise SystemExit(f'UFS has unresolved current-kernel imports: {missing}')
report = {'ufs_revision': revision, 'root_partition': args.partition, 'ios17_abi_bound': True,
          'archive_sha256': hashlib.sha256((out / 'libShengUfs.a').read_bytes()).hexdigest(),
          'native_ufs_source_sha256': hashlib.sha256((source_out / 'NativeUfs.cpp').read_bytes()).hexdigest(),
          'storage_interface_audit_sha256': hashlib.sha256((ctx.tree / 'build/storage-abi/interface-audit.json').read_bytes()).hexdigest(),
          'root_partition_test_passed': True, 'probe_only_unverified_root_build': not args.root_boot,
          'readonly_survey': args.readonly_survey,
          'block_read_probe': args.block_read_probe,
          'root_boot': args.root_boot,
          'root_support': support_report,
          'host_tests': host_tests,
          'unresolved_kernel_imports': missing,
          'resolved_from_native_link_objects': sorted(missing_in_image & object_names),
          'native_link_filelist_sha256': hashlib.sha256(link_file.read_bytes()).hexdigest(),
          'linked_into_kernel': False, 'hardware_tested': False}
if args.block_read_probe or args.root_boot:
    inputs = [*device.glob('package/VenusUfs*.h'), *device.glob('patches/ufs/*.patch')]
    report['device_inputs'] = {str(path.relative_to(device)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in inputs}
(out / 'venus-build.json').write_text(json.dumps(report, indent=2) + '\n')
export = root / ('artifacts/' + stem + args.partition)
export.mkdir(exist_ok=True)
for name in ('libShengUfs.a', 'bindings.json', 'venus-build.json', 'compile-command.json', 'compile.log'):
    shutil.copy2(out / name, export / name)
if args.root_boot:
    shutil.copytree(support, export / 'support', dirs_exist_ok=True)
    shutil.copy2(out / 'NativeUfs.o', export / 'NativeUfs.o')
    shutil.copy2(out / 'root-support.json', export / 'root-support.json')
print(json.dumps(report, indent=2))
os.sync()
