#!/usr/bin/env python3
"""Add passive UFS startup/failure evidence to the official copied-kernel panic screen."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import os

BASE = Path(os.environ['UNIXNU_SOURCE_BASE']).resolve()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def instrument_source(source, addresses):
    """No new MMIO, controller commands, locks or allocation in the panic path."""
    block = r'''
  /* Venus: software counters remain useful even if NativeUfs never started.
   * Values are adjacent cached updates, not an atomic hardware snapshot. */
  {
    const char *reason = *(const char *volatile *)@FAILURE@UL;
    u64 status[] = {
      *(volatile const u32 *)@PROBES@UL,
      *(volatile const u32 *)@MATCHED@UL,
      *(volatile const u32 *)@STEP@UL,
      *(volatile const u32 *)@PUBLISHED@UL,
      (u64)(reason ? reason : "none")
    };
    format (&g, "\nUFS probe=%u match=%u step=%u pub=%u\nwhy=%.120s\n", status);
  }
'''
    for name, address in addresses.items():
        block = block.replace('@' + name + '@', hex(address))
    if '@' in block:
        raise ValueError('Unresolved diagnostic address')
    marker = '  format (&g, fmt, args);'
    if source.count(marker) != 1:
        raise ValueError('Official panic renderer anchor changed')
    # The entry-page cave is bounded. This storage-focused screen spends the
    # former free/total-page footer space on UFS evidence and keeps backtraces.
    for line in ('  hex (&g, "\\npages=", *(volatile const u32 *)PAGE_TOTAL);',
                 '  hex (&g, "\\nfree=", *(volatile const u32 *)PAGE_FREE);'):
        if source.count(line) != 1:
            raise ValueError('Official VM footer anchor changed')
        source = source.replace(line, '', 1)
    return source.replace(marker, marker + '\n' + block, 1)


def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: patch-venus-root-panic.py KERNEL --panic-screen --no-reset [--usb-panic]')
    usb = '--usb-panic' in sys.argv
    if usb:
        sys.argv.remove('--usb-panic')
    compact = '--compact-no-reset-caves' in sys.argv
    if compact:
        sys.argv.remove('--compact-no-reset-caves')
    relocate = '--relocate-native-entry-caves' in sys.argv
    if relocate:
        sys.argv.remove('--relocate-native-entry-caves')
    kernel = Path(sys.argv[1]).resolve(strict=True)
    if '--no-reset' not in sys.argv or '--panic-screen' not in sys.argv:
        raise ValueError('Workspace copied kernel and non-resetting panic screen required')
    receipt = kernel.with_suffix('.macho.venus-panic.json')
    generated = kernel.with_suffix('.macho.venus-panic.c')
    if receipt.exists() or generated.exists():
        raise ValueError('Do not overwrite an existing diagnostic')
    upstream = BASE / 'scripts/patch-xnu-entry-probe.py'
    spec = importlib.util.spec_from_file_location('venus_official_entry_probe', upstream)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    if compact:
        # Keep both stage entry addresses. Each actual stage must fit the new
        # 80-byte extent (upstream checks this); reclaim 16 trailing zero bytes
        # from stage2 for the renderer without extending the entry-page cave.
        probe.CAVE_SIZE = 0x50
    original_assemble = probe.assemble_c
    original_common = probe.panic_common_entry
    original_rebase = probe.rebase
    screen_entries = {}
    report = {'input_sha256': sha(kernel), 'upstream_patcher_sha256': sha(upstream),
              'wrapper_sha256': sha(Path(__file__)), 'phone_operations': False,
              'hardware_access_added': False, 'runtime_qualified': False,
               'vm_page_footer_replaced_with_ufs': True}
    if compact:
        report['compact_no_reset_caves'] = {'original_stage_capacity': 0x60,
                                           'stage_capacity': 0x50, 'entry_addresses_unchanged': True,
                                           'panic_cave_end_unchanged': True}

    def rebase(path, data):
        names = original_rebase(path, data)
        if relocate:
            # Source reset code can grow before __start. Its padding ends at
            # the real4K page boundary, not at old_END + entry-PC delta.
            # Upstream verifies the entry preimage, every requested cave and
            # the entire renderer range are still zero before any write.
            first = (probe.ENTRY_VA + 4 + 15) & ~15
            probe.CAVES = {stage: first + (stage - 1) * probe.CAVE_SIZE for stage in range(1, 5)}
            probe.PANIC_CAVE_END = (probe.ENTRY_VA & ~4095) + 0xff0
            report['native_entry_caves'] = dict(entry_pc=hex(probe.ENTRY_VA), first=hex(first),
                capacity=probe.CAVE_SIZE, page_padding_end=hex(probe.PANIC_CAVE_END),
                real_page_boundary=True, empty_range_guards_retained=True)
            if compact:
                report['compact_no_reset_caves']['entry_addresses_unchanged'] = False
                report['compact_no_reset_caves']['panic_cave_end_unchanged'] = False
        return names

    def assemble(source, va, workdir, symbols):
        required = {'PROBES': ('_native_ufs_probe_calls', 4),
                    'MATCHED': ('_native_ufs_matched', 4),
                    'STEP': ('_native_ufs_root_step', 4),
                    'PUBLISHED': ('_native_ufs_blocks_published', 4),
                    'FAILURE': ('_native_ufs_root_failure', 8)}
        addresses = {}
        for name, (symbol, width) in required.items():
            address = symbols.get(symbol)
            if address is None or address % width or not any(
                    base <= address and address + width <= base + size
                    for base, size, _, _ in probe.SEGMENTS):
                raise ValueError('Missing or invalid UFS diagnostic symbol: ' + symbol)
            addresses[name] = address
        text = instrument_source(source.read_text(), addresses)
        with generated.open('x') as stream:
            stream.write(text)
        result = original_assemble(generated, va, workdir, symbols)
        report.update(symbols={name: hex(value) for name, value in addresses.items()},
                      upstream_renderer_sha256=sha(source), renderer_sha256=sha(generated),
                      renderer_load=hex(result[1]), renderer_bytes=len(result[0]),
                      renderer_machine_code_sha256=hashlib.sha256(result[0]).hexdigest())
        screen_entries['direct'] = result[2]
        return result

    def common_entry(workdir, code, load):
        result = original_common(workdir, code, load)
        screen_entries['common'] = result
        return result

    probe.assemble_c = assemble
    probe.panic_common_entry = common_entry
    probe.rebase = rebase
    probe.main()
    if 'symbols' not in report:
        raise ValueError('Panic renderer was not assembled')
    if usb:
        data = bytearray(kernel.read_bytes())
        names = {name: address for address, name in probe.kernel_symbols(kernel).items()}
        required = ('_panic', '_panic_trap_to_debugger', '_venus_panic_usb_direct',
                    '_venus_panic_usb_common', '_venus_panic_usb_main', '_venus_panic_usb_screen_common')
        if any(name not in names for name in required):
            raise ValueError('USB panic object is missing from the linked kernel')
        wiring = {}
        for kind, entry in (('direct', '_panic'), ('common', '_panic_trap_to_debugger')):
            site, target = names[entry], names['_venus_panic_usb_' + kind]
            at = probe.file_offset(site)
            expected = probe.branch(site, screen_entries[kind])
            if struct.unpack_from('<I', data, at)[0] != expected:
                raise ValueError('Ordinary screen branch differs: ' + entry)
            # Darwin variadics use stack arguments; the common funnel takes va_list*.
            wrapper = probe.file_offset(target)
            first = 0x910003e1 if kind == 'direct' else 0xf9400021
            if struct.unpack_from('<II', data, wrapper) != (
                    first, probe.branch(target + 4, names['_venus_panic_usb_main'])):
                raise ValueError('USB panic argument ABI differs: ' + kind)
            struct.pack_into('<I', data, at, probe.branch(site, target))
            wiring[kind] = {'site': hex(site), 'usb': hex(target), 'screen': hex(screen_entries[kind])}
        at = probe.file_offset(names['_venus_panic_usb_screen_common'])
        if struct.unpack_from('<Q', data, at)[0] != 0x5650555342434f4d:
            raise ValueError('USB panic screen placeholder is not pristine')
        struct.pack_into('<Q', data, at, screen_entries['common'])
        kernel.write_bytes(data)
        report['usb_panic'] = {'wiring': wiring, 'screen_pointer': hex(names['_venus_panic_usb_screen_common']),
                               'screen_target': hex(screen_entries['common']), 'runtime_qualified': False}
    report['instrumented_before_seal_sha256'] = sha(kernel)
    with receipt.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
