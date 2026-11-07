#!/usr/bin/env python3
"""Rebuild every native object from a locked source recipe in a fresh directory."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import re
import sys
import struct
from collections import Counter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--kdk', type=Path, required=True)
    parser.add_argument('--clang', type=Path, required=True)
    parser.add_argument('--ld', type=Path, required=True)
    parser.add_argument('--ar', default='llvm-ar')
    parser.add_argument('--source', action='append', default=[], metavar='KEY=DIR',
                        help='External source root named by the portable manifest')
    parser.add_argument('--sdk-runtime-report', type=Path,
                        help='Receipt for source-built SDK kernel runtime archives')
    parser.add_argument('--finish-existing', action='store_true',
                        help='Resume post-processing only after verifying every completed source compilation receipt')
    parser.add_argument('-j', type=int, default=8)
    args = parser.parse_args()
    root = args.manifest.resolve().parent
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    portable = manifest.get('schema') == 2
    external_sources = {}
    for value in args.source:
        key, separator, directory = value.partition('=')
        if not separator or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key) or key in external_sources:
            parser.error('--source requires a unique uppercase KEY=DIR')
        path = Path(directory).resolve(strict=True)
        if not path.is_dir():
            parser.error('External source must be a directory: ' + directory)
        external_sources[key] = path
    out = args.output.resolve()
    if out.exists() != args.finish_existing or not 1 <= args.j <= 32:
        parser.error('Fresh output required, or --finish-existing for a completed compilation; jobs1..32')
    for path in (args.sdk, args.kdk, args.clang, args.ld):
        if not path.exists(): parser.error('Required input missing: ' + str(path))
    source_runtime = None
    if args.sdk_runtime_report:
        source_runtime = json.loads(args.sdk_runtime_report.read_text())
        if source_runtime.get('result') != 'runtime-built' or source_runtime.get('source_units') != 7 or \
                source_runtime.get('previous_sdk_archives_copied') is not False or \
                Path(source_runtime['sdk']).resolve() != args.sdk.resolve():
            raise ValueError('SDK runtime receipt does not describe this source-built SDK')
        for name in ('libcc_kext.a', 'libfirehose_kernel.a'):
            path = args.sdk / 'usr/local/lib/kernel' / name
            if hashlib.sha256(path.read_bytes()).hexdigest() != source_runtime['libraries'].get(name):
                raise ValueError('Source-built SDK runtime archive hash mismatch: ' + name)
    work = out / 'work'
    if not args.finish_existing:
        out.mkdir(parents=True)
        work.mkdir()
    elif not work.is_dir():
        parser.error('Completed source workspace is missing')
    for name, digest in manifest['files'].items():
        source = root / ('sources' if portable else 'sources/work') / name
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError('Source hash mismatch: ' + name)
        if not args.finish_existing:
            destination = work / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    old_tree = '/work/zeta-ios26-root-033/tree'
    replacements = [(old_tree + '/.cache/xnu-12377.121.6-fakeroot', '${SDK}'),
                    (old_tree + '/.cache/fakeroot', '${SDK}'),
                    (old_tree + '/.cache/xnu-12377.121.6-kdk', '${KDK}'),
                    ('/work/', str(work) + '/')]
    def translate(value):
        if portable:
            bindings = dict(WORK=work, SDK=args.sdk.resolve(), KDK=args.kdk.resolve(),
                            CLANG=args.clang.resolve(), LD=args.ld.resolve(), PYTHON=sys.executable)
            bindings.update(external_sources)
            return re.sub(r'\$\{([A-Z][A-Z0-9_]*)\}', lambda m: str(bindings[m[1]]), value)
        for old, new in replacements: value = value.replace(old, new)
        return value.replace('${SDK}', str(args.sdk.resolve())).replace('${KDK}', str(args.kdk.resolve()))
    def command(values):
        if portable:
            return [translate(v) for v in values]
        values = list(values)
        if values[:4] == ['xcrun', '--sdk', 'iphoneos', 'clang']: values = [str(args.clang), *values[4:]]
        else: values[0] = str(args.clang)
        return [values[0], *[translate(v).replace('--ld-path=' + str(work / 'port/toolchain/cctools-lto/bin/ld'), '--ld-path=' + str(args.ld)) for v in values[1:]]]
    for name, record in ({} if args.finish_existing else manifest.get('external_files', {})).items():
        source = Path(translate(record['source']))
        data = source.read_bytes()
        if record.get('source_sha256') and hashlib.sha256(data).hexdigest() != record['source_sha256']:
            raise ValueError('External adapter input hash mismatch: ' + name)
        transform = record.get('transform')
        if transform == 'corecrypto12377-registration':
            text = data.decode('utf-8')
            registration = '    register_crypto_functions(&kpis);'
            definition = 'kern_return_t corecrypto_kext_start(kmod_info_t *ki, void *d)\n{'
            if text.count(registration) != 1 or text.count(definition) != 1:
                raise ValueError('Corecrypto source anchors changed')
            text = text.replace(definition, '#include "${WORK}/tree/scripts/corecrypto-12377-kpi.h"\n\n' + definition)
            text = text.replace(registration, '    cc12377_complete_kpis(&kpis);\n' + registration)
            text = 'extern int native_apfs_crypto_kpis_selftest(void);\n' + text
            text = text.replace(registration,
                '    if (native_apfs_crypto_kpis_selftest() != 0) {\n'
                '        panic("source crypto: APFS digest selftest failed");\n'
                '    }\n' + registration)
            text = 'extern int zeta_mldsa26_native_apfs_mldsa_selftest(void);\n' + text
            text = text.replace(registration,
                '    if (zeta_mldsa26_native_apfs_mldsa_selftest() != 0) {\n'
                '        panic("source crypto: APFS ML-DSA selftest failed");\n'
                '    }\n' + registration)
            data = text.encode('utf-8')
        elif transform == 'mldsa-known-answer':
            arrays = {}
            text = data.decode('utf-8')
            for original, renamed, expected in (
                    ('pubkey_kat', 'apfs_mldsa_kat_pubkey', 2592),
                    ('sig_kat', 'apfs_mldsa_kat_signature', 4627),
                    ('msg_kat', 'apfs_mldsa_kat_message', 32)):
                matches = re.findall(r'\b' + original + r'\[[^\]]*\]\s*=\s*\{([^}]+)\}', text)
                if len(matches) != 1:
                    raise ValueError('Ambiguous ML-DSA known-answer array: ' + original)
                values = bytes(int(v.strip(), 0) for v in matches[0].split(',') if v.strip())
                if len(values) != expected:
                    raise ValueError('ML-DSA known-answer array length changed')
                arrays[renamed] = values
            generated = '/* Generated from immutable external Apple source; do not commit. */\n'
            generated += '\n'.join(f'static const unsigned char {key}[{len(values)}] = {{\n'
                + ',\n'.join(','.join(f'0x{v:02x}' for v in values[i:i + 24])
                            for i in range(0, len(values), 24)) + '\n};'
                for key, values in arrays.items()) + '\n'
            data = generated.encode('utf-8')
        elif transform:
            raise ValueError('Unknown external source adapter: ' + transform)
        if hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError('External source hash mismatch: ' + name)
        destination = work / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    # Generated adapters used absolute include paths. Relocate include operands
    # only; never rewrite runtime paths or arbitrary string literals.
    for name in (() if args.finish_existing else set(manifest['files']) | set(manifest.get('external_files', {}))):
        path = work / name
        if path.suffix in ('.c', '.cpp', '.h', '.hpp', '.inc'):
            text = path.read_text(encoding='utf-8')
            replaced = re.sub(r'(?m)^(\s*#\s*include\s+")((?:/work/|\$\{)[^"\n]+)(")',
                              lambda m: m[1] + translate(m[2]) + m[3], text)
            if replaced != text: path.write_text(replaced, encoding='utf-8')
        elif name in manifest.get('path_templates', []):
            text = path.read_text(encoding='utf-8')
            path.write_text(translate(text), encoding='utf-8')
    public_external = work / ('tree' if portable else 'zeta-ios26-root-033/tree') / '.cache/xnu-12377.121.6-work/EXTERNAL_HEADERS'
    platform = args.kdk / 'System/Library/Frameworks/Kernel.framework/Versions/A/PrivateHeaders/platform'
    for name in (() if args.finish_existing else ('CoreEntitlements', 'TrustCache')):
        if (platform / name).is_dir(): shutil.copytree(platform / name, public_external / name, dirs_exist_ok=True)
    kernel_header = args.kdk / 'System/Library/KernelSupport/CoreEntitlements/V2/Kernel.h'
    if not args.finish_existing and kernel_header.is_file():
        destination = public_external / 'CoreEntitlements/V2/Kernel.h'
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(kernel_header, destination)
    def compile_command(recipe):
        argv = command(recipe['argv'])
        # Dependency JSON from the old compiler is not a source dependency.
        selected = []; index = 0
        while index < len(argv):
            if argv[index] in ('-MF', '-MJ', '-MT', '-MQ'): index += 2; continue
            if argv[index] not in ('-MD', '-MMD', '-MP'): selected.append(argv[index])
            index += 1
        return selected
    def build(item):
        output, recipe = item
        target = Path(translate(output)); target.parent.mkdir(parents=True, exist_ok=True)
        cwd = Path(translate(recipe['cwd'])); cwd.mkdir(parents=True, exist_ok=True)
        selected = compile_command(recipe)
        log = target.with_suffix(target.suffix + '.log')
        with log.open('xb') as stream:
            result = subprocess.run(selected, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
        if result.returncode: raise RuntimeError('Compile failed: ' + output + '; ' + str(log))
        row = dict(output=str(target.relative_to(out)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            source_manifest_sha256=manifest_sha256, command=selected)
        target.with_suffix(target.suffix + '.source-receipt.json').write_text(json.dumps(row, indent=2) + '\n')
        return row
    built = []
    failures = []
    if args.finish_existing:
        completed = json.loads((out / 'compilation.json').read_text())
        if completed['failures'] or len(completed['objects']) != len(manifest['recipes']):
            raise ValueError('Post-processing requires the complete source compilation closure')
        by_output = {row['output']: row for row in completed['objects']}
        for output, recipe in manifest['recipes'].items():
            target = Path(translate(output))
            relative = str(target.relative_to(out))
            row = by_output.get(relative)
            receipt = json.loads(target.with_suffix(target.suffix + '.source-receipt.json').read_text())
            if not row or row != receipt or row['source_manifest_sha256'] != manifest_sha256 or \
                    row['command'] != compile_command(recipe) or \
                    hashlib.sha256(target.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('Completed source object or compilation receipt changed: ' + output)
            built.append(row)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.j) as executor:
            futures = {executor.submit(build, item): item[0] for item in manifest['recipes'].items()}
            for future in concurrent.futures.as_completed(futures):
                try:
                    built.append(future.result())
                except Exception as error:
                    failures.append(dict(output=futures[future], error=str(error)))
                if (len(built) + len(failures)) % 100 == 0:
                    print(f'Completed {len(built) + len(failures)}/{len(futures)}; failures={len(failures)}', flush=True)
        (out / 'compilation.json').write_text(json.dumps(dict(objects=built, failures=failures), indent=2) + '\n')
    if failures:
        raise RuntimeError(f'{len(failures)} source compilations failed; see {out / "compilation.json"}')
    # XNU's Makefile filelist rules run SETUP/setsegname after compilation.
    # Preserve those non-debug section labels without changing code bytes.
    built_by_path = {row['output']: row for row in built}
    for output, expected_sections in manifest.get('object_section_maps', {}).items():
        path = Path(translate(output))
        data = bytearray(path.read_bytes())
        if data[:4] != b'\xcf\xfa\xed\xfe':
            raise ValueError('Section rewriting requires a thin Mach-O object')
        positions = {}
        offset = 32
        for _ in range(struct.unpack_from('<I', data, 16)[0]):
            cmd, length = struct.unpack_from('<II', data, offset)
            if cmd == 0x19:
                for index in range(struct.unpack_from('<I', data, offset + 64)[0]):
                    position = offset + 72 + index * 80
                    flags = struct.unpack_from('<I', data, position + 64)[0]
                    if flags & 0x02000000:
                        continue
                    name = data[position:position + 16].split(b'\0')[0].decode()
                    segment = data[position + 16:position + 32].split(b'\0')[0].decode()
                    positions.setdefault(name, []).append((position + 16, segment))
            offset += length
        expected = Counter((row['section'], row['segment']) for row in expected_sections)
        present = Counter((name, segment) for name, items in positions.items() for _, segment in items)
        if all(present[key] == count for key, count in expected.items()):
            continue  # Source attributes already emit these labels.
        if {row['segment'] for row in expected_sections} == {'__HIB'}:
            if Counter(row['section'] for row in expected_sections) != Counter(
                    name for name, items in positions.items() for _ in items):
                raise ValueError('XNU HIB section coverage changed: ' + output)
            for items in positions.values():
                for at, _ in items:
                    data[at:at + 16] = b'__HIB'.ljust(16, b'\0')
        else:
            for (name, segment), count in expected.items():
                found = positions.get(name, [])
                matches = [at for at, existing in found if existing == segment]
                if len(matches) == count:
                    continue
                if len(found) != count or len(segment.encode('ascii')) > 16:
                    raise ValueError('Ambiguous XNU section rewrite: ' + output + ': ' + name)
                for at, _ in found:
                    data[at:at + 16] = segment.encode('ascii').ljust(16, b'\0')
        path.write_bytes(data)
        row = built_by_path[str(path.relative_to(out))]
        row.setdefault('compiled_sha256', row['sha256'])
        row['sha256'] = hashlib.sha256(data).hexdigest()
        row['section_labels_rewritten'] = expected_sections
        path.with_suffix(path.suffix + '.source-receipt.json').write_text(json.dumps(row, indent=2) + '\n')
        (out / 'compilation.json').write_text(json.dumps(dict(objects=built, failures=[]), indent=2) + '\n')
    for output, transform in manifest.get('transforms', {}).items():
        values = [sys.executable, *[translate(v) for v in transform['argv'][1:]]]
        subprocess.run(values, cwd=translate(transform['cwd']), check=True, timeout=120)
    for archive in manifest['archives']:
        destination = Path(translate(archive['output'])); destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([args.ar, 'rcs', str(destination), *[translate(p) for p in archive['objects']]], check=True, timeout=120)
    if manifest.get('link_command'):
        filelist = Path(translate(manifest['link_filelist_path'])) if portable else work / 'venus-amfi065-native-003/link.filelist'
        filelist.parent.mkdir(parents=True, exist_ok=True)
        filelist.write_text('\n'.join(translate(p) for p in manifest['link_filelist']) + '\n')
        linked = command(manifest['link_command'])
        link_log = out / ('link-attempt-' + str(len(list(out.glob('link-attempt-*.log'))) + 1).zfill(3) + '.log')
        with link_log.open('xb') as log:
            subprocess.run(linked, cwd=work, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
        for stage in manifest.get('link_postprocess', []):
            subprocess.run([translate(v) for v in stage['argv']], cwd=translate(stage['cwd']), check=True, timeout=120)
    for row in built:
        row['sha256'] = hashlib.sha256((out / row['output']).read_bytes()).hexdigest()
        target = out / row['output']
        target.with_suffix(target.suffix + '.source-receipt.json').write_text(json.dumps(row, indent=2) + '\n')
    built.sort(key=lambda row: row['output'])
    sdk_archives = ['libcc_kext.a', 'libfirehose_kernel.a'] if manifest.get('link_command') and not source_runtime else []
    (out / 'objects.json').write_text(json.dumps(dict(result='compiled-source-closure', objects=built,
        no_existing_native_objects_used=True, external_sdk_archives_used=sdk_archives,
        source_built_sdk_archives=list(source_runtime['libraries']) if source_runtime else [],
        complete_source_link=not sdk_archives and bool(manifest.get('link_command')),
        probe_only=manifest.get('probe_only', False),
        link_performed=bool(manifest.get('link_command')), phone_operations=False), indent=2) + '\n')
    print('Compiled', len(built), 'source units; no previous kernel objects used')


if __name__ == '__main__': main()
