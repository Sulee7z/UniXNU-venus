#!/usr/bin/env python3
"""Audit and emit the066 KDK provider closure from a newly source-built kernel."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

# The size-argument and authenticated-pointer gates use this decoder. Require
# it before opening an output directory rather than reporting a false ABI gap.
import capstone

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
BASE_ROOTS = ['com.apple.filesystems.apfs', 'com.apple.driver.AppleMobileFileIntegrity',
              'com.apple.AppleFSCompression.AppleFSCompressionTypeZlib']
SANDBOX = 'com.apple.security.sandbox'
DISPLAY_ROOTS = ['com.apple.iokit.IOSurface', 'com.apple.iokit.IOMobileGraphicsFamily', 'com.apple.iokit.IOHIDFamily']

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('native', 'hmac-seal', 'extensions', 'reference', 'xnu-source', 'storage-source',
                 'crypto-source', 'display-source', 'hid-source', 'osaction-header', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        parser.error('Fresh prelink output required')
    for name, digest in json.loads((ROOT / 'sources.lock.json').read_text())['files'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Source emitter input changed: ' + name)
    out.mkdir(parents=True)
    def save(name, value):
        (out / name).write_text(json.dumps(value, indent=2) + '\n')
    summary = dict(result='running', prelinked=False, emitter_gates_passed=False,
                   runtime_compatible=False, phone_operations=False)
    try:
        xnu = out / 'sources/xnu'
        storage_source = out / 'sources/storage'
        shutil.copytree(args.xnu_source, xnu)
        shutil.copytree(args.storage_source, storage_source)
        display_source = out / 'sources/display/NativeLegacyDisplay.cpp'
        display_source.parent.mkdir(parents=True)
        shutil.copyfile(args.display_source, display_source)
        shutil.copyfile(args.hid_source, display_source.with_name('HidInputProbe.cpp'))
        # These source metadata files were not compiler inputs but are required
        # for genuine OSKext interfaces and the OSAction ABI check.
        for source, destination in ((ROOT / 'sources/xnu', xnu), (ROOT / 'sources/storage', storage_source)):
            for path in source.rglob('*'):
                if path.is_file():
                    target = destination / path.relative_to(source)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
        H = load('post_hmac', 'audit-zeta-plain-fips-hmac.py')
        hmac = H.audit(args.native, args.hmac_seal)
        save('hmac.json', hmac)
        if not hmac['hmac_field']['matches_expected_post_startup_text'] or not hmac['stored_matches_build_seal']:
            raise ValueError('Source POST HMAC audit failed')
        C = load('provider_closure', 'audit-zeta-apfs-closure.py')
        closure = C.audit(args.native, args.extensions, BASE_ROOTS + [SANDBOX] + DISPLAY_ROOTS)
        save('closure.json', closure)
        if not closure['decode_complete'] or not closure['binding']['static_binding_complete']:
            raise ValueError('Genuine KDK executable closure is incomplete')
        V = C.V
        native = V.Image(args.native)
        reference = V.Image(args.reference)
        index = C.index_bundles(args.extensions)
        storage = V.Image(Path(index['com.apple.iokit.IOStorageFamily']['executable']))
        importers = [V.Image(Path(index[name]['executable'])) for name in BASE_ROOTS]
        comparisons = {cls: V.compare_tables(native.primary_vtable(cls, [native]),
            (reference if cls in ('OSObject', 'IOService') else storage).primary_vtable(cls, [reference, storage]))
            for cls in V.CLASSES}
        primary = dict(inputs={'native': native.identity, 'kdk_kernel': reference.identity},
            decode_complete=True, comparisons=comparisons,
            gate='identical_observed_slots' if all(r['observed_tables_identical'] for r in comparisons.values())
                 else 'known_structural_incompatibility')
        save('vtables.json', primary)
        E = load('all_shared_tables', 'audit-zeta-apfs-extra-vtables.py')
        E.KERNEL_HEADERS.update(IORegistryIterator='iokit/IOKit/IORegistryEntry.h',
                                OSCollectionIterator='libkern/libkern/c++/OSCollectionIterator.h')
        E.STORAGE_HEADERS.update(IOBlockStorageDevice='IOBlockStorageDevice.h', IOGUIDPartitionScheme='IOGUIDPartitionScheme.h')
        providers = [reference, storage] + [V.Image(Path(index[name]['executable'])) for name in
            ('com.apple.driver.AppleEffaceableStorage', 'com.apple.iokit.CoreAnalyticsFamily')]
        extra = E.audit(native, providers, importers, xnu, storage_source, record_sizes=True)
        save('extra-vtables.json', extra)
        sandbox = E.audit(native, providers, [V.Image(Path(index[SANDBOX]['executable']))],
                          xnu, storage_source, record_sizes=True)
        save('sandbox-vtables.json', sandbox)
        unsafe = ('padding_only', 'beyond_padding', 'unqualified_hierarchies', 'table_failures', 'instance_size_mismatches')
        if not sandbox['decode_complete'] or any(sandbox['gate'][k] for k in unsafe):
            raise ValueError('Sandbox ABI evidence is incomplete or incompatible')
        D = load('graphics_abi', 'venus_display_abi.py')
        display = D.audit(E, native, reference, storage, index, closure['actual_kdk_executables'],
                          xnu, storage_source, display_source, args.osaction_header)
        save('display-abi.json', display)
        if display['result'] != 'passed':
            raise ValueError('Real graphics/HID ABI gates failed')
        emit = load('source_emitter', 'emit-zeta-apfs-prelink.py')
        original = emit.A.MachO(args.native.read_bytes(), args.native)
        modules = {}
        metadata_index = {}
        for name in closure['actual_kdk_executables']:
            row = index[name]
            sliced = V.Image(Path(row['executable']))
            modules[name] = emit.A.MachO(sliced.data, row['executable'], candidate=True)
            metadata_index[name] = dict(plist_path=Path(row['metadata']['path']))
        emit.gate(original, modules, closure, primary, extra)
        W = load('owned_window_alignment', 'venus_owned_window.py')
        previous = emit.L.plan
        emit.L.plan = lambda kernel, providers, info_bytes=None: W.align_layout(previous(kernel, providers, info_bytes), kernel)
        try:
            data, report = emit.emit(original, modules, metadata_index, closure, primary, extra,
                                     xnu, storage_source, args.crypto_source)
        finally:
            emit.L.plan = previous
        data = W.preserve_header_scan(data, report['layout'])
        report['output_sha256'] = hashlib.sha256(data).hexdigest()
        (out / 'kernel.macho').write_bytes(data)
        save('prelink-report.json', report)
        summary.update(json.loads((ROOT / 'binding-plans.json').read_text()))
        summary.update(result='passed', prelinked=True, emitter_gates_passed=True,
            prelinked_sha256=hashlib.sha256(data).hexdigest(), native_sha256=hashlib.sha256(args.native.read_bytes()).hexdigest())
    except Exception as error:
        summary.update(result='failed', error=str(error))
        raise
    finally:
        save('summary.json', summary)
    print(json.dumps({k: summary[k] for k in ('result', 'prelinked_sha256', 'runtime_compatible')}, indent=2))

if __name__ == '__main__':
    main()
