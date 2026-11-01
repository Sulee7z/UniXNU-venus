"""Check the exact parser against retained phone GPT and audit the linked SMMU store."""
import hashlib
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--suffix', choices=('', '-banks', '-init'), default='')
args = parser.parse_args()
root = Path('/mnt/g/UniXNU-Port')
device = root / 'ports/UniXNU-venus'
artifact = root / ('artifacts/venus-ufs-read' + args.suffix)
snapshot = root / 'evidence/venus/dual-readonly-20261025T161421Z'
prior = json.loads((device / 'evidence/dual-readonly.json').read_text())
for name in ('gpt-primary.bin', 'gpt-backup.bin'):
    if hashlib.sha256((snapshot / name).read_bytes()).hexdigest() != prior['files'][name]:
        raise SystemExit('Retained GPT differs: ' + name)
receipt = json.loads((root / 'artifacts/venus-ufs-read-unixnu/venus-build.json').read_text())
header = device / 'package/VenusUfsGptRead.h'
if hashlib.sha256(header.read_bytes()).hexdigest() != receipt['device_inputs']['package/VenusUfsGptRead.h']:
    raise SystemExit('Parser differs from the compiled archive')
binary = artifact / 'known-gpt-test'
subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                '-I', device / 'package', device / 'tests/ufs_read_fixture.cpp', '-o', binary], check=True)
last = prior['disk_bytes'] // prior['logical_block_bytes'] - 1
test = subprocess.check_output([binary, snapshot / 'gpt-primary.bin', snapshot / 'gpt-backup.bin', str(last)], text=True)
assembly = subprocess.check_output(['llvm-objdump', '-d', '--disassemble-symbols=__ZL14venusSmmuWritemj',
                                    artifact / 'kernel/kernel.macho'], text=True)
opcodes = re.findall(r'^\s*[0-9a-f]+:\s+([0-9a-f]{8})\s', assembly, re.M)
if opcodes != ['d5033f9f', 'b9000001', 'd5033f9f', 'd65f03c0']:
    raise SystemExit('Linked SMMU store changed; inspect its source register and barriers')
primary = (snapshot / 'gpt-primary.bin').read_bytes()[4096:8192]
backup = (snapshot / 'gpt-backup.bin').read_bytes()[-4096:]
record = {'source_snapshot': str(snapshot), 'source_files': prior['files'],
          'kernel_sha256': hashlib.sha256((artifact / 'kernel/kernel.macho').read_bytes()).hexdigest(),
          'block_bytes': 4096, 'last_lba': last, 'disk_bytes': prior['disk_bytes'],
          'primary_header_sha256': hashlib.sha256(primary).hexdigest(),
          'primary_header_crc': hex(struct.unpack_from('<I', primary, 16)[0]),
          'backup_header_crc': hex(struct.unpack_from('<I', backup, 16)[0]),
          'entries_crc': hex(struct.unpack_from('<I', primary, 88)[0]),
          'parser_fixture_result': test.strip(), 'linked_smmu_write_assembly': assembly.strip(),
          'phone_block_read_verified': False}
(device / ('evidence/ufs-read' + args.suffix + '-reference.json')).write_text(json.dumps(record, indent=2) + '\n')
print(test, end='')
print(json.dumps(record, indent=2))
