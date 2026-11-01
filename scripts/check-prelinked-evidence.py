"""Validate saved runtime observations and the exact candidate's ADT/firmware inputs."""
import hashlib
import json
from pathlib import Path
import struct

root = Path('/mnt/g/UniXNU-Port')
device = root / 'ports/UniXNU-venus'
base = root / 'artifacts/venus-guide-linux'
candidate = root / 'artifacts/venus-guide-prelinked'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def need(condition, message):
    if not condition:
        raise SystemExit(message)

reports = {}
for phase, directory, expected in [('bsd', base / 'qemu-bsd-amfi', '_bsd_init'),
                                   ('timer', base / 'qemu-timer', '_rtclock_intr'),
                                   ('apfs', base / 'qemu-apfs', '_native_apfs_probe_checkpoint'),
                                   ('payload_timer', candidate / 'qemu-timer', '_rtclock_intr')]:
    report = json.loads((directory / 'gdb-stop.json').read_text())
    kernel = candidate / 'kernel.macho' if phase == 'payload_timer' else base / 'kernel/kernel.macho'
    need(report['kernel_sha256'] == sha(kernel), phase + ': kernel identity mismatch')
    need(report['stop_symbol'] == expected and not report['bounded_timeout_interrupted'], phase + ': checkpoint not reached')
    need(report['native_4k_mmu_observed'], phase + ': missing native 4K observation')
    need(report['armdt_globals']['_armdt_platform_configured'] == 1, phase + ': platform not configured')
    if phase != 'payload_timer':
        need(report['original_crypto_initialized_observed'], phase + ': original crypto not initialized')
    if phase in ('timer', 'payload_timer'):
        need(report['function_return_stack_matched'], phase + ': did not observe the actual interrupt return')
        cpu = report['armcpu_globals']
        need(cpu['_armcpu_gic_ready'] == 1 and cpu['_armcpu_timer_interrupts'] >= 1 and cpu['_gCPUsRunning'] == 1,
             phase + ': missing GIC/timer/CPU result')
    if phase == 'apfs':
        need(report['native_apfs_globals']['_native_apfs_load_status'] == 0, 'APFS load failed')
    reports[phase] = {'report': str((directory / 'gdb-stop.json').relative_to(root)),
                      'report_sha256': sha(directory / 'gdb-stop.json'), 'kernel_sha256': report['kernel_sha256'],
                      'stop_symbol': expected, 'native_4k': True, 'timeout': False,
                      'cpu': report['armcpu_globals']}
    if phase == 'apfs':
        reports[phase]['apfs'] = report['native_apfs_globals']

blob = (candidate / 'kernel.macho.adt').read_bytes()
nodes = {}
def parse(at, parent):
    count, children = struct.unpack_from('<II', blob, at)
    at += 8
    props = {}
    for _ in range(count):
        name, length = struct.unpack_from('<32sI', blob, at)
        at += 36
        need(length <= len(blob) - at, 'Truncated ADT property')
        props[name.split(b'\0')[0].decode()] = blob[at:at + length]
        at += (length + 3) & ~3
    name = props['name'].rstrip(b'\0').decode()
    path = '/' if parent is None else parent.rstrip('/') + '/' + name
    nodes[path] = props
    for _ in range(children):
        at = parse(at, path)
    return at
need(parse(0, None) == len(blob), 'Unparsed ADT tail')
need(nodes['/chosen']['crypto-hash-method'] == b'sha2-384\0', 'Phone ADT lacks OS crypto hash method')
need(nodes['/chosen']['amfi-only-platform-code'] == struct.pack('<I', 1), 'Phone ADT lacks platform code policy')
need(nodes['/chosen']['osenvironment'] == b'main\0', 'Phone ADT has wrong OS environment')
need(nodes['/cpus/cpu0']['reg'] == struct.pack('<I', 0), 'Unexpected boot CPU')
need(nodes['/cpus/cpu0']['timebase-frequency'] == struct.pack('<I', 19200000), 'Unexpected phone timer frequency')
payload = json.loads((candidate / 'payload.json').read_text())
verify = json.loads((candidate / 'verification.json').read_text())
need(sha(candidate / 'kernel.macho') == payload['payload_kernel_sha256'], 'Extracted payload kernel differs')
need(sha(candidate / 'kernel.macho.adt') == payload['adt_sha256'], 'Extracted payload ADT differs')
need(sha(candidate / 'boot-venus-unixnu.img') == verify['sha256'], 'Boot image hash differs')
need(verify['roundtrip_verified'] and verify['bytes'] <= 201326592, 'Boot container check failed')
build = (candidate / 'build-report.txt').read_text()
for marker in ('DxeCoreAdvancedLoggerLibConstructor', 'AdvancedLogDxe', 'QrEncoderLib', 'PcdAdvancedLoggerPages'):
    need(marker in build, 'Missing compiled logger integration: ' + marker)
result = {'upstream_revision': '16e592abee8a550dec8154ed1f38b5ebc4f16213', 'qemu': reports,
          'candidate': verify, 'payload': payload, 'phone_os_properties_checked': True,
          'advanced_log_efi_sha256': sha(candidate / 'AdvancedLogDxe.efi'),
          'firmware_build_report_sha256': sha(candidate / 'build-report.txt'),
          'logger_phone_tested': False, 'candidate_phone_tested': False,
          'apfs_root_mounted': False, 'ios_userspace_booted': False,
          'limits': ['APFS kext loading succeeded; VFS registration and root mount were not observed.',
                     'QEMU uses its own hardware DT, not phone addresses.',
                     'Logger protocol/QR interaction awaits the first phone run.']}
(device / 'evidence/prelinked-runtime.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS: prelinked BSD/crypto, timer return, APFS load, instrumented payload timer, phone ADT and logger build inputs')
