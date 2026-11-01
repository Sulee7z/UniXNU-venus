"""Verify the isolated survey kernel, linked archive, payload and host controls."""
import hashlib
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--block-read', action='store_true')
parser.add_argument('--suffix', choices=('', '-banks', '-init'), default='')
args = parser.parse_args()
root = Path('/mnt/g/UniXNU-Port')
device = root / 'ports/UniXNU-venus'
base_stem = 'ufs-read' if args.block_read else 'ufs-survey'
stem = base_stem + args.suffix
config = 'venus_ufs_read' if args.block_read else 'venus_ufs'
artifacts = root / ('artifacts/venus-' + stem)
target = Path('/root/unixnu-build/venus-guide-out/venus/ipados-17.7.11-21H461') / config
compiled_source = target.parent / ('venus/tree/build/venus-' + base_stem + '-unixnu/source')
def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
def load(path):
    return json.loads(path.read_text())
def need(value, message):
    if not value:
        raise SystemExit(message)

archive = load(target / 'tree/build/sheng-ufs/venus-build.json')
need(bool(archive['readonly_survey']) == (not args.block_read) and
     bool(archive.get('block_read_probe')) == args.block_read and not archive['unresolved_kernel_imports'], 'Wrong linked UFS archive mode')
if args.block_read:
    need(len(archive['host_tests']) == 5, 'Missing block-read tests')
    for name, digest in archive['device_inputs'].items():
        need(sha(device / name) == digest, 'Source changed after compilation: ' + name)
need(sha(target / 'tree/build/sheng-ufs/libShengUfs.a') == archive['archive_sha256'], 'Linked archive input differs')
need(sha(compiled_source / 'NativeUfs.cpp') == archive['native_ufs_source_sha256'], 'Compiled UFS source differs')
need(sha(compiled_source / 'VenusUfsSurvey.h') == sha(device / 'package/VenusUfsSurvey.h'), 'Survey header changed after compilation')
status = load(artifacts / 'status.json')
need(status['configuration'] == config + '_defconfig', 'Wrong kernel configuration')
payload = load(artifacts / 'phone/payload.json')
verify = load(artifacts / 'phone/verification.json')
need(sha(artifacts / 'kernel/kernel.macho') == payload['kernel_sha256'], 'Source kernel identity mismatch')
need(sha(artifacts / 'phone/kernel.macho') == payload['payload_kernel_sha256'], 'Extracted kernel identity mismatch')
need(sha(artifacts / 'phone/kernel.macho.adt') == payload['adt_sha256'], 'Extracted ADT identity mismatch')
need(sha(artifacts / 'phone/boot-venus-unixnu.img') == verify['sha256'] and verify['roundtrip_verified'], 'Boot container identity mismatch')
words = payload['kernel_args'].split()
need(words.count('native-ufs-probe=' + ('3' if args.block_read else '2')) == 1 and words.count('native-ufs-root=0') == 1, 'Unexpected survey arguments')
need(not any(w.startswith(('sheng-data-persist=', 'sheng-log=')) for w in words), 'Unexpected storage-write arguments')
controls = load(device / ('evidence/' + stem + '-controls.json'))
need(controls['kernel_sha256'] == payload['kernel_sha256'], 'Controls used a different kernel')
off = load(artifacts / 'phone/qemu-off/gdb-stop.json')
need(off['kernel_sha256'] == payload['payload_kernel_sha256'] and not off['bounded_timeout_interrupted'] and
     off['stop_symbol'] == '_IOFindBSDRoot' and off['native_ufs']['mapped'] == 0, 'Instrumented default-off regression failed')
layout = load(artifacts / 'phone/layout-check.json')
need(layout['memory_conflicts'] == 0 and layout['reserved_ranges_covered'] == 21, 'Firmware layout changed unexpectedly')
record = {'upstream_revision': '16e592abee8a550dec8154ed1f38b5ebc4f16213', 'configuration': config + '_defconfig',
          'archive': archive, 'header_sha256': sha(device / 'package/VenusUfsSurvey.h'),
          'controls': controls, 'payload': payload, 'candidate': verify, 'layout': layout,
          'probe_performs_mmio_writes': args.block_read, 'probe_submits_storage_commands': args.block_read,
          'probe_writes_storage_media': False, 'probe_publishes_root': False, 'phone_tested': False}
(device / ('evidence/' + stem + '-candidate.json')).write_text(json.dumps(record, indent=2) + '\n')
print('PASS: isolated', stem, 'linked archive, host controls and exact phone candidate')
print('Candidate:', verify['sha256'], verify['bytes'])
