"""Shared-class and exact KDK display-slot checks before graphics prelink."""
from pathlib import Path
import re

DISPLAY_ARGS = (
    'keepsyms=1', 'offline-mobile-graphics-load=1', 'offline-legacy-register=1',
    'offline-legacy-gop=1', 'offline-legacy-unit-scale=2', 'offline-legacy-phase=4',
    'offline-legacy-pm=1', 'offline-legacy-validate=1', 'offline-legacy-transfer=1',
    'offline-legacy-cpu-present=1', 'sheng-vsync=60', 'offline-key-events=1', 'sheng-aks=1',
    'offline-hid-input=1', 'offline-hid-home=1',
)


def qualify_action(extra, native, reference, providers, xnu, generated, report):
    """IIG adds a second, empty non-polymorphic interface to OSAction."""
    V = extra.V
    inputs = (generated, xnu / 'libkern/libkern/c++/OSMetaClass.h', xnu / 'iokit/DriverKit/OSAction.iig')
    contents = [p.read_bytes() for p in inputs]
    code = [re.sub(r'/\*.*?\*/|//[^\n]*', '', data.decode(), flags=re.S) for data in contents]
    declarations = (
        len(re.findall(r'class\s+OSAction\s*:\s*public OSObject\s*,\s*public OSActionInterface\s*\{', code[0])) == 1 and
        len(re.findall(r'class\s+OSActionInterface\s*:\s*public OSInterface\s*\{\s*public:\s*\};', code[0])) == 1 and
        len(re.findall(r'class\s+OSInterface\s*\{\s*\};', code[1])) == 1 and
        len(re.findall(r'class\s+NATIVE\s+KERNEL\s+OSAction\s*:\s*public OSObject\s*\{', code[2])) == 1)
    if not declarations:
        raise ValueError('OSAction generated/empty-interface declaration changed')
    for cls in ('OSActionInterface', 'OSInterface'):
        name = '__ZTV' + str(len(cls)) + cls
        if any(name in image.by_name for image in (native, *providers)):
            raise ValueError('OSAction interface unexpectedly has its own virtual table')
    comparison = V.compare_tables(native.primary_vtable('OSAction', [native]), reference.primary_vtable('OSAction', providers))
    left, right = extra.instance_size_argument(native, 'OSAction'), extra.instance_size_argument(reference, 'OSAction')
    sizes = (left.get('status') == right.get('status') == 'constant_sizeof_argument' and
             left['sizeof_argument'] == right['sizeof_argument'])
    proof = {'sources': [V.F.identity(path, data) for path, data in zip(inputs, contents)],
             'declarations_checked': True, 'empty_interfaces_have_no_vtable': True,
             'instance_size': {'native': left, 'kdk': right},
             'primary_table_matches': comparison['observed_tables_identical'], 'instance_sizes_match': sizes}
    report['empty_interface_primary'] = {'OSAction': proof}
    if not comparison['observed_tables_identical'] or not sizes:
        return
    row = report['classes']['OSAction']
    row.update(status=comparison['classification'],
               source_hierarchy={'status': 'one_polymorphic_base_and_empty_interface',
                                 'class_name': 'OSAction', 'base_clause': 'public OSObject, public OSActionInterface',
                                 'source': proof['sources'][0]},
               instance_size_observation={'native': left, 'kdk': right, 'both_arguments_proven': True, 'equal': True})
    report['comparisons']['OSAction'] = comparison
    previous = report['gate']
    unqualified = set(previous['unqualified_hierarchies']) - {'OSAction'}
    report['gate'] = extra.classify_gate(report['comparisons'], previous['missing_native_providers'],
                                         unqualified, previous['table_failures'])
    report['gate']['instance_size_mismatches'] = previous['instance_size_mismatches']
    report['decode_complete'] = not unqualified and not previous['table_failures']
    report['class_coverage'].update(paired=len(report['comparisons']), unqualified_hierarchy=len(unqualified))
    coverage = report['instance_size_argument_coverage']
    coverage['both_named_arguments_proven'] += 1
    coverage['matching'] += 1
    report['limitations'].append('OSAction is additionally checked against its generated header, empty non-polymorphic interface, exact primary table and equal emitted sizeof arguments.')


