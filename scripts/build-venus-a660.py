#!/usr/bin/env python3
"""Build zeta's real A660 GPU dependency closure with the Venus iOS17 XNU recipes.

Original repositories are read-only. Patches apply to content-addressed copies.
A failed unit outside the required closure is recorded, never substituted.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import importlib.util

ROOT = Path('/mnt/g/UniXNU-Port')
DEVICE = ROOT / 'ports/UniXNU-venus'
BASE = ROOT / 'sources/UniXNU-zeta-base'
PATCHES = ROOT / 'sources/UniXNU-zeta-none24smu/package'
BOARD = DEVICE / 'package/Adreno660'
DEFAULT_TREE = Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root/tree')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tree', type=Path, default=DEFAULT_TREE)
parser.add_argument('--output', type=Path, help='Separate GPU build directory; preserve historical candidates')
parser.add_argument('--abi-kernel-dir', type=Path, default=ROOT / 'artifacts/venus-metal-touch/kernel-link-33')
args = parser.parse_args()
TREE = args.tree.resolve()
OUT = args.output.resolve() if args.output else TREE / 'build/venus-a660'
OUT.mkdir(parents=True, exist_ok=True)
OBJ = TREE / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
os.environ.setdefault('CCC_OVERRIDE_OPTIONS', '# +-Wno-missing-designated-field-initializers +-Wno-unused-but-set-global')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(parts, **kw):
    return subprocess.check_output([str(p) for p in parts], text=True, **kw).strip()


def require(ok, why):
    if not ok:
        raise SystemExit(why)


require(command(['git', '-C', BASE, 'rev-parse', 'HEAD']) == '35c384e84266343991fd14706e8c651f7d2e09ed',
        'Unexpected fixed zeta base')


def patched(module, source):
    # iOS17 uses 4K VM pages. Preserve its stricter native4K CPU contract;
    # hostsim-only patches are not part of the kernel dependency closure.
    chosen = [p for p in sorted(PATCHES.glob(module + '-*.patch'))
              if p.name != 'NativeAdreno-16k-vm.patch' and 'host-' not in p.name]
    revision = command(['git', '-C', source, 'rev-parse', 'HEAD'])
    inputs = {'revision': revision, 'patches': {p.name: sha(p) for p in chosen}}
    key = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:16]
    destination = OUT / (module + '-' + key)
    receipt = destination / 'venus-source-receipt.json'
    if not receipt.exists():
        require(not destination.exists(), 'Partial source copy needs inspection: ' + str(destination))
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns('.git'))
        for patch in chosen:
            result = subprocess.run(['patch', '-p1', '--batch', '--forward', '--fuzz=0',
                                     '-d', str(destination), '-i', str(patch)], capture_output=True, text=True)
            (OUT / (module + '-' + patch.name + '.log')).write_text(result.stdout + result.stderr)
            require(result.returncode == 0, 'Patch failed: ' + patch.name + '\n' + result.stdout + result.stderr)
        receipt.write_text(json.dumps(inputs, indent=2) + '\n')
    else:
        require(json.loads(receipt.read_text()) == inputs, 'Source receipt mismatch')
    return destination, inputs


ADRENO, adreno_inputs = patched('NativeAdreno', BASE / 'drivers/NativeAdreno')
SMMU, smmu_inputs = patched('ArmSmmu4K', BASE / 'kits/ArmSmmu4K')
spec = importlib.util.spec_from_file_location('venus_metal_audit', DEVICE / 'scripts/audit-venus-metal-discovery.py')
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)
accelerator_abi = audit_module.audit(args.abi_kernel_dir)
(OUT / 'accelerator-abi.json').write_text(json.dumps(accelerator_abi, indent=2) + '\n')
# The generic adapter's relative include names the matching Metal ABI header.
# Its three original imports are qualified against the actual Venus prelink.
(OUT / 'NativeMetal').mkdir(exist_ok=True)
abi_header = OUT / 'NativeMetal/OriginalAcceleratorABI.h'
abi_header.write_bytes((BASE / 'drivers/NativeMetal/OriginalAcceleratorABI.h').read_bytes())
FIRMWARE = BASE / 'kits/AdrenoFirmware'
PM4 = BASE / 'kits/AdrenoPM4'
INCLUDES = [BOARD, ADRENO, SMMU, FIRMWARE, PM4, TREE / '.cache/xnu-work/osfmk']


def recipe(name):
    return json.loads((OBJ / name).read_text().strip().rstrip(','))


cpp_record = recipe('iokit/DEVELOPMENT/IOPlatformExpert.cpo.json')
c_record = recipe('bsd/DEVELOPMENT/kern_exec.o.json')


def compile_unit(source, destination, record):
    original = record['arguments']
    cmd, i = [], 0
    while i < len(original):
        part = original[i]
        if part == record['file']:
            cmd.append(str(source))
        elif part == '-o':
            cmd.extend(['-o', str(destination)])
            i += 1
        elif part in ('-MF', '-MJ', '-MT', '-MQ'):
            i += 1
        elif part == '-Xclang' and original[i + 1].startswith('-W'):
            i += 1
        elif part not in ('-MD', '-MMD', '-MP') and not part.startswith('-W'):
            cmd.append(part)
        i += 1
    cmd.extend(['-mgeneral-regs-only', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                '-Wno-deprecated-declarations', '-Wno-c99-designator', '-Wno-reorder-init-list',
                '-Wno-missing-designated-field-initializers', '-Wno-unnecessary-virtual-specifier',
                '-Wno-deprecated-enum-enum-conversion'])
    for path in INCLUDES:
        cmd.extend(['-I', str(path)])
    result = subprocess.run(cmd, cwd=record['directory'], capture_output=True, text=True, timeout=300)
    (OUT / (source.stem + '.log')).write_text(result.stdout + result.stderr)
    (OUT / (source.stem + '.command.json')).write_text(json.dumps(cmd, indent=2) + '\n')
    return result.returncode == 0


probe = OUT / 'GpuPowerProbe.o'
require(compile_unit(BOARD / 'GpuPowerProbe.cpp', probe, cpp_record),
        'A660 board probe failed; inspect ' + str(OUT / 'GpuPowerProbe.log'))
excluded = {'NativeAdrenoClient.cpp', 'NativeAdrenoService.cpp', 'NativeAdrenoAccelerator.cpp',
            'NativeAdrenoGmuConfig.cpp', 'NativeAdrenoGmuPlatform.cpp', 'NativeAdrenoGmuService.cpp'}
candidates = [p for p in sorted(ADRENO.glob('NativeAdreno*.cpp')) if p.name not in excluded]
candidates += sorted(SMMU.glob('ArmSmmu4K*.c'))
candidates += [PM4 / 'AdrenoPM4.c', BOARD / 'ZetaGmu.c', BOARD / 'ZetaGmuVotes.c']
candidates += [FIRMWARE / (name + '.c') for name in ('AdrenoFirmware', 'AdrenoHfi', 'AdrenoHfiStartup')]
candidates += [BOARD / 'VenusMetalPublication.cpp', ADRENO / 'NativeAdrenoAccelerator.cpp']
objects, failures = {}, {}
for source in candidates:
    obj = OUT / (source.stem + '.o')
    if compile_unit(source, obj, c_record if source.suffix == '.c' else cpp_record):
        if source.name == 'NativeAdrenoAccelerator.cpp':
            late = OUT / 'NativeAdrenoAccelerator.late.o'
            subprocess.run(['python3', str(TREE / 'scripts/macho-late-init.py'), str(obj), str(late),
                            '--initializer', '__GLOBAL__sub_I_NativeAdrenoAccelerator.cpp'], check=True)
            headers = command(['/usr/bin/llvm-objdump', '--macho', '--section-headers', late])
            require('__mod_init_func' not in headers, 'Accelerator initializer must run after IOGPUFamily load')
            obj = late
        objects[source.name] = (source, obj)
    else:
        errors = [s for s in (OUT / (source.stem + '.log')).read_text().splitlines() if 'error:' in s]
        failures[source.name] = errors[:8]


def symbols(obj, *options):
    return set(command(['/usr/bin/llvm-nm', '--just-symbol-name', *options, obj]).split())


providers = {}
for name, (source, obj) in objects.items():
    for symbol in symbols(obj, '--defined-only', '--extern-only'):
        if symbol in providers and providers[symbol] != name:
            # Weak defaults are not needed by this board. A closure must not
            # select two strong providers under the same exported name.
            continue
        providers[symbol] = name
wanted = symbols(probe, '--undefined-only')
required = {'_NativeAdrenoGmuContextBringup', '_NativeAdrenoGpuContextBringup', '_native_adreno_publish',
             '_ZetaGmuColdStart', '_ZetaGmuBuildStartup', '_venus_metal_publish',
             '_venus_metal_wait_before_launchd', '_native_adreno_accelerator_allocate'}
wanted.update(required)
selected = set()
while True:
    new = {providers[s] for s in wanted if s in providers} - selected
    if not new:
        break
    selected.update(new)
    for name in new:
        wanted.update(symbols(objects[name][1], '--undefined-only'))
missing = sorted(required - providers.keys())
bindings = accelerator_abi['bindings']
accelerator_imports = {n for n in symbols(objects['NativeAdrenoAccelerator.cpp'][1], '--undefined-only') if 'IOAcceleratorES' in n}
require(accelerator_imports == set(bindings), 'Unexpected original accelerator imports')
asm = OUT / 'accelerator-original-bindings.S'
asm.write_text(''.join(f'.globl {name}\n.set {name}, {address}\n' for name, address in sorted(bindings.items())))
binding_object = OUT / 'accelerator-original-bindings.o'
subprocess.run(['/usr/bin/clang-18', '-target', 'arm64-apple-ios17.0', '-c', str(asm), '-o', str(binding_object)],
               env={k: v for k, v in os.environ.items() if k != 'CCC_OVERRIDE_OPTIONS'}, check=True)
report = {
    'target': 'arm64-apple-ios17.0', 'xnu': '10063.141.1',
    'base_commit': '35c384e84266343991fd14706e8c651f7d2e09ed',
    'adreno_source': adreno_inputs, 'smmu_source': smmu_inputs,
    'selected_units': sorted(selected), 'excluded_a740_units': sorted(excluded - {'NativeAdrenoAccelerator.cpp'}),
    'accelerator_abi': accelerator_abi,
    'metal_discovery': 'original-IOAcceleratorES-late-adapter',
    'failed_units': failures, 'missing_required_providers': missing,
    'board_sources': {p.name: sha(p) for p in sorted(BOARD.glob('*')) if p.is_file()},
    'out': str(OUT), 'gpu_hardware_tested': False,
}
(OUT / 'build-report.json').write_text(json.dumps(report, indent=2) + '\n')
require(not missing, 'Required A660 providers failed: ' + ', '.join(missing))
# Any missing symbol from a failed candidate makes the compilation incomplete,
# even if that dependency was weak-imported by the reference board probe.
report['unresolved_external_symbols'] = sorted(wanted - providers.keys() - symbols(probe, '--defined-only', '--extern-only'))
archive = OUT / 'libVenusA660.a'
archive.unlink(missing_ok=True)
subprocess.run(['/usr/bin/llvm-ar', 'rcs', str(archive), str(probe),
                 *[str(objects[name][1]) for name in sorted(selected)], str(binding_object)], check=True)
report.update(archive_sha256=sha(archive), archive_bytes=archive.stat().st_size,
              required_providers={name: providers[name] for name in sorted(required)},
               compiled_objects={name: sha(objects[name][1]) for name in sorted(selected)},
               archive=str(archive),
               input_files={str(path): sha(path) for path in [
                   *sorted(p for p in BOARD.iterdir() if p.is_file()), abi_header,
                   *[objects[name][0] for name in sorted(selected)]]},
               object_files={str(path): sha(path) for path in [probe, binding_object,
                   *[objects[name][1] for name in sorted(selected)]]})
(OUT / 'build-report.json').write_text(json.dumps(report, indent=2) + '\n')
os.sync()
print('PASS: A660 GPU/GMU/publication dependency closure compiled against real iOS17 XNU recipes')
print('Archive:', archive, report['archive_sha256'])
print('Selected:', ', '.join(sorted(selected)))
print('Non-selected compilation failures:', json.dumps(failures, indent=2))
