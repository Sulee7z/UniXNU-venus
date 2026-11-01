#!/usr/bin/env python3
"""Cross-check the assembled Venus iOS26 candidate without touching the phone."""
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path('/root/unixnu-build')
PROJECT = Path('/mnt/g/UniXNU-Port')
PHONE = ROOT / 'venus-ios26-phone'
PAYLOAD = PHONE / 'payload.img'
KERNEL = ROOT / 'venus-ios26-prelinked'  # placeholder, replaced below
PRELINK = ROOT / 'venus-ios26-prelink-root-v3/kernel.macho'
TRUST = ROOT / 'venus-ios26-trustcache.bundle'
DATA_PLAN = ROOT / 'venus-ios26-data-plan.json'
DATA_PACKED = ROOT / 'venus-ios26-data.dbr'
DATA_RAW = ROOT / 'venus-ios26-data.apfs'
ROOT_IMAGE = Path('/mnt/c/unixnu-ios26-root/userdata-root.json')
ARTIFACT = PROJECT / 'artifacts/venus-ios26'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def payload_file(name):
    return subprocess.check_output(['mtype', '-i', str(PAYLOAD), '::/EFI/UniXNU/Payloads/' + name])


def main():
    checks = {}
    codec = module(PROJECT / 'ports/UniXNU-venus/scripts/inject-a660-firmware-adt.py', 'adt_codec')
    tree = codec.parse(payload_file('kernel.macho.adt'))
    chosen = codec.find(tree, 'chosen')
    memory_map = codec.find(chosen, 'memory-map')
    props = dict(chosen.props)
    plan = json.loads(DATA_PLAN.read_text())
    volumes = json.loads((ROOT / 'venus-ios26-inputs/volumes.json').read_text())['containers']

    # ADT
    checks['adt_seed_256'] = len(props['random-seed']) == 256
    checks['adt_crypto_sha2_384'] = props.get('crypto-hash-method') == b'sha2-384\0'
    checks['adt_dram'] = (int.from_bytes(props['dram-base'], 'little'),
                          int.from_bytes(props['dram-size'], 'little')) == (0x80000000, 0x200000000)
    checks['adt_owned_memory'] = int.from_bytes(props['darwinboot-memory-size'], 'little') == 0x40000000
    checks['adt_nvram_proxy'] = 'nvram-proxy-data' in props and 'nvram-bank-size' in props
    root_matching = props.get('root-matching', b'').decode(errors='ignore')
    checks['adt_root_matches_os'] = volumes['OS']['volumes'][0]['uuid'] in root_matching
    names = [key for key, _ in memory_map.props if key != 'name']
    checks['adt_memory_map'] = names == ['PackedRAMDisk', 'TrustCache']
    checks['adt_map_sizes'] = all(len(v) == 16 for k, v in memory_map.props if k in ('PackedRAMDisk', 'TrustCache'))
    checks['adt_unique_chip_id'] = int.from_bytes(props['unique-chip-id'], 'little') != 0
    checks['adt_cpu_count'] = len([c for c in codec.find(tree, 'cpus').children]) == 8

    # Kernel and prelink identity
    kernel = payload_file('kernel.macho')
    checks['payload_kernel_matches_prelink'] = sha(kernel) == sha(PRELINK.read_bytes())
    checks['kernel_embeds_data_uuid'] = plan['volume_uuid'].encode() in kernel
    # The OS volume is selected through /chosen/root-matching in the ADT, not
    # compiled into the kernel; that link is asserted by adt_root_matches_os.
    checks['adt_is_only_os_selector'] = volumes['OS']['volumes'][0]['uuid'].encode() not in kernel
    magic = kernel[:4]
    checks['kernel_is_arm64_macho'] = magic == b'\xcf\xfa\xed\xfe'

    # Trust bundle: re-implement DarwinBoot's own structural checks here so the
    # verifier shares no code with the generator.
    cached = payload_file('kernel.macho.trustcache')

    def valid_trust(data):
        import struct
        count = struct.unpack_from('<I', data)[0]
        if not 0 < count <= 128:
            return False
        for index in range(count):
            begin = struct.unpack_from('<I', data, 4 + 4 * index)[0]
            end = struct.unpack_from('<I', data, 8 + 4 * index)[0] if index + 1 < count else len(data)
            if (begin < 4 + 4 * count or begin & 3 or end > len(data) or end - begin < 24
                    or struct.unpack_from('<I', data, begin)[0] != 2):
                return False
            entries = struct.unpack_from('<I', data, begin + 20)[0]
            if end - begin != 24 + entries * 24:
                return False
            for entry in range(entries):
                at = begin + 24 + entry * 24
                if not 1 <= data[at + 20] <= 4:
                    return False
                if entry and data[at - 24:at - 4] >= data[at:at + 20]:
                    return False
        return True

    checks['trust_matches_file'] = sha(cached) == sha(TRUST.read_bytes())
    checks['trust_valid_for_loader'] = valid_trust(cached)
    import struct as _struct
    checks['trust_single_static_module'] = _struct.unpack_from('<I', cached, 0)[0] == 1
    start = _struct.unpack_from('<I', cached, 4)[0]
    checks['trust_module_is_static'] = _struct.unpack_from('<I', cached, start)[0] == 2
    checks['trust_entry_count'] = _struct.unpack_from('<I', cached, start + 20)[0]

    # Data seed
    data = payload_file('scratch-data.img')
    checks['data_matches_packed'] = sha(data) == sha(DATA_PACKED.read_bytes())
    checks['data_raw_matches_receipt'] = sha(DATA_RAW.read_bytes()) == \
        json.loads((ROOT / 'venus-ios26-data.json').read_text())['raw_sha256']
    with DATA_RAW.open('rb') as stream:
        raw = stream.read(4096)
    checks['data_raw_is_apfs'] = raw[32:36] == b'NXSB'

    # Root image receipt (bytes already verified block-by-block at build time)
    receipt = json.loads(ROOT_IMAGE.read_text())
    checks['root_two_windows'] = [w['name'] for w in receipt['windows']] == ['OS', 'SystemOS']
    checks['root_os_window_is_modified_os'] = receipt['windows'][0]['source_sha256'] == \
        json.loads((ROOT / 'venus-ios26-root-candidate/root-report.json').read_text())['root_container']['sha256']
    checks['root_systemos_unmodified'] = receipt['windows'][1]['source_sha256'] == \
        volumes['SystemOS']['sha256']
    checks['root_fits_partition'] = receipt['image_bytes'] <= receipt['unixnu_capacity']

    # Boot container identity
    candidate = json.loads((ARTIFACT / 'candidate.json').read_text())
    checks['boot_image_matches_artifact'] = sha((ARTIFACT / 'boot-venus-ios26.img').read_bytes()) == \
        candidate['image_sha256']
    checks['boot_roundtrip'] = candidate['roundtrip_verified'] is True
    checks['boot_no_memory_conflicts'] = candidate['uefi_memory_conflicts'] == []
    checks['boot_payload_matches'] = sha(PAYLOAD.read_bytes()) == candidate['payload_sha256']
    checks['boot_adt_matches'] = sha(payload_file('kernel.macho.adt')) == candidate['adt_sha256']
    checks['boot_data_matches'] = sha(data) == candidate['data_sha256']
    checks['boot_trust_matches'] = sha(cached) == candidate['trust_sha256']

    failed = []
    for name, value in checks.items():
        if isinstance(value, bool) and not value:
            failed.append(name)
        elif value is None:
            failed.append(name + ':missing')
    report = dict(result='passed' if not failed else 'failed', checks=checks, failed=failed,
                  data_volume_uuid=plan['volume_uuid'],
                  os_volume_uuid=volumes['OS']['volumes'][0]['uuid'],
                  systemos_volume_uuid=volumes['SystemOS']['volumes'][0]['uuid'],
                  phone_operations=False)
    (ARTIFACT / 'consistency.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
