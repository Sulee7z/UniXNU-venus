"""Validate the collected dual-layout and compiled UFS preparation evidence."""
import hashlib
import json
from pathlib import Path

root = Path('/mnt/g/UniXNU-Port')
device = root / 'ports/UniXNU-venus'
def load(path):
    return json.loads(path.read_text())
def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
def need(value, message):
    if not value:
        raise SystemExit(message)

layout = load(device / 'evidence/dual-readonly.json')
abi = load(root / 'artifacts/venus-storage-abi/interface-audit.json')
snapshot = load(root / 'artifacts/venus-storage-abi/qemu/gdb-stop.json')
need(layout['device_write_performed'] is False and layout['official_partition_plan_created'] is False, 'Unexpected partition operation')
need(abi['method_slots'] == 190 and abi['live_native_4k'] and
     abi['live_instance_sizes'] == {'IOBlockStorageDevice': 144, 'IOService': 136}, 'Storage ABI evidence incomplete')
need(snapshot['kernel_sha256'] == abi['candidate_sha256'] and not snapshot['bounded_timeout_interrupted'], 'Wrong live metadata input')
variants = {}
for name in ('unixnu', 'userdata'):
    directory = root / ('artifacts/venus-ufs-probe-' + name)
    report, binding = load(directory / 'venus-build.json'), load(directory / 'bindings.json')
    need(report['root_partition'] == name and report['archive_sha256'] == sha(directory / 'libShengUfs.a'), 'UFS archive mismatch')
    need(not report['unresolved_kernel_imports'] and binding['virtual_methods_checked'] == 190 and
         binding['unresolved_original_imports'] == 0 and report['root_partition_test_passed'], 'UFS preparation did not pass')
    need(not report['linked_into_kernel'] and not report['hardware_tested'], 'Scope mismatch')
    variants[name] = {'build': report, 'bindings': binding}
result = {'upstream_revision': '16e592abee8a550dec8154ed1f38b5ebc4f16213',
          'sheng_page_revision': '516a780473a2ac59c8b438e132bb60204dda9e22',
          'dual_snapshot': layout['snapshot'], 'dual_conditions': layout['conditions'],
          'logical_block_bytes': layout['logical_block_bytes'], 'userdata': layout['userdata'],
          'f2fs': layout['f2fs'], 'storage_abi': {k: v for k, v in abi.items() if k != 'methods'},
          'variants': variants, 'selected_deployment_partition': None,
          'physical_ufs_verified': False, 'root_policy_integrated': False,
          'recovery_shrink_verified': False, 'partition_writes_performed': False}
(device / 'evidence/storage-preparation.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS: read-only layout, live iOS17 storage ABI, both bounded partition variants and import binding evidence')
