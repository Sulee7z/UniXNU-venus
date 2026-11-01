"""Use current upstream QEMU validation with local firmware and register naming."""
import hashlib
import json
import os
import re
from pathlib import Path
import sys

root = Path('/mnt/g/UniXNU-Port')
tree = Path('/root/unixnu-build/venus-guide-out/venus/ipados-17.7.11-21H461/venus/tree')
source = tree / 'scripts/probe-darwinboot-xnu.py'
toolchain = Path(os.environ.get('UNIXNU_TOOLCHAIN', '/root/unixnu-toolchain'))
os.environ.setdefault('UNIXNU_TOOLCHAIN', str(toolchain))
os.environ.setdefault('CLT_PREFIX', str(toolchain / 'CommandLineTools/usr'))
os.environ.setdefault('XCTOOLCHAIN_PREFIX', str(toolchain / 'XcodeDefault.xctoolchain/usr'))
os.environ['PATH'] = os.pathsep.join([str(toolchain / 'CommandLineTools/usr/bin'),
                                    str(toolchain / 'bin'), os.environ.get('PATH', '')])
sys.path.insert(0, str(source.parent))
original = source.read_text()
replacements = {
    "ROOT / 'scripts/qemu-entry/make-dt.py'": "Path('/mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/make-qemu-large-memory-dt.py')",
    "ROOT / 'scripts/qemu-entry/gdb-stop.py'": "Path('/mnt/g/UniXNU-Port/tools/guide-gdb-stop.py')",
    'subprocess.run(gdb_command, check=True)':
        "subprocess.run(gdb_command + ['--firmware', '/root/unixnu-build/qemu-firmware/edk2-aarch64-code.fd'], check=True)",
    "symbols = subprocess.check_output(['xcrun', 'nm', '-U', args.kernel], text=True)":
        "symbols = '\\n'.join(line for line in subprocess.check_output(['xcrun', 'nm', '-U', args.kernel], text=True).splitlines() if line.split()[:2] != ['0000000000000000', 'A'])",
}
code = original
if '--skip-target-hits' in sys.argv:
    index=sys.argv.index('--skip-target-hits')
    if index+1>=len(sys.argv) or not sys.argv[index+1].isdigit():raise SystemExit('Invalid bounded target skip')
    skip=int(sys.argv[index+1])
    if not 0<=skip<=16 or '--finish-function' not in sys.argv:raise SystemExit('Target skip needs a finished function call and at most16 skips')
    key='subprocess.run(gdb_command, check=True)'
    replacements[key]=replacements[key].replace('gdb_command + [',f"gdb_command + ['--skip-target-hits', '{skip}'] + [")
    del sys.argv[index:index+2]
metadata_plan = None
if '--metadata-plan' in sys.argv:
    index = sys.argv.index('--metadata-plan')
    if index + 1 >= len(sys.argv) or '--kernel' not in sys.argv:
        raise SystemExit('--metadata-plan requires a plan and an explicit kernel')
    plan_path = Path(sys.argv[index + 1]).resolve()
    metadata_plan = json.loads(plan_path.read_text())
    kernel_path = Path(sys.argv[sys.argv.index('--kernel') + 1])
    if hashlib.sha256(kernel_path.read_bytes()).hexdigest() != metadata_plan['kernel_sha256']:
        raise SystemExit('Metadata plan is for another kernel')
    requests = metadata_plan['read_memory']
    if not requests or len(requests) > 32:
        raise SystemExit('Metadata read count is not bounded')
    extra = []
    for request in requests:
        if not re.fullmatch(r'[0-9a-fA-F]+:[0-9a-fA-F]+', request):
            raise SystemExit('Invalid metadata range')
        address, size = (int(v, 16) for v in request.split(':'))
        if not 0 < size <= 4096 or not 0xfffffff000000000 <= address < address + size < 1 << 64:
            raise SystemExit('Metadata range is outside bounded kernel memory')
        extra += ['--read-memory', request]
    key = 'subprocess.run(gdb_command, check=True)'
    replacements[key] = replacements[key].replace("gdb_command + [", f"gdb_command + {extra!r} + [")
    del sys.argv[index:index + 2]
fixture_adt = None
packed_data_fixture = '--packed-data-fixture' in sys.argv
if packed_data_fixture:
    if '--data-ramdisk' not in sys.argv:raise SystemExit('Packed Data fixture requires --data-ramdisk')
    sys.argv.remove('--packed-data-fixture')
    replacements['subprocess.run(dt_command, check=True)'] = (
        'subprocess.run(dt_command, check=True)\n'
        'import importlib.util\n'
        '_spec=importlib.util.spec_from_file_location("packed_fixture_adt", "/mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/inject-a660-firmware-adt.py")\n'
        '_codec=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_codec)\n'
        '_adt_path=payloads / "kernel.macho.adt"\n'
        '_tree=_codec.parse(_adt_path.read_bytes())\n'
        '_map=_codec.find(_codec.find(_tree,"chosen"),"memory-map")\n'
        'assert sum(k=="RAMDisk" for k,v in _map.props)==1\n'
        '_map.props=[("PackedRAMDisk" if k=="RAMDisk" else k,v) for k,v in _map.props]\n'
        '_adt_path.write_bytes(_codec.dump(_tree))')
if '--fixture-adt' in sys.argv:
    if packed_data_fixture:raise SystemExit('Select one explicit ADT fixture')
    index = sys.argv.index('--fixture-adt')
    if index + 1 >= len(sys.argv):
        raise SystemExit('--fixture-adt requires a QEMU hardware ADT path')
    fixture_adt = Path(sys.argv[index + 1]).resolve()
    if not fixture_adt.is_file():
        raise SystemExit('QEMU fixture ADT is missing')
    del sys.argv[index:index + 2]
    replacements['subprocess.run(dt_command, check=True)'] = (
        'subprocess.run(dt_command, check=True)\n'
        f'shutil.copyfile({str(fixture_adt)!r}, payloads / "kernel.macho.adt")')
for before, after in replacements.items():
    if code.count(before) != 1:
        raise SystemExit('Upstream observer layout changed: ' + before)
    code = code.replace(before, after)
record = root / 'ports/UniXNU-venus/evidence/qemu-observer.json'
record.write_text(json.dumps({'upstream_revision': '16e592abee8a550dec8154ed1f38b5ebc4f16213',
    'observer_sha256': hashlib.sha256(original.encode()).hexdigest(),
    'gdb_observer_sha256': hashlib.sha256((tree / 'scripts/qemu-entry/gdb-stop.py').read_bytes()).hexdigest(),
    'fixture_adt': str(fixture_adt) if fixture_adt else None,
    'packed_data_fixture': packed_data_fixture,
    'metadata_plan': metadata_plan,
    'host_replacements': replacements, 'guest_code_modified': False}, indent=2) + '\n')
exec(compile(code, str(source), 'exec'), {'__name__': '__main__', '__file__': str(source)})
