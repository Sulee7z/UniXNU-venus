#!/usr/bin/env python3
"""Check compiled reset matching, real QEMU secondary startup, and the four-core payload."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path('/mnt/g/UniXNU-Port')
OUT=ROOT/'artifacts/venus-smp-038'
CORE=ROOT/'artifacts/venus-smp-037/core-r3'
KERNEL=ROOT/'artifacts/venus-metal-touch/kernel-link-36'
PHONE=ROOT/'artifacts/venus-metal-touch-038/phone'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


def reset_mask(path):
    text=subprocess.check_output(['/usr/bin/llvm-objdump','--macho','--disassemble','--no-show-raw-insn',str(path)],text=True)
    begin=text.index('_reset_vector:')
    body=text[begin:begin+6000]
    found=re.findall(r'and\s+x0,\s*x15,\s*#(0x[0-9a-f]+)',body)
    assert found and int(found[0],16) in (0xff,0xffff)
    return int(found[0],16)


old=reset_mask(CORE/'start-before.o')
new=reset_mask(CORE/'start.o')
assert old==0xff and new==0xffff
hardware=[0x80000000+(i<<8) for i in range(8)]
assert [value&old for value in hardware]==[0]*8
assert [value&new for value in hardware]==[i<<8 for i in range(8)]
qdir=ROOT/'artifacts/venus-smp-038/qemu-late-four'
q=json.loads((qdir/'gdb-stop.json').read_text())
plan=json.loads((ROOT/'artifacts/venus-smp-037/state-plan.json').read_text())
assert q['kernel_sha256']==sha(KERNEL/'kernel.macho')==plan['kernel_sha256']
assert q['stop_symbol']=='_rtclock_intr' and not q['bounded_timeout_interrupted']
assert q['pc']==q['function_return_target'] and q['native_4k_mmu_observed']
fields={}
for name,address in plan['field_ranges'].items():
    value=bytes.fromhex(q['memory'][address])
    fields[name]=[int.from_bytes(value[i:i+4],'little') for i in range(0,len(value),4)]
assert fields['_armcpu_smp_running'][0]==3
assert fields['_armcpu_smp_step'][1:4]==[7,7,7]
assert fields['_armcpu_smp_fail']==[0]*8 and fields['_armcpu_smp_psci_rc']==[0]*8
assert sum(fields['_armcpu_core_timer'][:4])>0
assert fields['_processor_avail_count'][0]==4
candidate=json.loads((PHONE.parent/'candidate.json').read_text())
assert sha(PHONE/'boot-venus-unixnu.img')==candidate['image_sha256']
assert candidate['cpu_count_requested']==4 and candidate['cpu_affinities']==[0,0x400,0x500,0x700]
assert candidate['args'].split().count('cpus=4')==1 and 'cpus=8' not in candidate['args'].split()
link=json.loads((KERNEL/'report.json').read_text())
baseline=json.loads((ROOT/'artifacts/venus-metal-touch/kernel-link-34/report.json').read_text())
assert link['touch_archive_sha256']==baseline['touch_archive_sha256']
assert link['mainline_hid_object_sha256']==baseline['mainline_hid_object_sha256']
assert link['gpu_archive_sha256']==baseline['gpu_archive_sha256']
report={'passed':True,'old_reset_affinity_mask':old,'new_reset_affinity_mask':new,
    'old_hardware_affinities_alias_boot_cpu':True,'new_hardware_affinities_unique':True,
    'compiled_max_cpus':4,'qemu_registered_cpu_nodes':q['armdt_globals']['_armdt_platform_cpu_count'],
    'qemu_running_secondary_cpus':3,'qemu_available_cpus':4,'qemu_state':fields,
    'qemu_timer_dispatch_return_verified':True,
    'qemu_timer_all_four_cpus':all(value>0 for value in fields['_armcpu_core_timer'][:4]),
    'qemu_ipi_delivery_verified':False,
    'image_sha256':candidate['image_sha256'],'kernel_sha256':candidate['kernel_sha256'],
    'touch_producer_consumer_preserved':True,'gpu_archive_preserved':True,
    'phone_operations':False,'smp_hardware_verified':False,'full_qemu_systemos_verified':False,
    'scope':'Compiled Affinity1 correction and real QEMU four-core startup plus timer dispatch return. The bounded sample does not contain a timer on every core or delivered IPIs; not a device or UI performance qualification.'}
(OUT/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('passed','qemu_running_secondary_cpus','qemu_available_cpus','qemu_timer_all_four_cpus','qemu_ipi_delivery_verified','image_sha256')},indent=2))
