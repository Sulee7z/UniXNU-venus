#!/usr/bin/env python3
"""Create bounded read-only CPU state ranges for the actual prelinked SMP kernel."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path('/mnt/g/UniXNU-Port')
kernel=ROOT/'artifacts/venus-metal-touch/kernel-link-36/kernel.macho'
names=subprocess.check_output(['/usr/bin/llvm-nm','--defined-only','--extern-only',str(kernel)],text=True)
fields={'_armcpu_smp_running':4,'_armcpu_smp_step':32,'_armcpu_smp_psci_rc':32,
        '_armcpu_smp_fail':32,'_armcpu_smp_seen_mpidr':32,'_armcpu_core_timer':32,
        '_armcpu_core_sgi':32,'_armcpu_ipi_sent':8,'_armcpu_ipi_interrupts':8,
        '_processor_avail_count':4}
ranges=[]
for name,size in fields.items():
    address=re.findall(r'^([0-9a-fA-F]+)\s+\S\s+'+re.escape(name)+r'$',names,re.M)
    assert len(address)==1,name
    ranges.append(address[0]+':'+format(size,'x'))
plan={'kernel_sha256':hashlib.sha256(kernel.read_bytes()).hexdigest(),'read_memory':ranges,
      'field_ranges':dict(zip(fields,ranges))}
path=ROOT/'artifacts/venus-smp-037/state-plan.json'
path.write_text(json.dumps(plan,indent=2)+'\n')
print('SMP state plan:',path)
