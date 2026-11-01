#!/usr/bin/env python3
"""Build XNU26 platform providers in an isolated copy of the qualified WSL tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE = Path('/root/unixnu-build/zeta-venus-wsl/zeta/tree')
DEFAULT = Path('/root/unixnu-build/venus-xnu26-platform')
VERSION = '12377.121.6'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--profile', choices=['platform', 'storage', 'storage-data'], default='platform')
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(Path('/root/unixnu-build')) or not out.parent.is_dir():
        parser.error('Use an existing WSL build parent')
    if not 1 <= args.jobs <= 16:
        parser.error('Jobs must be1..16')
    if not args.resume:
        out.mkdir()
    elif not (out / 'tree/scripts/build-xnu-12377.sh').is_file():
        parser.error('No prepared tree to resume')
    report_path = out / 'build-report.json'
    report = json.loads(report_path.read_text()) if args.resume else dict(
        result='preparing', source_tree=str(BASE), commands=[],
        runner_sha256=sha(Path(__file__)), phone_operations=False)
    tree = out / 'tree'
    try:
        if not args.resume:
            # No inherited object paths; every kernel/provider object is rebuilt
            # against this source tree. Reference feeds remain read-only links.
            tree.mkdir()
            for name in ('scripts', 'patches'):
                shutil.copytree(BASE / name, tree / name, symlinks=False)
            for name in ('drivers', 'refer'):
                shutil.copytree(BASE / name, tree / name, symlinks=True)
            (tree / 'kits').mkdir()
            (tree / 'kits/zeta').symlink_to('/mnt/g/UniXNU-Port/sources/UniXNU-zeta-none24smu/package')
            (tree / '.cache').mkdir()
            for name in (f'xnu-{VERSION}-work', f'xnu-{VERSION}-fakeroot', f'xnu-{VERSION}-kdk'):
                shutil.copytree(BASE / '.cache' / name, tree / '.cache' / name, symlinks=True)
            (tree / '.cache/xnu-work').symlink_to(f'xnu-{VERSION}-work')
            (tree / '.cache/fakeroot').symlink_to(f'xnu-{VERSION}-fakeroot')
            source = tree / '.cache' / f'xnu-{VERSION}-work'
            revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            if revision != 'ac9718fb1af618d5ce8678d0dc6e8a58f252216f':
                raise RuntimeError('Source pin mismatch')
            diff = subprocess.check_output(['git', '-C', str(source), 'diff', '--binary'])
            (out / 'source.patch').write_bytes(diff)
            report['source_revision'] = revision
            report['source_patch_sha256'] = sha(out / 'source.patch')
            script = tree / 'scripts/build-xnu-12377.sh'
            text = script.read_text()
            begin = text.index('# Apply the series in name order;')
            end = text.index('\nif [ ! -x "$FAKEROOT/usr/local/libexec/availability.pl" ]; then', begin)
            text = text[:begin] + '# Source copied from the qualified, already patched WSL work tree.\n' + text[end:]
            begin = text.index('python3 scripts/kdk-headers.py --url')
            end = text.index('\n', begin)
            text = text[:begin] + 'test -d "$KDKROOT/System/Library/Frameworks/Kernel.framework"' + text[end:]
            script.write_text(text)
            report['build_script_sha256'] = sha(script)
            report['build_script_adaptations'] = [
                'Use recorded already-patched source snapshot instead of replaying overlapping patches.',
                'Use already-extracted KDK headers; no network or global shim changes.']
        # Reuse UniXNU's existing Linux OpenStep parser for the crypto project.
        parser_source = Path('/mnt/g/UniXNU-Port/sources/UniXNU-guide/scripts/pbxproj.py')
        shutil.copyfile(parser_source, tree / 'scripts/pbxproj.py')
        crypto_builder = tree / 'scripts/build-corecrypto-14.py'
        text = crypto_builder.read_text()
        if "subprocess.run(['plutil', '-convert', 'json'" in text:
            start = text.index("subprocess.run(['plutil', '-convert', 'json'")
            end = text.index('\nproject = json.loads', start)
            text = text[:start] + "import pbxproj\n(OUT / 'project.json').write_text(json.dumps(pbxproj.load(SOURCE / 'corecrypto.xcodeproj/project.pbxproj')))\n" + text[end:]
            crypto_builder.write_text(text)
        if 'import pbxproj' not in text:
            raise RuntimeError('Linux crypto project parser was not installed')
        report['linux_pbxproj_parser_sha256'] = sha(parser_source)
        report['crypto_builder_sha256'] = sha(crypto_builder)
        platform_builder = tree / 'scripts/build-platform-12377.py'
        text = platform_builder.read_text()
        old = "'-Wno-unnecessary-virtual-specifier']"
        new = "'-Wno-unnecessary-virtual-specifier', '-Wno-missing-designated-field-initializers']"
        if old in text:
            platform_builder.write_text(text.replace(old, new, 1))
        text = platform_builder.read_text()
        old = "'-Wno-missing-designated-field-initializers']"
        if old in text:
            platform_builder.write_text(text.replace(old,
                "'-Wno-missing-designated-field-initializers', '-Wno-unused-but-set-global']", 1))
        report['platform_builder_sha256'] = sha(platform_builder)
        pthread = tree / 'refer/libpthread-539'
        if pthread.is_symlink() and pthread.resolve() == (tree / 'refer/libpthread').resolve():
            pthread.unlink()  # Replace this wrapper's earlier wrong-version link.
        if not pthread.exists():
            subprocess.run(['git', 'clone', '--depth', '1', '--branch', 'libpthread-539.100.4',
                'https://github.com/apple-oss-distributions/libpthread.git', str(pthread)], check=True)
        revision = subprocess.check_output(['git', '-C', str(pthread), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != '1f4f5265b319111142f1bf3a27d4484ef5a98314':
            raise RuntimeError('The source pthread adapter requires the pinned539.100.4 provider')
        report['pthread_revision'] = revision
        if args.profile in ('storage', 'storage-data'):
            verified = tree / 'kits/VerifiedRoot'
            if not verified.exists():
                verified.symlink_to('/mnt/g/UniXNU-Port/sources/UniXNU-zeta-base/kits/VerifiedRoot')
            # Owner policy for Venus is generated from its retained local owner
            # public key, rather than inheriting the Duo's distinct anchor.
            policy_path = Path('/mnt/g/UniXNU-Port/sources/UniXNU-zeta-base/kits/VerifiedRoot/tools/manifest.py')
            import importlib.util
            spec = importlib.util.spec_from_file_location('owner_policy', policy_path)
            policy = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(policy)
            public = Path('/root/unixnu-build/venus-owner-root/owner-public.pem')
            anchor = policy.public_anchor(public)
            header = ('/* Venus owner public anchor; generated from retained public key. */\n'
                      'const unsigned char verified_root_key[VR_KEY_BYTES] = {\n' +
                      ''.join('  ' + ','.join(f'0x{b:02x}' for b in anchor[i:i+16]) + ',\n'
                              for i in range(0, len(anchor), 16)) + '};\n')
            (tree / 'scripts/zeta-owner-root-key.h').write_text(header)
            report['owner_public_key_sha256'] = sha(public)
            storage_builder = tree / 'scripts/build-storage-12377.py'
            text = storage_builder.read_text()
            hook = "print('Storage 12377: complete SM8350 source patch verified', flush=True)"
            if '# Venus exact partition selection' not in text:
                replacement = hook + '''
# Venus exact partition selection, after the complete generic SM8350 patch.
layout = UFS / 'RootLayout.h'
text = layout.read_text()
old = 'static const char wanted[] = "userdata";'
if text.count(old) != 1:
    raise SystemExit('NativeUfs partition selection source changed')
text = text.replace(old, 'static const char wanted[] = "unixnu";', 1)
old = '    if (match) {\\n'
if text.count(old) != 1:
    raise SystemExit('NativeUfs partition match block changed')
text = text.replace(old, old + '      if (index != 34 || entryFirst != 44881664ULL || entryLast != 61658879ULL) {\\n'
                    '        *why = "Venus unixnu partition geometry mismatch";\\n'
                    '        return false;\\n'
                    '      }\\n', 1)
layout.write_text(text)
'''
                if text.count(hook) != 1:
                    raise RuntimeError('Storage source patch hook changed')
                storage_builder.write_text(text.replace(hook, replacement, 1))
            report['storage_builder_sha256'] = sha(storage_builder)
        toolchain = Path('/root/unixnu-toolchain')
        sdk = tree / '.cache' / f'xnu-{VERSION}-fakeroot'
        flags = dict(XNU_NATIVE_ARCH_TIMER='1', XNU_VIRTUAL_TIMER_ONLY='1',
                     XNU_SOURCE_CORECRYPTO14='1', XNU_SOURCE_PTHREAD='1',
                     XNU_ARM_DT_PLATFORM='1', XNU_ARMCPU='1',
                     XNU_DT_PANIC_REGION='1', XNU_PROC_TRACE_CONSOLE='1')
        if args.profile in ('storage', 'storage-data'):
            flags.update(XNU_NATIVE_UFS_SM8350='1', XNU_NATIVE_UFS_VERIFIED_ROOT='1',
                         XNU_NATIVE_UFS_OWNER_ROOT='1', XNU_KDK_IOKIT_ABI='1',
                         XNU_APFS_CRYPTO_KPIS='1', XNU_APFS_CSR='1', XNU_APFS_MLDSA='1',
                         XNU_TRUST_CACHE_RUNTIME='1', XNU_DYLD_FLAGS_BOOTARG='1',
                         XNU_NATIVE_IOS_CLASS_ALIASES='1', XNU_EDT_FSTAB='1',
                         # Polling CDC-ACM transport after ExitBootServices so the
                         # phone can show real kernel/BSD output over USB.
                         XNU_NATIVE_DWC3_CONSOLE='1')
        if args.profile == 'storage-data':
            plan = Path('/root/unixnu-build/venus-ios26-data-plan.json')
            if not plan.exists():
                raise RuntimeError('Build the iOS26 Data seed plan before the storage-data profile')
            volume_uuid = json.loads(plan.read_text())['volume_uuid']
            flags.update(XNU_NATIVE_RAM_BLOCK='1', XNU_OWNER_DATA_MOUNT='1',
                         XNU_OWNER_DATA_VOLUME_UUID=volume_uuid)
            report['owner_data_volume_uuid'] = volume_uuid
        env = dict(os.environ)
        for key in list(env):
            if key.startswith('XNU_'):
                env.pop(key)
        env.update(flags, UNIXNU_TOOLCHAIN=str(toolchain), UNIXNU_SDKROOT=str(sdk),
                   UNIXNU_SDK_VERSION='26.0', UNIXNU_PLATFORM_PATH=str(sdk / 'Platforms/iPhoneOS.platform'),
                   XNU_TOOLCHAIN_BIN=f'{toolchain}/CommandLineTools/usr/bin {toolchain}/XcodeDefault.xctoolchain/usr/bin',
                   CLT_PREFIX=str(toolchain / 'CommandLineTools/usr'),
                   XCTOOLCHAIN_PREFIX=str(toolchain / 'XcodeDefault.xctoolchain/usr'),
                   PLATFORM='iPhoneOS', HOST_CC=str(toolchain / 'CommandLineTools/usr/bin/xnu-host-cc'),
                   MIGCOM=str(toolchain / 'CommandLineTools/usr/libexec/migcom'),
                   CROSS_CLANG=str(toolchain / 'llvm/bin/clang'), DARWIN_TRIPLE='arm64-apple-ios26.0',
                   CROSS_EXTRA_FLAGS='-mllvm -disable-atexit-based-global-dtor-lowering',
                   PATH=f'{toolchain}/CommandLineTools/usr/bin:{toolchain}/bin:' + env.get('PATH', ''),
                   JOBS=str(args.jobs), HOST_OS_VERSION='26.0', PYTHONDONTWRITEBYTECODE='1')
        for name, command in [('MEMORY_SIZE', ['getconf', '_PHYS_PAGES']),
                              ('SYSCTL_HW_PHYSICALCPU', ['nproc']), ('SYSCTL_HW_LOGICALCPU', ['nproc'])]:
            value = int(subprocess.check_output(command, text=True))
            if name == 'MEMORY_SIZE':
                value *= int(subprocess.check_output(['getconf', 'PAGE_SIZE'], text=True))
            env[name] = str(value)
        report['flags'] = flags
        report['profile'] = args.profile
        report['result'] = 'building'
        command = ['bash', 'scripts/build-xnu-12377.sh']
        log_name = f'kernel-{len(report["commands"]) + 1:03}.log'
        record = dict(command=command, cwd=str(tree), log=str(out / log_name))
        report['commands'].append(record)
        save(report_path, report)
        print(f'Building platform/CPU/source crypto/pthread: {out / log_name}', flush=True)
        with (out / log_name).open('w') as log:
            completed = subprocess.run(command, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT)
        record['returncode'] = completed.returncode
        if completed.returncode:
            raise RuntimeError(f'Kernel build exited{completed.returncode}; see{log_name}')
        obj = tree / f'build/xnu-{VERSION}/ios-obj/DEVELOPMENT_ARM64_BCM2837'
        products = {}
        for name in ('mach.development.bcm2837', 'mach.development.bcm2837.unstripped.noctf'):
            path = obj / name
            products[name] = dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))
        report.pop('error', None)
        report.update(result='built', products=products, runtime_verified=False)
    except Exception as error:
        report.update(result='failed', error=str(error))
        save(report_path, report)
        print(f'FAIL: {error}; report: {report_path}', file=sys.stderr)
        return 1
    save(report_path, report)
    print('PASS: source/provider kernel built; ' + str(report_path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
