#!/usr/bin/env python3
"""Build the pinned zeta EFI loaders in WSL, or audit the retained EFI pair.

All generated files stay in /root/unixnu-build/zeta-qemu-loaders. A failed
build is recorded and the retained candidates are inspected without copying
them. No QEMU invocation or kernel/device-tree preparation is performed.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tomllib


PROJECT = Path('/mnt/g/UniXNU-Port')
SOURCE = PROJECT / 'sources/UniXNU-zeta-base'
TREE = Path('/root/unixnu-build/zeta-venus-wsl/zeta/tree')
FETCHED_EDK2 = TREE.parents[1] / 'feeds/mu_basecore-89034cbb'
OUT = Path('/root/unixnu-build/zeta-qemu-loaders')
CANDIDATES = PROJECT / 'artifacts/venus-scale-refresh-012/phone'
EXPECTED_SOURCE = '35c384e84266343991fd14706e8c651f7d2e09ed'
EXPECTED_DARWINBOOT = '85332b317ee80898fc78939ea64e6ca52d3837a3'
EXPECTED_EDK2 = 'cfb93724a06ff86ff5ba971413368a7809ee42a5'


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + '\n')


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(
        ['git', '--no-optional-locks', '-C', str(path), *args], text=True
    ).strip()


def revision(path: Path, expected: str, *scope: str) -> dict:
    head = git(path, 'rev-parse', 'HEAD')
    status = git(path, 'status', '--porcelain', '--untracked-files=all', '--', *scope)
    if head != expected or status:
        raise RuntimeError(f'Source pin/cleanliness mismatch at {path}: {head}; {status}')
    return {'path': str(path), 'revision': head, 'checked_paths': list(scope),
            'status': status, 'origin': git(path, 'remote', 'get-url', 'origin')}


def pe_metadata(path: Path, subsystem: int) -> dict:
    data = path.read_bytes()
    if len(data) < 64 or data[:2] != b'MZ':
        raise RuntimeError(f'Not a DOS/PE image: {path}')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    if pe + 24 > len(data) or data[pe:pe + 4] != b'PE\0\0':
        raise RuntimeError(f'Invalid PE signature/header: {path}')
    machine, sections, timestamp = struct.unpack_from('<HHI', data, pe + 4)
    optional_size, characteristics = struct.unpack_from('<HH', data, pe + 20)
    optional = pe + 24
    if optional_size < 112 or optional + optional_size + sections * 40 > len(data):
        raise RuntimeError(f'Truncated PE image: {path}')
    magic = struct.unpack_from('<H', data, optional)[0]
    actual_subsystem = struct.unpack_from('<H', data, optional + 68)[0]
    if (machine, magic, actual_subsystem) != (0xaa64, 0x20b, subsystem):
        raise RuntimeError(f'Wrong machine/format/subsystem: {path}: '
                           f'{machine:#x}/{magic:#x}/{actual_subsystem}')
    for index in range(sections):
        section = optional + optional_size + index * 40
        raw_size, raw_offset = struct.unpack_from('<II', data, section + 16)
        if raw_size and raw_offset + raw_size > len(data):
            raise RuntimeError(f'Truncated PE section {index}: {path}')
    return {'path': str(path), 'bytes': len(data), 'sha256': sha256(path),
            'machine': '0xaa64 (ARM64/AArch64)', 'format': 'PE32+',
            'subsystem': actual_subsystem,
            'subsystem_name': {10: 'EFI application', 11: 'EFI boot-service driver'}[subsystem],
            'sections': sections, 'coff_timestamp': timestamp,
            'characteristics': hex(characteristics),
            'entry_point_rva': hex(struct.unpack_from('<I', data, optional + 16)[0])}


def audit_candidates() -> dict:
    receipt = CANDIDATES / 'verification.json'
    recorded = json.loads(receipt.read_text())['efi']
    result = {'receipt': str(receipt), 'receipt_sha256': sha256(receipt),
              'source_revisions': None,
              'provenance_limit': 'The receipt identifies EFI bytes, not their source '
                                  'revisions. These are not asserted to match zeta.',
              'runtime_validation': 'No boot test performed by this wrapper.', 'loaders': {}}
    for name, subsystem in [('UniXNU', 10), ('DarwinBoot', 11)]:
        metadata = pe_metadata(CANDIDATES / f'{name}.efi', subsystem)
        metadata['windows_path'] = str(Path('G:/UniXNU-Port/artifacts/venus-scale-refresh-012/phone') / f'{name}.efi')
        metadata['matches_existing_receipt'] = all(
            metadata[key] == recorded[name][key] for key in ('bytes', 'sha256'))
        if not metadata['matches_existing_receipt']:
            raise RuntimeError(f'{name}.efi differs from verification.json')
        result['loaders'][name] = metadata
    write_json(OUT / 'existing-candidates.json', result)
    return result


def run(command: list[str], cwd: Path, env: dict, report: dict, log_name: str) -> None:
    record = {'argv': command, 'cwd': str(cwd), 'log': str(OUT / log_name)}
    report['commands'].append(record)
    write_json(OUT / 'build-report.json', report)
    print(f'Running {log_name}: {command}', flush=True)
    with (OUT / log_name).open('w') as log:
        completed = subprocess.run(command, cwd=cwd, env=env, stdout=log,
                                   stderr=subprocess.STDOUT)
    record['returncode'] = completed.returncode
    write_json(OUT / 'build-report.json', report)
    if completed.returncode:
        raise RuntimeError(f'{log_name}: command exited {completed.returncode}; see {OUT / log_name}')


def build(jobs: int, report: dict) -> None:
    edk2 = (TREE / 'refer/edk2').resolve()
    if not (edk2 / 'MdePkg/MdePkg.dec').is_file():
        edk2 = FETCHED_EDK2
    report['sources'] = {
        'UniXNU': revision(SOURCE, EXPECTED_SOURCE, 'package', 'feeds.toml', 'scripts/build-darwinboot.sh'),
        'DarwinBoot': revision(SOURCE / 'drivers/DarwinBoot', EXPECTED_DARWINBOOT),
        'mu_basecore': revision(edk2, EXPECTED_EDK2),
    }
    report['assembled_edk2_link_present'] = (TREE / 'refer/edk2').exists()
    feeds = tomllib.loads((SOURCE / 'feeds.toml').read_text())
    feed = next(item for item in feeds['source'] if item['name'] == 'edk2')
    if feed['commit'] != EXPECTED_EDK2:
        raise RuntimeError('Mu pin differs from the source feeds.toml')
    darwin_pin = git(SOURCE, 'ls-tree', 'HEAD', 'drivers/DarwinBoot').split()[2]
    if darwin_pin != EXPECTED_DARWINBOOT:
        raise RuntimeError('DarwinBoot gitlink differs from the selected revision')
    report['sources']['mu_basecore']['submodule_status'] = git(edk2, 'submodule', 'status')
    for submodule in feed['submodules']:
        pin = git(edk2, 'ls-tree', 'HEAD', submodule).split()[2]
        revision(edk2 / submodule, pin)
    for tool in ('clang', 'lld-link', 'llvm-lib', 'llvm-rc', 'make', 'gcc', 'g++', 'nasm'):
        if not os.access(f'/usr/bin/{tool}', os.X_OK):
            raise RuntimeError(f'Missing existing WSL tool: /usr/bin/{tool}')
    report['tools'] = {tool: subprocess.check_output(
        [f'/usr/bin/{tool}', '--version'], text=True).splitlines()[0]
        for tool in ('clang', 'lld-link', 'make', 'gcc', 'python3')}
    snapshots = OUT / 'sources'
    snapshots.mkdir()
    for origin, destination in ((SOURCE / 'package', snapshots / 'package'),
                                (SOURCE / 'drivers/DarwinBoot', snapshots / 'DarwinBoot'),
                                (edk2, snapshots / 'mu_basecore')):
        # Dereference symlinks: all build writes must land in this output tree.
        shutil.copytree(origin, destination, symlinks=False,
                        ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))
    inventory = {str(path.relative_to(snapshots)): sha256(path)
                 for path in sorted(snapshots.rglob('*')) if path.is_file()}
    write_json(OUT / 'source-files.json', inventory)
    report['source_inventory_sha256'] = sha256(OUT / 'source-files.json')
    workspace = OUT / 'work'
    workspace.mkdir()
    temporary = OUT / 'tmp'
    temporary.mkdir()
    local_edk2 = snapshots / 'mu_basecore'
    # Use distribution tools explicitly rather than the kernel's global shims.
    env = dict(os.environ, PATH='/usr/bin:/bin', TMPDIR=str(temporary),
               PYTHONDONTWRITEBYTECODE='1', PYTHON_COMMAND='/usr/bin/python3',
               CLANG_BIN='/usr/bin/', CLANG_HOST_BIN='/usr/bin/',
               UNIXNU_EDK2=str(local_edk2), UNIXNU_BUILD_DIR=str(workspace), JOBS=str(jobs))
    for key in ('WORKSPACE', 'PACKAGES_PATH', 'EDK_TOOLS_PATH', 'CONF_PATH',
                'MAKEFLAGS', 'CC', 'CXX', 'AR', 'LD', 'PYTHONPATH', 'GCC_PREFIX'):
        env.pop(key, None)
    report['environment'] = {key: env[key] for key in (
        'PATH', 'TMPDIR', 'PYTHONDONTWRITEBYTECODE', 'PYTHON_COMMAND', 'CLANG_BIN',
        'CLANG_HOST_BIN', 'UNIXNU_EDK2', 'UNIXNU_BUILD_DIR', 'JOBS')}
    run(['/bin/bash', str(snapshots / 'package/build.sh'), '-b', 'DEBUG', '-t', 'CLANGPDB'],
        workspace, env, report, 'unixnu-build.log')
    env.update(WORKSPACE=str(workspace),
               PACKAGES_PATH=f'{snapshots / "DarwinBoot"}:{snapshots / "package"}:{local_edk2}',
               EDK_TOOLS_PATH=str(local_edk2 / 'BaseTools'),
               CONF_PATH=str(workspace / 'Build/Conf'))
    env['PATH'] = f'{local_edk2}/BaseTools/BinWrappers/PosixLike:{local_edk2}/BaseTools/Source/C/bin:/usr/bin:/bin'
    report['darwinboot_environment'] = {key: env[key] for key in (
        'WORKSPACE', 'PACKAGES_PATH', 'EDK_TOOLS_PATH', 'CONF_PATH', 'PATH')}
    run([str(local_edk2 / 'BaseTools/BinWrappers/PosixLike/build'),
         '-p', 'DarwinBootPkg/DarwinBoot.dsc', '-m', 'DarwinBootPkg/Driver/DarwinBoot.inf',
         '-a', 'AARCH64', '-b', 'DEBUG', '-t', 'CLANGPDB', '-n', str(jobs)],
        workspace, env, report, 'darwinboot-build.log')
    binaries = {
        'UniXNU': (workspace / 'Build/Out/AARCH64-DEBUG/UniXNU.efi', 10),
        'DarwinBoot': (workspace / 'build/DarwinBoot/DEBUG_CLANGPDB/AARCH64/DarwinBoot.efi', 11),
    }
    # Validate both before publishing the pair at the top level.
    report['build_products'] = {name: pe_metadata(path, subsystem)
                                for name, (path, subsystem) in binaries.items()}
    report['outputs'] = {}
    for name, (path, subsystem) in binaries.items():
        destination = OUT / f'{name}.efi'
        shutil.copy2(path, destination)
        report['outputs'][name] = pe_metadata(destination, subsystem)
    report['result'] = 'built-and-PE-verified'
    report['runtime_validation'] = 'Not run; ready for the caller-owned QEMU ESP/entry test.'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--verify-existing', action='store_true',
                        help='Only verify the retained loaders and their existing receipt')
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    if sys.platform != 'linux' or not OUT.parent.is_dir():
        parser.error('Run in UniXNU-Build WSL with /root/unixnu-build present')
    if OUT.is_symlink():
        parser.error(f'Output directory must not be a symlink: {OUT}')
    if args.verify_existing:
        OUT.mkdir(exist_ok=True)
        print(json.dumps(audit_candidates(), indent=2))
        return 0
    if OUT.exists():
        parser.error(f'Build output already exists; preserve it: {OUT}. Use --verify-existing to audit fallback inputs.')
    OUT.mkdir()
    report = {'result': 'in-progress', 'commands': [], 'wrapper_sha256': sha256(Path(__file__))}
    try:
        build(args.jobs, report)
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as error:
        report['result'] = 'blocked'
        report['blocker'] = str(error)
        try:
            report['existing_candidates'] = audit_candidates()
        except (OSError, RuntimeError, ValueError) as audit_error:
            report['candidate_audit_error'] = str(audit_error)
    write_json(OUT / 'build-report.json', report)
    print(json.dumps(report, indent=2))
    return 0 if report['result'] == 'built-and-PE-verified' else 1


if __name__ == '__main__':
    raise SystemExit(main())
