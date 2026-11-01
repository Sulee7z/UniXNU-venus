"""Bind the reduced ADT window, unchanged root inputs and real root checkpoint."""
import hashlib
import json
from pathlib import Path
import struct

root = Path('/mnt/g/UniXNU-Port')
artifacts = root/'artifacts/venus-ufs-root'
old, new = artifacts/'phone', artifacts/'phone-288m'
def load(path): return json.loads(path.read_text())
def need(condition, text):
    if not condition: raise SystemExit(text)
def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
before, after = load(old/'payload.json'), load(new/'payload.json')
for key in ('kernel_sha256','payload_kernel_sha256','kernel_args','trust_cache_sha256','data_ramdisk_sha256'):
    need(before[key] == after[key], 'Root input changed: '+key)
need(sha(new/'kernel.macho') == after['payload_kernel_sha256'], 'Payload kernel bytes differ')
original = (old/'kernel.macho.adt').read_bytes(); actual = (new/'kernel.macho.adt').read_bytes()
name = b'darwinboot-memory-size'.ljust(32,b'\0')
need(original.count(name) == actual.count(name) == 1,'Ambiguous memory property')
offset = original.index(name)+32
need(struct.unpack_from('<IQ',original,offset) == (8,0x20000000),'Unexpected previous memory value')
expected = bytearray(original); struct.pack_into('<Q',expected,offset+4,0x12000000)
def properties(data):
    found = {}
    def node(offset, parent):
        count, children = struct.unpack_from('<II', data, offset); offset += 8
        items = {}
        for _ in range(count):
            key = data[offset:offset+32].split(b'\0',1)[0].decode()
            size = struct.unpack_from('<I',data,offset+32)[0] & 0x7fffffff
            offset += 36; items[key] = data[offset:offset+size]; offset = (offset+size+3)&~3
        path = parent+'/'+items.get('name',b'').split(b'\0',1)[0].decode()
        found.update({path+'/'+key:value for key,value in items.items()})
        for _ in range(children): offset=node(offset,path)
        return offset
    need(node(0,'') == len(data), 'Invalid ADT extent')
    return found
left, right = properties(original), properties(actual)
changed = sorted(key for key in left.keys()|right.keys() if left.get(key) != right.get(key))
need(changed == ['/device-tree/chosen/darwinboot-memory-size', '/device-tree/chosen/random-seed'],
     'Unexpected ADT property changes: '+str(changed))
seed = '/device-tree/chosen/random-seed'
need(len(left[seed]) == len(right[seed]) and len(right[seed]) >= 32,'Random seed shape changed')
need(right['/device-tree/chosen/darwinboot-memory-size'] == struct.pack('<Q',0x12000000),'Wrong requested window')
boot = load(new/'verification.json')
need(sha(new/'boot-venus-unixnu.img') == boot['sha256'] and boot['roundtrip_verified'],'Boot container mismatch')
need(boot['efi'] == load(old/'verification.json')['efi'], 'Core loader EFI identities changed')
photo = load(root/'ports/UniXNU-venus/evidence/root-boot-memory-failure.json')
need(int(photo['largest_conventional_run_start'],16) % 0x200000 == 0 and
     0x12000000+0x200000 <= photo['largest_conventional_run_bytes'],'Observed run lacks window/alignment headroom')
observation = artifacts/'qemu-root-mount-288m/gdb-stop.json'
qemu = load(observation); binding=qemu['owner_root_binding_audit']
need(qemu['kernel_sha256'] == after['kernel_sha256'] and not qemu['bounded_timeout_interrupted'] and
     qemu['stop_symbol'] == '_native_owner_root_accepted_checkpoint' and binding['boot_root_accepted'] and
     binding['_native_owner_root_readonly'] == 1 and binding['_native_verified_block_root_uuid_match'] == 1 and
     binding['_native_verified_block_wrong_uuid_refused'] == 1,'Reduced-window actual APFS root checkpoint failed')
report = {'boot_image':str(new/'boot-venus-unixnu.img'),'boot_sha256':boot['sha256'],'boot_bytes':boot['bytes'],
          'owned_memory_bytes':0x12000000,'previous_owned_memory_bytes':0x20000000,
          'adt_changed_properties':changed,'same_kernel_trust_data_and_arguments':True,
          'qemu_root_checkpoint':str(observation),'qemu_report_sha256':sha(observation),
          'kernel_sha256':after['kernel_sha256'],'payload_kernel_sha256':after['payload_kernel_sha256'],
          'largest_observed_conventional_run_bytes':photo['largest_conventional_run_bytes'],
          'phone_root_mount_verified':False,'new_ram_boot_requires_authorization':True}
memory = artifacts/'qemu-root-mount-288m/memory-budget.json'
if memory.exists():
    budget=load(memory)
    need(budget['_max_mem'] == 0x12000000 and qemu['native_virtio_integrity']['_native_virtio_verified_devices'] == 2,
         'Owned memory or authenticated policy count differs')
    budget['authenticated_virtio_policy_copies'] = 2
    budget['scope'] = 'Actual 288 MiB QEMU OS-root checkpoint with two policies copied into protected kernel memory by NativeVirtioBlock::configureVerification; SystemOS/Data mounts and userspace are later stages'
    report['qemu_memory_budget'] = budget
(root/'ports/UniXNU-venus/evidence/root-memory-candidate.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
