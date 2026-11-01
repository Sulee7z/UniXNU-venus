"""Match the phone's fault opcode and verify source-built virtual-only timer code."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

root = Path('/mnt/g/UniXNU-Port')
sys.path.insert(0, str(root / 'sources/UniXNU-guide/kits/XnuPrelink'))
from native_prelink import macho

def need(condition, message):
    if not condition:
        raise SystemExit(message)

def inspect(path):
    data = path.read_bytes()
    table = sorted((int(p[0], 16), p[2]) for line in subprocess.check_output(
        ['llvm-nm', '-n', path], text=True).splitlines() if len(p := line.split()) == 3)
    start = next(address for address, name in table if name == '_fiq_context_init')
    end = next(address for address, _ in table if address > start)
    segment = next(s for s in macho(data)['segments'] if s['va'] <= start and end <= s['va'] + s['filesize'])
    at = segment['fileoff'] + start - segment['va']
    code = data[at:at + end - start]
    words = list(struct.unpack('<' + 'I' * (len(code) // 4), code))
    return {'kernel_sha256': hashlib.sha256(data).hexdigest(), 'function_start': hex(start),
            'function_bytes': code.hex(),
            'physical_timer_writes': [hex(start + i * 4) for i, word in enumerate(words) if word & 0xffffffe0 == 0xd51be220],
            'virtual_timer_writes': [hex(start + i * 4) for i, word in enumerate(words) if word & 0xffffffe0 == 0xd51be320]}

old = inspect(root / 'artifacts/venus-guide-prelinked/kernel.macho')
out = root / 'artifacts/venus-guide-virtual-timer'
new = inspect(out / 'kernel/kernel.macho')
payload = inspect(out / 'phone/kernel.macho')
need(old['physical_timer_writes'] == ['0xfffffff00741a378'], 'Old binary does not match the photographed fault')
for item in (new, payload):
    need(not item['physical_timer_writes'] and len(item['virtual_timer_writes']) == 1,
         'Expected the source fix to preserve CNTV and remove CNTP')
for name, kernel in [('qemu-timer', new), ('phone/qemu-timer', payload)]:
    report = json.loads((out / name / 'gdb-stop.json').read_text())
    need(report['kernel_sha256'] == kernel['kernel_sha256'], 'Wrong kernel in runtime evidence')
    need(report['stop_symbol'] == '_rtclock_intr' and report['function_return_stack_matched'] and
         not report['bounded_timeout_interrupted'], 'Actual timer-interrupt return was not observed')
    need(report['armcpu_globals']['_armcpu_gic_ready'] == 1 and
         report['armcpu_globals']['_armcpu_timer_interrupts'] >= 1, 'Missing GIC/timer result')
    if name == 'qemu-timer':
        need(report['original_crypto_initialized_observed'], 'Original crypto initialization missing')
verify = json.loads((out / 'phone/verification.json').read_text())
need(hashlib.sha256((out / 'phone/boot-venus-unixnu.img').read_bytes()).hexdigest() == verify['sha256'],
     'Candidate identity differs from verification')
patch = root / 'ports/UniXNU-sm8350-common/patches/xnu/sm8350-virtual-timer-only.patch'
result = {'upstream_revision': '16e592abee8a550dec8154ed1f38b5ebc4f16213',
          'photo': 'G:/a217923c0c9828c9afd5ef414e0eef34.jpg', 'fault_opcode': '0xd51be228',
          'old': old, 'source_rebuilt': new, 'payload': payload,
          'soc_patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
          'qemu_timer_returns_verified': True, 'new_phone_tested': False, 'candidate': verify}
(root / 'ports/UniXNU-venus/evidence/virtual-timer-fix.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'old_fault': old['physical_timer_writes'], 'new_physical_writes': new['physical_timer_writes'],
                  'new_virtual_writes': new['virtual_timer_writes'], 'qemu_timer_returns_verified': True,
                  'boot_sha256': verify['sha256'], 'boot_bytes': verify['bytes']}, indent=2))
