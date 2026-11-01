#!/usr/bin/env python3
"""Stage the WSL-built XNU 12377 and observe real UEFI/DarwinBoot QEMU entry."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

TREE = Path('/root/unixnu-build/zeta-venus-wsl/zeta/tree')
OBJECTS = TREE / 'build/xnu-12377.121.6/ios-obj/DEVELOPMENT_ARM64_BCM2837'
LOADERS = Path('/root/unixnu-build/zeta-qemu-loaders')
FIRMWARE = Path('/root/unixnu-build/qemu-firmware/edk2-aarch64-code.fd')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def identity(path):
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def macho(path):
    data = path.read_bytes()
    magic, cpu, subtype, kind, count, size = struct.unpack_from('<6I', data)
    if (magic, cpu, subtype, kind) != (0xfeedfacf, 0x100000c, 0, 2):
        raise RuntimeError(f'Expected native ARM64 executable: {path}')
    segments, text = [], {}
    at, entry, deployment = 32, None, None
    for _ in range(count):
        cmd, length = struct.unpack_from('<II', data, at)
        if length < 8 or not at + length <= 32 + size <= len(data):
            raise RuntimeError('Invalid Mach-O load command')
        if cmd == 0x19:
            name = data[at + 8:at + 24].split(b'\0')[0].decode()
            va, vmsize, offset, filesize = struct.unpack_from('<4Q', data, at + 24)
            if offset + filesize > len(data):
                raise RuntimeError('Truncated Mach-O segment')
            segments.append(dict(name=name, va=va, vmsize=vmsize,
                                 offset=offset, filesize=filesize))
            nsects = struct.unpack_from('<I', data, at + 64)[0]
            if 72 + 80 * nsects > length:
                raise RuntimeError('Truncated Mach-O section table')
            for i in range(nsects):
                section = at + 72 + 80 * i
                sname = data[section:section + 16].split(b'\0')[0].decode()
                addr, nbytes, fileoff = struct.unpack_from('<QQI', data, section + 32)
                if sname == '__text':
                    if fileoff + nbytes > len(data):
                        raise RuntimeError('Truncated text section')
                    text[name + '/' + sname] = dict(va=hex(addr), bytes=nbytes,
                        sha256=hashlib.sha256(data[fileoff:fileoff + nbytes]).hexdigest())
        elif cmd == 0x32:
            deployment = struct.unpack_from('<II', data, at + 8)
        elif cmd == 5:
            if length != 288:
                raise RuntimeError('Unexpected ARM64 thread command')
            entry = struct.unpack_from('<Q', data, at + 272)[0]
        at += length
    if at != 32 + size or entry is None or not text or deployment != (2, 0x1a0000):
        raise RuntimeError(f'Expected linked iOS26.0 kernel: {deployment}, {entry}')
    return data, segments, dict(**identity(path), entry_va=hex(entry),
                               deployment='iOS 26.0', text_sections=text)


def main():
    global TREE, OBJECTS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, default=TREE)
    parser.add_argument('--kernel', type=Path, help='Explicit sealed native kernel; also supplies symbols')
    parser.add_argument('--output', type=Path, required=True, help='New WSL output directory')
    parser.add_argument('--checkpoint', choices=['arm_init', 'arm_vm_init', 'arm_vm_init_return', 'bsd_init'],
                        default='arm_vm_init_return')
    parser.add_argument('--timeout', type=int, default=90)
    args = parser.parse_args()
    TREE = args.tree.resolve()
    OBJECTS = TREE / 'build/xnu-12377.121.6/ios-obj/DEVELOPMENT_ARM64_BCM2837'
    output = args.output.resolve()
    if not output.is_relative_to(Path('/root/unixnu-build')) or not output.parent.is_dir():
        parser.error('Use an existing /root/unixnu-build parent')
    if not 5 <= args.timeout <= 600:
        parser.error('Timeout must be 5..600 seconds')
    output.mkdir()  # Preserve all earlier runs, including failures.
    report = dict(result='preparing', checkpoint=args.checkpoint, commands=[],
                  guest_code_modified=False, hardware_boot_demonstrated=False,
                  os_boot_demonstrated=False, runner=identity(Path(__file__)))
    report_path = output / 'entry-report.json'
    try:
        kernel = args.kernel.resolve() if args.kernel else OBJECTS / 'mach.development.bcm2837'
        symbols_file = kernel if args.kernel else OBJECTS / 'mach.development.bcm2837.unstripped'
        _, _, report['kernel'] = macho(kernel)
        _, _, report['symbols_kernel'] = macho(symbols_file)
        if report['kernel']['text_sections'] != report['symbols_kernel']['text_sections']:
            raise RuntimeError('Stripped and unstripped executable sections differ')
        nm = subprocess.check_output(['/usr/bin/llvm-nm', '--defined-only', str(symbols_file)], text=True)
        symbols = {name: int(address, 16) for address, kind, name in
                   re.findall(r'^([0-9a-fA-F]+)\s+(\S)\s+(\S+)$', nm, re.M) if kind.upper() != 'A'}
        report['symbols'] = {name: hex(symbols[name]) for name in
                             ('_arm_init', '_arm_vm_init', '_bsd_init', '_panic')}
        # XNU12377 builds TCR_EL1_BOOT with MOV64 in start.s; it has no
        # XNU10063 _sysreg_restore data symbol. Verify the real register below.
        work = TREE / '.cache/xnu-12377.121.6-work'
        revision = subprocess.check_output(['git', '-C', str(work), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != 'ac9718fb1af618d5ce8678d0dc6e8a58f252216f':
            raise RuntimeError('XNU source revision differs')
        report['xnu_revision'] = revision
        diff = subprocess.check_output(['git', '-C', str(work), 'diff', '--binary'])
        (output / 'xnu-working-tree.patch').write_bytes(diff)
        report['xnu_diff'] = identity(output / 'xnu-working-tree.patch')
        report['version_source'] = identity(OBJECTS / 'version.c')
        report['loader_build_report'] = identity(LOADERS / 'build-report.json')
        loader_build = json.loads((LOADERS / 'build-report.json').read_text())
        if loader_build['result'] != 'built-and-PE-verified':
            raise RuntimeError('Loaders have no successful build receipt')
        esp = output / 'esp'
        payloads = esp / 'EFI/UniXNU/Payloads'
        payloads.mkdir(parents=True)
        (esp / 'EFI/BOOT').mkdir()
        report['loaders'] = {}
        for name, destination in [('UniXNU', esp / 'EFI/BOOT/BOOTAA64.EFI'),
                                  ('DarwinBoot', payloads / 'DarwinBoot.efi')]:
            source = LOADERS / (name + '.efi')
            if sha(source) != loader_build['outputs'][name]['sha256']:
                raise RuntimeError(f'{name} differs from build receipt')
            shutil.copyfile(source, destination)
            report['loaders'][name] = identity(destination)
        staged = payloads / 'kernel.macho'
        shutil.copyfile(kernel, staged)
        generator = TREE / 'scripts/qemu-entry/make-dt.py'
        dt_command = [sys.executable, '-B', str(generator), '--output', str(payloads / 'kernel.macho.adt'),
                      '--dram-size', '0x80000000', '--owned-memory-size', '0x20000000',
                      '--armvirt', '--armcpu', '--nvram-proxy', '--crypto-hash-method', 'sha2-384']
        report['commands'].append(dt_command)
        subprocess.run(dt_command, check=True)
        codec_path = Path(__file__).with_name('inject-a660-firmware-adt.py')
        spec = importlib.util.spec_from_file_location('adt_codec', codec_path)
        codec = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(codec)
        adt = payloads / 'kernel.macho.adt'
        dt = codec.parse(adt.read_bytes())
        chosen = codec.find(dt, 'chosen')
        seed = os.urandom(256)
        chosen.props = [(key, seed if key == 'random-seed' else value) for key, value in chosen.props]
        armio = codec.find(dt, 'arm-io')
        # The upstream test DT includes unused Qualcomm UFS placeholders.
        # This entry test describes only hardware actually present in QEMU.
        armio.children = [child for child in armio.children if child.name not in ('ufshc', 'ufsphy')]
        adt.write_bytes(codec.dump(dt))
        check = codec.find(codec.parse(adt.read_bytes()), 'chosen')
        if [value for key, value in check.props if key == 'random-seed'] != [seed]:
            raise RuntimeError('ADT random-seed round trip failed')
        report['adt'] = dict(**identity(adt), random_seed_bytes=len(seed),
                             random_seed_sha256=hashlib.sha256(seed).hexdigest(),
                             generator=identity(generator), codec=identity(codec_path))
        (esp / 'EFI/UniXNU/unixnu.toml').write_text('''version = 1
[boot]
timeout = 1
default = "zeta-12377"
[kits]
autoload = false
[[driver]]
path = "Payloads/DarwinBoot.efi"
[[entry]]
id = "zeta-12377"
title = "WSL zeta XNU 12377 QEMU entry"
type = "xnu"
path = "Payloads/kernel.macho"
args = "-v serial=3 cpus=1 debug=0x14e -no_slto_panic"
''')
        original = TREE / 'scripts/qemu-entry/gdb-stop.py'
        code = original.read_text()
        replacements = {
            "if register.attrib['name'] in wanted:":
                "if register.attrib['name'] in wanted or register.attrib['name'] == 'SCTLR':",
            "report['system_registers'][register.attrib['name']] = hex(value)":
                "report['system_registers']['SCTLR_EL1' if register.attrib['name'] == 'SCTLR' else register.attrib['name']] = hex(value)",
        }
        for before, after in replacements.items():
            if code.count(before) != 1:
                raise RuntimeError('Upstream observer changed: ' + before)
            code = code.replace(before, after)
        observer = output / 'gdb-stop.py'
        observer.write_text(code)
        report['observer'] = dict(upstream=identity(original), adapted=identity(observer),
                                  replacements=replacements)
        report['firmware'] = identity(FIRMWARE)
        report['qemu_version'] = subprocess.check_output(['qemu-system-aarch64', '--version'], text=True).splitlines()[0]
        target = symbols['_' + args.checkpoint.removesuffix('_return')]
        command = [sys.executable, '-B', str(observer), hex(target), '--fixture', str(output),
                   '--esp', str(esp), '--kernel', str(staged), '--firmware', str(FIRMWARE),
                   '--gic-version', '3', '--qemu-memory-mib', '2048', '--system-registers',
                   '--timeout', str(args.timeout), '--also-stop', hex(symbols['_panic'])]
        if args.checkpoint != 'arm_init':
            command += ['--trace-address', hex(symbols['_arm_init'])]
        if args.checkpoint.endswith('_return'):
            command += ['--finish-function']
        report['commands'].append(command)
        report['result'] = 'staged'
        save(report_path, report)
        env = dict(os.environ, PYTHONPATH=str(original.parent), PYTHONDONTWRITEBYTECODE='1')
        with (output / 'observer.log').open('w') as log:
            result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        report['observer_returncode'] = result.returncode
        if result.returncode:
            raise RuntimeError(f'QEMU observer failed ({result.returncode}); see observer.log')
        stopped = json.loads((output / 'gdb-stop.json').read_text())
        regs = {key: int(value, 16) for key, value in stopped['system_registers'].items()}
        report['observation'] = {key: stopped[key] for key in
            ('pc', 'pstate', 'bounded_timeout_interrupted', 'boot_path', 'trace_events', 'system_registers')}
        reached = (stopped.get('function_return_stack_matched', False) and
                   int(stopped['finished_function_entry'], 16) == target) if args.checkpoint.endswith('_return') else int(stopped['pc'], 16) == target
        checks = dict(checkpoint_reached=bool(reached), no_timeout=not stopped['bounded_timeout_interrupted'],
                      kernel_identity=stopped['kernel_sha256'] == report['kernel']['sha256'] == sha(staged),
                      real_uefi=stopped['boot_path'] == 'uefi-unixnu-darwinboot',
                      el1=((int(stopped['pstate'], 16) >> 2) & 3) == 1,
                      mmu_enabled=bool(regs['SCTLR_EL1'] & 1),
                      native_4k=((regs['TCR_EL1'] >> 14) & 3, (regs['TCR_EL1'] >> 30) & 3) == (0, 2))
        report['checks'] = checks
        if not all(checks.values()):
            raise RuntimeError('Entry qualification failed: ' + ', '.join(k for k, v in checks.items() if not v))
        report['result'] = 'passed'
    except Exception as error:
        report.update(result='failed', error=str(error))
        save(report_path, report)
        print(f'FAIL: {error}\nReport: {report_path}', file=sys.stderr)
        return 1
    save(report_path, report)
    print(f'PASS: {args.checkpoint}, real UEFI/DarwinBoot, EL1, MMU, native 4K\nReport: {report_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