def audit(extra, native, reference, storage, index, module_names, xnu, storage_source, display_source, osaction_header=None):
    V = extra.V
    modules = {name: V.Image(Path(index[name]['executable'])) for name in module_names}
    providers = [reference, storage, *modules.values()]
    aliases = {'IOMemoryMap': 'iokit/IOKit/IOMemoryDescriptor.h',
               'IORegistryIterator': 'iokit/IOKit/IORegistryEntry.h',
               'IOPlatformDevice': 'iokit/IOKit/IOPlatformExpert.h',
               'IODTPlatformExpert': 'iokit/IOKit/IOPlatformExpert.h',
               'IOCPUInterruptController': 'iokit/IOKit/IOCPU.h',
               'IOPMrootDomain': 'iokit/IOKit/pwr_mgt/RootDomain.h',
               'IOPerfControlClient': 'iokit/IOKit/perfcontrol/IOPerfControl.h',
               'IOUserClient2022': 'iokit/IOKit/IOUserClient.h',
               'OSSerializer': 'libkern/libkern/c++/OSSerialize.h',
               **{name: 'iokit/IOKit/IOKernelReporters.h' for name in
                  ('IOHistogramReporter', 'IOReportLegend', 'IOReporter', 'IOSimpleReporter', 'IOStateReporter')}}
    extra.STORAGE_HEADERS['IOBlockStorageDevice'] = 'IOBlockStorageDevice.h'
    shared = set()
    for image in modules.values():
        shared.update(cls for cls in V.imported_cpp_classes(image) if '__ZTV' + str(len(cls)) + cls in native.by_name)
    for cls in sorted(shared - extra.KERNEL_HEADERS.keys() - extra.STORAGE_HEADERS.keys()):
        if cls in aliases:
            extra.KERNEL_HEADERS[cls] = aliases[cls]
            continue
        paths = list((xnu / 'iokit/IOKit').rglob(cls + '.h')) + list((xnu / 'libkern/libkern/c++').glob(cls + '.h'))
        if len(paths) == 1:
            extra.KERNEL_HEADERS[cls] = str(paths[0].relative_to(xnu))
    shared_report = extra.audit(native, providers, list(modules.values()), xnu, storage_source, record_sizes=True)
    if 'OSAction' in shared_report['gate']['unqualified_hierarchies']:
        qualify_action(extra, native, reference, providers, xnu,
                       osaction_header or display_source.parent.parent / 'OSAction.generated.h', shared_report)
    gate = shared_report['gate']
    shared_ok = shared_report['decode_complete'] and not any(gate[key] for key in (
        'padding_only', 'beyond_padding', 'unqualified_hierarchies', 'table_failures', 'instance_size_mismatches'))
    family = modules['com.apple.iokit.IOMobileGraphicsFamily']
    surface = modules['com.apple.iokit.IOSurface']
    table = family.primary_vtable('IOMobileFramebufferLegacy', providers)
    source = display_source.read_text()
    constants = {name: int(value) for name, value in re.findall(r'\b(k\w+)\s*=\s*(\d+)', source)}
    overrides = re.findall(r'\{(k\w+),\s*"(__Z[^"]+)"\}', source)
    if len(overrides) != 12 or constants.get('kSlots') != 473:
        raise ValueError('Unexpected display ABI source contract')
    checks = {'vtable_473_slots': table['function_slots'] == 473 and table['trailing_zero_words'] >= 1}
    for key, symbol in overrides:
        slot = constants[key]
        checks[f'slot_{slot}_{key}'] = symbol in table['words'][slot + 2]['names']
    for slot in (317, 319, 352, 353, 419, 420, 452, 453, 460):
        checks[f'pure_{slot}'] = '___cxa_pure_virtual' in table['words'][slot + 2]['names']
    checks['register_service_slot'] = '__ZN9IOService15registerServiceEj' in table['words'][constants['kRegisterService'] + 2]['names']
    bindings = re.findall(r'native_kext_symbol\((kFamily|kSurfaceKext),\s*"([^"]+)"', source)
    for owner, symbol in bindings:
        image = family if owner == 'kFamily' else surface
        checks['symbol_' + symbol] = symbol in image.by_name and symbol not in image.ambiguous_names
    size = extra.instance_size_argument(family, 'IOMobileFramebufferLegacy')
    checks['instance_covers_display_fields'] = size.get('status') == 'constant_sizeof_argument' and size['sizeof_argument'] >= 0x1908
    hid = modules['com.apple.iokit.IOHIDFamily']
    hid_table = hid.primary_vtable('IOHIDDevice', providers)
    hid_source = display_source.with_name('HidInputProbe.cpp').read_text()
    hid_constants = {name: int(value) for name, value in re.findall(r'\b(k\w+)\s*=\s*(\d+)', hid_source)}
    checks['hid_334_slots'] = hid_table['function_slots'] == 334 and hid_table['trailing_zero_words'] >= 1
    for key, symbol in re.findall(r'\{(k\w+|\d+),\s*"(__Z[^"]+)"\}', hid_source):
        slot = int(key) if key.isdecimal() else hid_constants[key]
        checks[f'hid_slot_{slot}'] = symbol in hid_table['words'][slot + 2]['names']
    hid_size = extra.instance_size_argument(hid, 'IOHIDDevice')
    checks['hid_instance_208_bytes'] = hid_size.get('sizeof_argument') == 208
    return {'result': 'passed' if shared_ok and all(checks.values()) else 'failed',
            'checks': checks, 'family': family.identity, 'surface': surface.identity,
            'family_instance_size': size, 'family_vtable': table, 'shared_classes': shared_report,
            'hid_vtable': hid_table, 'hid_instance_size': hid_size,
            'runtime_qualified': False,
            'scope': 'Exact provider symbols, shared primary slots, observed sizes and473-slot backend contract; runtime still required'}
