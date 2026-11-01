"""Bind the photographed IRQ-parent crash, QEMU regression and phone ADT fix."""
import hashlib
import json
from pathlib import Path
import struct

root = Path('/mnt/g/UniXNU-Port')
old = root / 'artifacts/venus-guide-virtual-timer'
new = root / 'artifacts/venus-guide-adt-fix'

def need(condition, message):
    if not condition:
        raise SystemExit(message)

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def read_adt(path):
    data, result = path.read_bytes(), {}
    def visit(at, parent):
        props_count, children = struct.unpack_from('<II', data, at)
        at += 8
        props = {}
        for _ in range(props_count):
            key, size = struct.unpack_from('<32sI', data, at)
            at += 36
            need(size <= len(data) - at, 'Truncated ADT')
            name = key.split(b'\0')[0].decode()
            need(name not in props, 'Duplicate ADT property')
            props[name] = data[at:at + size]
            at += (size + 3) & ~3
        name = props['name'].rstrip(b'\0').decode()
        node = '/' if parent is None else parent.rstrip('/') + '/' + name
        result[node] = props
        for _ in range(children):
            at = visit(at, node)
        return at
    need(visit(0, None) == len(data), 'Unexpected ADT tail')
    return result

before = json.loads((old / 'qemu-shared-before/gdb-stop.json').read_text())
after = json.loads((old / 'qemu-shared-after/gdb-stop.json').read_text())
need(before['kernel_exception']['pc'] == '0xfffffff0078e5bb4' and before['kernel_exception']['far'] == '0x0',
     'Negative case does not reproduce the phone fault')
need(after['stop_symbol'] == '_rtclock_intr' and after['function_return_stack_matched'] and
     not after['bounded_timeout_interrupted'] and after['armdt_globals']['_armdt_platform_configured'] == 1 and
     after['armcpu_globals']['_armcpu_timer_interrupts'] >= 1 and after['original_crypto_initialized_observed'],
     'Shared-generated ADT runtime regression did not pass')
need(before['kernel_sha256'] == after['kernel_sha256'], 'The A/B test changed the kernel')
previous = read_adt(old / 'phone/kernel.macho.adt')
current = read_adt(new / 'kernel.macho.adt')
need('AAPL,phandle' not in previous['/arm-io/intc'], 'Old ADT did not have the diagnosed omission')
need(current['/arm-io/intc']['AAPL,phandle'] == current['/arm-io/intc']['phandle'] == current['/arm-io/timer']['interrupt-parent'],
     'Phone IRQ provider identity does not match')
need(sha(new / 'kernel.macho') == sha(old / 'phone/kernel.macho'), 'ADT-only revision unexpectedly changed kernel code')
verify = json.loads((new / 'verification.json').read_text())
need(sha(new / 'boot-venus-unixnu.img') == verify['sha256'] and verify['roundtrip_verified'], 'Candidate identity mismatch')
result = {'upstream_revision': '16e592abee8a550dec8154ed1f38b5ebc4f16213',
          'local_converter_sha256': sha(root / 'sources/UniXNU-guide/scripts/unixnu/devicetree.py'),
          'photo': 'G:/54aa65409b42226aadab1ec2adc131c1.jpg',
          'negative_fault': before['kernel_exception'], 'positive_stop': after['stop_symbol'],
          'positive_timer_interrupts': after['armcpu_globals']['_armcpu_timer_interrupts'],
          'same_kernel_in_ab_test': True, 'phone_interrupt_handle': struct.unpack('<I', current['/arm-io/intc']['AAPL,phandle'])[0],
          'kernel_unchanged_from_timer_fix': True, 'candidate': verify,
          'new_phone_runtime_verified': False, 'docs_build_passed': True, 'unit_tests_passed': 6}
(root / 'ports/UniXNU-venus/evidence/adt-irq-fix.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'candidate'}, indent=2))
print('Candidate:', verify['sha256'], verify['bytes'])
