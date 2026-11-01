"""Tie host build/runtime evidence to the exact proposed deployment files."""
import hashlib
import json
from pathlib import Path

root = Path('/mnt/g/UniXNU-Port')
device = root / 'ports/UniXNU-venus'
artifact = root / 'artifacts/venus-ufs-root'
deployment = root / 'artifacts/venus-deployment'
def load(path): return json.loads(path.read_text())
def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def need(ok, message):
    if not ok: raise SystemExit(message)
kernel_hash = sha(artifact / 'kernel/kernel.macho')
off = load(artifact/'qemu-off/gdb-stop.json')
crypto = load(artifact/'qemu-owner-crypto/gdb-stop.json')
mount = load(artifact/'qemu-root-mount/gdb-stop.json')
for observation in (off, crypto, mount):
    need(observation['kernel_sha256'] == kernel_hash and not observation['bounded_timeout_interrupted'], 'Kernel observation identity/timeout mismatch')
need(off['stop_symbol'] == '_IOFindBSDRoot' and off['native_ufs']['mapped'] == 0, 'Default-off regression failed')
need(crypto['owner_root_crypto_probe']['_native_verified_root_status'] == 1 and
     crypto['owner_root_crypto_probe']['results'] == [0, 4, 3, 3, 4, 5, 2, 1], 'Real kernel crypto controls failed')
binding = mount['owner_root_binding_audit']
need(mount['stop_symbol'] == '_native_owner_root_accepted_checkpoint' and binding['boot_root_accepted'] and
     binding['_native_owner_root_readonly'] == 1 and binding['_native_verified_block_root_uuid_match'] == 1 and
     binding['_native_verified_block_wrong_uuid_refused'] == 1, 'Actual readonly root acceptance is missing')
payload = load(artifact/'phone/payload.json')
phone = load(artifact/'phone/verification.json')
need(payload['kernel_sha256'] == kernel_hash and sha(artifact/'phone/kernel.macho') == payload['payload_kernel_sha256'] and
     sha(artifact/'phone/kernel.macho.adt') == payload['adt_sha256'], 'Payload identity mismatch')
need(sha(artifact/'phone/boot-venus-unixnu.img') == phone['sha256'] and phone['roundtrip_verified'], 'Root boot container mismatch')
need(payload['trust_cache_sha256'] == '7416ca4f8377146626bb284e2133c76bee6cb4e3ee0af5d648b186235a7323a7', 'Wrong original trust bundle')
need(payload['data_ramdisk_sha256'] == sha(deployment/'Data.dbr'), 'Data seed identity mismatch')
root_image = load(deployment/'unixnu-root.json')
need(root_image['partition'] == 'unixnu' and root_image['partition_bytes'] == 64 << 30 and
     root_image['native_c_signatures_and_all_blocks_verified'] and
     sha(deployment/'unixnu-root.img') == root_image['image_sha256'], 'Root image qualification mismatch')
gpt_directory = deployment/'gpt-apply-label'
gpt = load(gpt_directory/'gpt-tool.json')
gpt_test = load(device/'evidence/gpt-efi-menu-host-test.json')
need(gpt['mode'] == 'apply' and gpt_test['compiled_efi_executed'] and
     gpt_test['efi_sha256'] == sha(gpt_directory/'VenusPartition.efi') == gpt['efi_sha256'] and
     gpt_test['boot_image_sha256'] == sha(gpt_directory/'boot-venus-unixnu.img') == gpt['image_sha256'], 'GPT tool evidence mismatch')
need(gpt['fat_label'] == 'VENUSXNU' and gpt['fat_recognizer_test'] and gpt_test['unixnu_menu_chain_executed'] and
     gpt_test['actual_payload_sha256'] == sha(gpt_directory/'payload.img'), 'Missing board-FAT/menu-chain qualification')
record = {'upstream_revision': '16e592abee8a550dec8154ed1f38b5ebc4f16213',
          'configuration': 'venus_ufs_root_defconfig', 'kernel_sha256': kernel_hash,
          'bootstrap_missing_object_recovery_tested': True, 'root_binding': binding,
          'root_mount_backend': 'read-only QEMU Virtio disks, not phone UFS',
          'phone_boot': phone, 'payload': payload, 'root_image': root_image,
          'data_validation': load(device/'evidence/root-payload-inputs.json'), 'gpt_tool': gpt,
          'phone_gpt_changed': False, 'phone_root_image_written': False,
          'phone_root_mount_verified': False, 'systemos_data_mount_and_userspace_verified': False}
(device/'evidence/deployment-host-ready.json').write_text(json.dumps(record, indent=2)+'\n')
print('PASS: root kernel, real crypto/refusal, actual readonly APFS root acceptance, signed root/Data inputs and compiled GPT tool')
print('Root boot:', phone['sha256'])
print('GPT tool:', gpt['image_sha256'])
