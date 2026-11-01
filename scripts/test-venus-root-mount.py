"""Observe the real prelinked APFS/owner-root chain against read-only host disks."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

root = Path('/mnt/g/UniXNU-Port')
artifact = root / 'artifacts/venus-ufs-root'
inputs = root / 'artifacts/venus-deployment'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--owned-memory-size', type=lambda value: int(value, 0), default=0x20000000)
parser.add_argument('--inspect-memory-budget', action='store_true')
parser.add_argument('--inspect-os-services', action='store_true',
                     help='Read and check AKS/HID software state at the real root checkpoint')
parser.add_argument('--systemos-checkpoint',action='store_true',
                    help='Continue beyond root acceptance to the actual SystemOS mount/owner-cache checkpoint')
parser.add_argument('--qemu-memory-mib', type=int, default=2048)
parser.add_argument('--kernel', type=Path, default=artifact/'kernel/kernel.macho')
parser.add_argument('--prelink-report', type=Path, default=artifact/'kernel/kernel.json')
parser.add_argument('--out-name')
parser.add_argument('--extra-kernel-arg', action='append', default=[])
args = parser.parse_args()
if not 0x10000000 <= args.owned_memory_size <= 0x200000000 or args.owned_memory_size & 0x1fffff:
    raise SystemExit('Owned window must satisfy the real DarwinBoot size/alignment bounds')
default_name = 'qemu-root-mount' if args.owned_memory_size == 0x20000000 else f'qemu-root-mount-{args.owned_memory_size >> 20}m'
out = artifact / (args.out_name or default_name)
out.mkdir(exist_ok=True)
memory_reads = {}
service_reads = {}
if args.inspect_memory_budget or args.inspect_os_services:
    kernel = args.kernel
    symbols = subprocess.check_output(['/usr/bin/llvm-nm', str(kernel)], text=True)
    def add_reads(target, fields):
        for name, size in fields:
            addresses = re.findall(r'^([0-9a-fA-F]+)\s+\S\s+'+re.escape(name)+r'$', symbols, re.M)
            if len(addresses) != 1 or not int(addresses[0],16):
                raise SystemExit('Missing unique nonzero observation symbol: '+name)
            target[name] = f'{int(addresses[0],16):x}:{size:x}'
    if args.inspect_memory_budget:
        add_reads(memory_reads, (('_vm_page_free_count', 4), ('_vm_page_wire_count', 4), ('_max_mem', 8)))
    if args.inspect_os_services:
        add_reads(service_reads, (('_native_keyevents_stage',4), ('_native_keyevents_status',4),
            ('_native_keyevents_service',8), ('_native_aks_opens',4), ('_native_aks_calls',4),
            ('_native_hid_stage',4), ('_native_hid_load_status',4), ('_native_hid_matching_load_status',4),
            ('_native_hid_resource_found',4), ('_native_hid_input_meta_status',4),
            ('_native_hid_input_object',8), ('_native_hid_input_events',32), ('_native_hid_input_results',32)))
        for name, size in (('_venus_st_stage',4), ('_venus_st_status',4), ('_venus_st_chip_id',4),
                           ('_venus_st_firmware_version',4), ('_venus_st_frames',4), ('_venus_st_errors',4),
                           ('_venus_st_hid_status',4), ('_venus_st_hid_ready',4), ('_venus_st_hid_reports',4)):
            addresses = re.findall(r'^([0-9a-fA-F]+)\s+\S\s+'+re.escape(name)+r'$', symbols, re.M)
            if len(addresses) == 1 and int(addresses[0], 16):
                service_reads[name] = f'{int(addresses[0],16):x}:{size:x}'
    with kernel.open('rb') as stream: kernel_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    (out/'memory-plan.json').write_text(json.dumps({'kernel_sha256':kernel_hash,
        'read_memory':list(memory_reads.values())+list(service_reads.values())},indent=2)+'\n')
fdt = out / 'qemu.dtb'
command = ['qemu-system-aarch64', '-machine', 'virt,virtualization=off,secure=off,gic-version=3,dumpdtb=' + str(fdt),
           '-cpu', 'cortex-a710', '-m', str(args.qemu_memory_mib), '-smp', '1', '-display', 'none', '-nic', 'none',
           '-device', 'ramfb', '-global', 'virtio-mmio.force-legacy=false']
for name, filename in (('offline-block', 'OS.raw'), ('offline-extra', 'SystemOS.raw')):
    command += ['-blockdev', json.dumps({'driver': 'raw', 'node-name': name, 'read-only': True,
                                        'file': {'driver': 'file', 'filename': str(inputs / filename), 'read-only': True, 'locking': 'off'}}),
                '-device', 'virtio-blk-device,drive=' + name]
subprocess.run(command, check=True, timeout=30)
probe = ['python3', root / 'ports/UniXNU-venus/scripts/probe-venus-prelinked.py',
         '--kernel', args.kernel, '--prelink-report', args.prelink_report,
         '--output', out, '--armvirt', '--armdt-platform', '--armcpu', '--nvram-proxy', '--qemu-ramfb',
         '--crypto-hash-method', 'sha2-384', '--osenvironment', 'main', '--amfi-platform-only',
         '--owned-memory-size', hex(args.owned_memory_size), '--qemu-memory-mib', str(args.qemu_memory_mib),
         '--virtio-block-image', inputs / 'OS.raw', '--virtio-extra-block-image', inputs / 'SystemOS.raw',
         '--virtio-mmio-fdt', fdt, '--root-match-volume-uuid', '04769D26-2CA0-4825-B443-E2E5F88300F2',
          '--trust-cache', inputs / 'original-static-system.bundle', '--load-apfs',
          '--inspect-owner-root', '--kernel-extra-args',
          ' '.join(['sheng-pmgr=2', 'native-ufs-root=0', *args.extra_kernel_arg]), '--timeout', '180']
expected_stop='_native_owner_cache_checkpoint' if args.systemos_checkpoint else '_native_owner_root_accepted_checkpoint'
probe+=['--break-symbol',expected_stop] if args.systemos_checkpoint else ['--owner-root-accepted']
if memory_reads or service_reads: probe += ['--metadata-plan', out/'memory-plan.json']
subprocess.run([str(x) for x in probe], check=True)
report = json.loads((out / 'gdb-stop.json').read_text())
if report['stop_symbol'] != expected_stop or report['bounded_timeout_interrupted']:
    raise SystemExit('Mount did not reach the requested real checkpoint; inspect the saved report')
if args.systemos_checkpoint:
    cache=report['owner_cache_mount']
    if cache['_native_owner_cache_status']!=0 or cache['_native_owner_cache_stage']!=6 or not cache['_native_owner_cache_authorized']:
        raise SystemExit('Original SystemOS mount/authorization failed; inspect the actual cache state')
    (out/'systemos-mount.json').write_text(json.dumps({'kernel_sha256':report['kernel_sha256'],
        'passed':True,'owner_cache':cache,'scope':'Real original SystemOS APFS mount and authorization in QEMU, before Data; no UFS/overlay hardware'},indent=2)+'\n')
if service_reads:
    services = {}
    for name, address in service_reads.items():
        data = report['memory'][address]
        if data.startswith('E') or len(data) != int(address.split(':')[1],16)*2:
            raise SystemExit('OS service read failed: '+name)
        raw = bytes.fromhex(data)
        services[name] = ([int.from_bytes(raw[i:i+4],'little') for i in range(0,32,4)]
                          if len(raw)==32 else int.from_bytes(raw,'little'))
    gates = set(' '.join(args.extra_kernel_arg).split())
    aks_enabled = {'offline-key-events=1','sheng-aks=1'} <= gates
    hid_enabled = {'offline-hid-input=1','offline-hid-home=1'} <= gates
    aks_ok = (services['_native_keyevents_stage']==3 and services['_native_keyevents_status']==0 and
              services['_native_keyevents_service']!=0) if aks_enabled else services['_native_keyevents_stage']==0
    hid_ok = (services['_native_hid_stage']==3 and services['_native_hid_load_status']==0 and
              services['_native_hid_matching_load_status']==0 and services['_native_hid_resource_found']==1 and
              services['_native_hid_input_meta_status']==0 and services['_native_hid_input_object']!=0 and
              all(services['_native_hid_input_events'][i]>0 and services['_native_hid_input_results'][i]==0
                  for i in (0,1,2))) if hid_enabled else services['_native_hid_stage']==0
    result = {'kernel_sha256':report['kernel_sha256'], 'aks_enabled':aks_enabled, 'hid_enabled':hid_enabled,
              'aks_state_passed':bool(aks_ok), 'hid_state_passed':bool(hid_ok), 'state':services,
              'scope':'Real QEMU IOKit initialization at root acceptance; no touch hardware or userspace UI qualification'}
    (out/'os-services.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not aks_ok or not hid_ok:
        raise SystemExit('OS service initialization/control failed; inspect os-services.json')
if memory_reads:
    counters = {}
    for name, address in memory_reads.items():
        data = report['memory'][address]
        if data.startswith('E') or len(data) != int(address.split(':')[1],16)*2:
            raise SystemExit('VM counter read failed: '+name)
        counters[name] = int.from_bytes(bytes.fromhex(data), 'little')
    counters['free_bytes'] = counters['_vm_page_free_count'] * 4096
    counters['requested_owned_bytes'] = args.owned_memory_size
    counters['authenticated_virtio_policy_copies'] = report['native_virtio_integrity']['_native_virtio_verified_devices']
    counters['scope'] = ('Actual QEMU SystemOS mount checkpoint, before Data/userspace' if args.systemos_checkpoint else
                         'Actual QEMU OS-root checkpoint; authenticated Virtio policies have protected-memory copies, while SystemOS/Data mounts and userspace are later stages')
    (out/'memory-budget.json').write_text(json.dumps(counters,indent=2)+'\n')
    print(json.dumps(counters,indent=2))
print('PASS: actual APFS reached '+expected_stop+' on read-only host disks')
