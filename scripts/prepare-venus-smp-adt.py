#!/usr/bin/env python3
"""Replace only CPU/PSCI nodes using the measured enabled Venus SMP hardware tree."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT=Path('/mnt/g/UniXNU-Port');DEVICE=ROOT/'ports/UniXNU-venus'
sys.path.insert(0,str(ROOT/'sources/UniXNU-guide/scripts'))
from unixnu.devicetree import read_fdt,registers
spec=importlib.util.spec_from_file_location('codec',DEVICE/'scripts/inject-a660-firmware-adt.py')
codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--affinities',default='0,0x400,0x500,0x700',help='Enabled hardware affinities within the compiled four-CPU kernel limit')
args=parser.parse_args()
out=args.output;out.mkdir(parents=True,exist_ok=False)
source=DEVICE/'dts/venus-smp.dts';hardware=out/'hardware.dtb'
subprocess.run(['dtc','-I','dts','-O','dtb','-i',str(ROOT/'ports/UniXNU-sm8350-common/dts'),
                '-i',str(DEVICE/'dts'),'-o',str(hardware),str(source)],check=True)
fdt=read_fdt(hardware.read_bytes())
cpus=next(node for node in fdt.children if node.name=='cpus')
enabled=[node for node in cpus.children if node.enabled()]
affinities=[registers(node)[0][0] for node in enabled]
assert affinities==[i<<8 for i in range(8)] and cpus.scalar('timebase-frequency')==19200000
selected=[int(value,0) for value in args.affinities.split(',')]
assert selected and selected[0]==0 and 1<=len(selected)<=4 and len(set(selected))==len(selected)
assert all(value in affinities for value in selected)
enabled=[enabled[affinities.index(value)] for value in selected]
affinities=selected
psci=next(node for node in fdt.children if node.name=='psci')
assert psci.strings('method')==['smc']
base=ROOT/'artifacts/venus-metal-touch-036/phone/payload.img'
old=subprocess.check_output(['mtype','-i',str(base),'::/EFI/UniXNU/Payloads/kernel.macho.adt'])
tree=codec.parse(old);node=codec.find(tree,'cpus');old_children=node.children.copy()
assert len(node.children)==1
template=node.children[0]
node.children=[]
for i,(hardware_cpu,affinity) in enumerate(zip(enabled,affinities)):
    properties=[(key,value) for key,value in template.props if key not in ('name','reg','state','compatible','timebase-frequency')]
    properties+=[('name',f'cpu{i}'.encode()+b'\0'),('reg',struct.pack('<I',affinity)),
                 ('state',b'running\0' if i==0 else b'waiting\0'),('compatible',hardware_cpu.properties['compatible']),
                 ('timebase-frequency',struct.pack('<I',cpus.scalar('timebase-frequency')))]
    node.children.append(codec.Node(f'cpu{i}',properties,[]))
assert not any(dict(child.props).get('name')==b'psci\0' for child in tree.children)
new_psci=codec.Node('psci',[('name',b'psci\0'),('compatible',b'arm,psci-1.0\0'),('method',b'smc\0')],[])
tree.children.append(new_psci)
new=codec.dump(tree)
(out/'kernel.macho.adt').write_bytes(new)
node.children=old_children;tree.children.remove(new_psci)
assert codec.dump(tree)==old,'Other ADT inputs changed'
report={'input_adt_sha256':hashlib.sha256(old).hexdigest(),'adt_sha256':hashlib.sha256(new).hexdigest(),
        'cpu_affinities':affinities,'cpu_count':len(affinities),'compiled_max_cpus':4,'psci':'smc','timebase_frequency':19200000,
        'hardware_dtb_sha256':hashlib.sha256(hardware.read_bytes()).hexdigest(),
        'all_other_adt_inputs_preserved':True,'phone_operations':False,'hardware_smp_verified':False}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
