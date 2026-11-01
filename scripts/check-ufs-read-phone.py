"""Compare the transcribed successful phone report with independently retained GPT."""
import hashlib
import json
from pathlib import Path

root = Path('/mnt/g/UniXNU-Port')
device = root / 'ports/UniXNU-venus'
def load(name):
    return json.loads((device / 'evidence' / name).read_text())
def need(value, message):
    if not value:
        raise SystemExit(message)
report = load('ufs-read-init-phone.json')
reference = load('ufs-read-init-reference.json')
candidate = load('ufs-read-init-candidate.json')
def number(name):
    value = report[name]
    return int(value, 0) if isinstance(value, str) else value
need(report['image_sha256'] == candidate['candidate']['sha256'], 'Wrong tested image identity')
need(reference['kernel_sha256'] == candidate['payload']['kernel_sha256'], 'Reference belongs to another kernel')
need(report['result'] == 'VENUS UFS BLOCK READ OK' and report['lun'] == 0, 'No successful LUN0 report')
need(number('block_bytes') == reference['block_bytes'] and number('last_lba') == reference['last_lba'], 'Capacity geometry differs')
need(number('disk_bytes') == reference['disk_bytes'] == (number('last_lba') + 1) * number('block_bytes'), 'Capacity byte count differs')
for key in ('primary_header_crc', 'backup_header_crc', 'entries_crc'):
    need(number(key) == int(reference[key], 0), 'GPT checksum differs: ' + key)
need(report['primary_header_sha256'] == reference['primary_header_sha256'], 'Known primary-header SHA256 differs')
need(report['entries'] == 64 and report['used_entries'] == 34 and report['gpt_reads'] == 5 and report['commands'] == 9,
     'Unexpected completed command/GPT counts')
need(number('sid') == 0xe0 and not (number('s2cr') & ~255) and number('s2cr') == 74 and
     number('cbar') == 0x10000 and report['cba2r'] == 1, 'Unexpected configured UFS route')
need(number('dma') == number('new_transfer_list') and number('dma_extent') == 0x22000 and not (number('dma') & 4095),
     'DMA/list extent differs')
need(number('dma') not in (number('old_transfer_list'), number('old_task_list')), 'Expected private replacement list')
for key in ('final_transfer_run', 'final_task_run', 'final_transfer_doorbell', 'final_task_doorbell', 'gfsr'):
    need(number(key) == 0, 'Unexpected final queue/fault state: ' + key)
photo = root.parent / '20261026_153025.JPG'
result = {'photo_sha256': hashlib.sha256(photo.read_bytes()).hexdigest(),
          'report': report, 'reference': reference,
          'image_sha256': report['image_sha256'], 'capacity_and_known_block_match': True,
          'native_dma_block_read_device_verified': True, 'root_mount_verified': False,
          'evidence_type': 'User photo transcription compared with preexisting Android raw-block hashes/CRCs'}
(device / 'evidence/ufs-read-device-verified.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS: phone capacity, primary/backup CRCs and primary-header SHA256 match retained Android blocks')
print('Commands:', report['commands'], 'GPT reads:', report['gpt_reads'], 'bytes:', number('disk_bytes'))
