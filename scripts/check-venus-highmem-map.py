"""Static check of the Venus high-memory addition against the live DT."""
import json
import argparse
from pathlib import Path
import re
import subprocess

root = Path('/mnt/g/UniXNU-Port')
source = root/'ports/uefi-venus/Platforms/Xiaomi/venusPkg/Library/MemoryMapLib/MemoryMapLib.c'
dtb = root/'evidence/venus/20261025T020508Z/live.dtb'
text = source.read_text()
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--six-gib',action='store_true')
args=parser.parse_args()
# Select the actual C preprocessor branch before checking descriptors. Only the
# unavailable firmware include is omitted for this host preprocessing pass.
defines=['-DUNIXNU_VENUS_HIGH_MEMORY']+(['-DUNIXNU_VENUS_6G_MEMORY'] if args.six_gib else [])
text=subprocess.check_output(['gcc','-E','-P','-x','c',*defines,'-'],
    input=text.replace('#include <Library/MemoryMapLib.h>',''),text=True)
regions = []
for match in re.finditer(r'\{"([^"]+)",\s*(0x[0-9A-Fa-f]+),\s*(0x[0-9A-Fa-f]+),', text):
    regions.append((match.group(1), int(match.group(2), 16), int(match.group(3), 16)))
high = [r for r in regions if r[1] >= 0x100000000]
assert len(high) == 1, 'Expected exactly one high-memory region'
name, base, length = high[0]
assert (name, base, length) == ('Kernel RAM G', 0x100000000, 0x180000000 if args.six_gib else 0x100000000), 'Unexpected high region'
# Sort the DT memory banks and reserved-memory ranges.
def fdtget(*args):
    return subprocess.check_output(['fdtget', '-t', 'x', str(dtb), *args], text=True).split()
bank = [int(v, 16) for v in fdtget('/memory', 'reg')]
banks = [(bank[i] << 32 | bank[i+1], bank[i+2] << 32 | bank[i+3]) for i in range(0, len(bank), 4)]
assert any(start <= base and base + length <= start + size for start, size in banks), 'High region is outside DT memory'
reserved = []
for node in subprocess.check_output(['fdtget', '-l', str(dtb), '/reserved-memory'], text=True).split():
    try:
        values = [int(v, 16) for v in fdtget('/reserved-memory/' + node, 'reg')]
    except subprocess.CalledProcessError:
        continue
    for i in range(0, len(values), 4):
        start = values[i] << 32 | values[i+1]
        size = values[i+2] << 32 | values[i+3]
        if size:
            reserved.append((node, start, size))
overlaps = [entry for entry in reserved if entry[1] < base + length and base < entry[1] + entry[2]]
assert not overlaps, 'High region overlaps DT reserved memory: ' + repr(overlaps)
# Check all DT-memory regions >= PcdSystemMemoryBase for overlaps.
system = sorted((r for r in regions if r[1] >= 0x80000000 and r[2]), key=lambda r: r[1])
for previous, current in zip(system, system[1:]):
    assert previous[1] + previous[2] <= current[1], f'Overlap: {previous} and {current}'
conventional = [(n, b, l) for n, b, l in regions if n.startswith('Kernel RAM')]
largest = max(conventional, key=lambda r: r[2])
report = {'source': str(source), 'source_sha256': subprocess.check_output(['sha256sum', str(source)], text=True).split()[0],
          'dtb': str(dtb), 'high_region': {'name': name, 'base': hex(base), 'bytes': length},
          'dt_banks': [{'base': hex(b), 'bytes': l} for b, l in banks],
          'high_reserved_overlaps': overlaps,
          'largest_conventional_before': 'Kernel RAM F 0x13600000',
          'largest_conventional_after': {'name': largest[0], 'base': hex(largest[1]), 'bytes': largest[2]},
          'map_overlaps': False, 'host_qualified': True,'preprocessor_defines':defines,
          'physical_six_gib_handoff_verified':False}
filename='highmem-6g-map-check.json' if args.six_gib else 'highmem-map-check.json'
(root/'ports/UniXNU-venus/evidence'/filename).write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
