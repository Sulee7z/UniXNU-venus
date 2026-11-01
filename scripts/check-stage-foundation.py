#!/usr/bin/env python3
"""Recheck the ordered bring-up foundation using actual profiles and the pinned live DT.

Host only: configuration, ADT, retained firmware mapping and existing persistence
tests. Does not boot or write a phone, and does not claim hardware completion.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tomllib

DEVICE = Path(__file__).resolve().parents[1]
ROOT = DEVICE.parents[1]
BASE = Path('/root/unixnu-build/UniXNU-sheng-base')
BUILD = Path('/root/unixnu-build/venus-legacy-full')
OUT = ROOT/'artifacts/venus-stage-foundation'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--snapshot', action='store_true', help='Save the original board before alignment')
options = parser.parse_args()
OUT.mkdir(parents=True, exist_ok=True)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def need(ok, message):
    if not ok:
        raise SystemExit(message)


if options.snapshot:
    before = OUT/'board-before.toml'
    need(not before.exists(), 'Foundation snapshot already exists; preserve it')
    shutil.copy2(DEVICE/'board.toml',before)
    print('Saved board baseline:',sha(before))
    raise SystemExit(0)

commands = []
def run(command, name, timeout=180):
    argv = [str(x) for x in command]
    result = subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
    (OUT/(name+'.log')).write_text(result.stdout+result.stderr)
    commands.append({'command':argv,'returncode':result.returncode,'log':name+'.log'})
    need(result.returncode==0, name+' failed: '+result.stdout+result.stderr)
    return result.stdout

sys.path.insert(0,str(BASE/'scripts'))
from unixnu.cli import parser as cli_parser
from unixnu.config import Context
from unixnu.devicetree import generate, read_fdt, registers
converter = BASE/'scripts/unixnu/devicetree.py'
reference_converter = ROOT/'sources/UniXNU-guide/scripts/unixnu/devicetree.py'
need(converter.read_text()==reference_converter.read_text(),
     'Active converter differs from the previously qualified phandle/arm-io implementation')
run(['git','-C',BASE,'apply','--reverse','--check',DEVICE/'patches/tools/adt-handoff.patch'],'converter-patch-check')
run(['python3','-c',
     "import sys,runpy; sys.path.insert(0,sys.argv[1]); path=sys.argv[2]; sys.argv=[path]; runpy.run_path(path,run_name='__main__')",
     BASE/'scripts',ROOT/'sources/UniXNU-guide/scripts/test-devicetree-phandles.py'],'phandle-regression')
ctx = Context(cli_parser().parse_args(['status','-D',str(DEVICE),'--out',str(BUILD)]))
need(ctx.board['board']['os_profile']=='ipados-17.7.11-21H461', 'Wrong OS profile')
need(ctx.config_name=='venus_ufs_root_defconfig', 'Select the full root configuration before checking')
need(ctx.board['kernel']['defconfig']=='venus_ufs_root_defconfig', 'Default config still points to early entry')
need(ctx.config.get('XNU_VENUS_UFS_ROOT') and ctx.config.get('XNU_NATIVE_LEGACY_DISPLAY'),
     'Resolved config does not contain the tested root/display implementations')
for key in ('XNU_NATIVE_UFS','XNU_OWNER_ROOT_TRUST','XNU_OWNER_DATA_MOUNT'):
    need(ctx.config.get(key), 'Missing foundation config: '+key)
old = tomllib.loads((OUT/'board-before.toml').read_text())
new = tomllib.loads((DEVICE/'board.toml').read_text())
for key in ('board','components','userdata','device_tree','firmware','bootimg'):
    need(old[key]==new[key], 'Unexpected unrelated board change: '+key)
need(old['kernel']['archives']==new['kernel']['archives'] and old['kernel']['patch_series']==new['kernel']['patch_series'],
     'Foundation alignment unexpectedly changed driver/archive selection')
args = new['payload']['kernel_args']
need(len({a.split('=',1)[0] for a in args})==len(args), 'Duplicate boot argument keys')
need({'cpus=1','native-ufs-root=1','sheng-data-persist=2','sheng-log-reserve=1024',
      'offline-key-events=1','sheng-aks=1','offline-hid-input=1','offline-hid-home=1',
      'sheng-gpu-power=0','sheng-fb-gpu=0'}<=set(args), 'Incorrect ordered-baseline gates')

run(['python3',DEVICE/'scripts/check-venus-hardware.py','--unixnu',BASE,
     '--evidence',ROOT/'evidence/venus/20261025T020508Z','--soc',ROOT/'ports/UniXNU-sm8350-common',
     '--output',OUT/'hardware'],'hardware')
hardware = json.loads((OUT/'hardware/hardware.json').read_text())
need(not hardware['errors'] and len(hardware['reservations'])==21,'Hardware comparison failed')
mapping = ROOT/'ports/uefi-venus/Platforms/Xiaomi/venusPkg/Library/MemoryMapLib/MemoryMapLib.c'
dsc = ROOT/'ports/uefi-venus/Platforms/Xiaomi/venusPkg/venus.dsc'
qualified_map = json.loads((DEVICE/'evidence/highmem-map-check.json').read_text())
need(sha(mapping)==qualified_map['source_sha256'],'UEFI map changed since the high-memory audit')
need('-DUNIXNU_VENUS_HIGH_MEMORY' in dsc.read_text(),'UEFI high-memory support is not enabled')
owned = int(new['payload']['adt']['owned_memory_size'],0)
need(owned==0x40000000 and owned<=qualified_map['high_region']['bytes'],'Owned memory differs from tested baseline')

spec = importlib.util.spec_from_file_location('adt_codec',DEVICE/'scripts/inject-a660-firmware-adt.py')
adt = importlib.util.module_from_spec(spec);spec.loader.exec_module(adt)
control_path = ROOT/'artifacts/venus-frontboard-mode-phone/kernel.macho.adt'
control = adt.parse(control_path.read_bytes())
old_chosen = dict(adt.find(control,'chosen').props)
seed = int.from_bytes(old_chosen['unique-chip-id'],'little')
generated = generate(OUT/'hardware/hardware.dtb',ctx.board,unique_chip_id=f'{seed:x}',data=True,trust=True)
(OUT/'kernel.macho.adt').write_bytes(generated)
tree = adt.parse(generated)
chosen = dict(adt.find(tree,'chosen').props)
product = dict(adt.find(tree,'product').props)
buttons = dict(adt.find(tree,'buttons').props)
need(product['artwork-display-gamut']==b'sRGB\0','Typed sRGB property did not reach the actual ADT')
need(product['model']==b'J120AP\0','Product model does not match selected OS board identity')
need(int.from_bytes(product['thin-bezel'],'little')==1,'Bezel class missing')
need(buttons['button-names']==b'hold\0voldown\0volup\0' and int.from_bytes(buttons['home-button-type'],'little')==2,
     'Button description differs from the board input policy')
for key in ('unique-chip-id','chip-id','root-matching','dram-base','dram-size','darwinboot-memory-size',
            'text-fixups','osenvironment','amfi-only-platform-code'):
    need(chosen[key]==old_chosen[key],'Unexpected handoff identity/policy change: '+key)
need('ephemeral-storage' not in chosen,'Persistent Data described as ephemeral')
intc = dict(adt.find(adt.find(tree,'arm-io'),'intc').props)
need(intc['AAPL,phandle']==intc['phandle'],'Apple interrupt-parent alias missing')
arm_io = adt.find(tree,'arm-io')
old_arm_io = adt.find(control,'arm-io')
need(dict(arm_io.props)['ranges']==dict(old_arm_io.props)['ranges'],'arm-io translation changed from tested control')
for name in ('intc','timer'):
    need(dict(adt.find(arm_io,name).props)==dict(adt.find(old_arm_io,name).props),
         'Interrupt/timer binding differs from tested control: '+name)
need(dict(adt.find(adt.find(tree,'chosen'),'memory-map').props)==
     dict(adt.find(adt.find(control,'chosen'),'memory-map').props),'Data/trust placeholders changed')

# Use the existing persistence core tests, with modeled media only. They do not
# substitute for the required actual Data write/reboot/readback sequence.
ram = ROOT/'sources/UniXNU-guide/drivers/RamBlock'
run(['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
     '-fno-pie','-no-pie','-fsanitize=address,undefined',ram/'Test/persist.cpp','-o',OUT/'persist-test'],
    'persist-build')
persist_output = run([OUT/'persist-test'],'persist-test',timeout=180)
run(['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
     '-Wno-unused-function','-fno-pie','-no-pie','-fsanitize=address,undefined',
     ram/'Test/direct.cpp','-o',OUT/'direct-test'],'direct-build')
direct_output = run([OUT/'direct-test'],'direct-test',timeout=180)

inventory = []
live = read_fdt((ROOT/'evidence/venus/20261025T020508Z/live.dtb').read_bytes())
def visit(node, parent=''):
    path = parent+'/'+node.name if node.parent else ''
    compatible = node.strings('compatible')
    text = (path+' '+' '.join(compatible)).lower()
    relevant = any(k in text for k in ('touch','focal','goodix','novatek','himax','synapt','fts','nvt',
                                      'sensor','slpi','ssc','lis2','lsm6','bmi','akm','ltr','tmd'))
    if relevant and (compatible or path.startswith('/reserved-memory/')):
        selected = {}
        for key,value in node.properties.items():
            if key in ('compatible','reg','status','interrupts','interrupt-parent','spi-max-frequency','spi-cpol','spi-cpha') or any(k in key for k in ('gpio','supply','firmware')):
                selected[key] = value.hex()
        inventory.append({'path':path,'compatible':compatible,'node_enabled':node.enabled(),'properties_hex':selected})
    for child in node.children:
        visit(child,path)
visit(live)
(OUT/'declared-peripherals.json').write_text(json.dumps(inventory,indent=2)+'\n')
report = {'device':'venus','date':'2026-10-28','base_revision':run(['git','-C',BASE,'rev-parse','HEAD'],'base-revision').strip(),
    'board_before_sha256':sha(OUT/'board-before.toml'),'board_after_sha256':sha(DEVICE/'board.toml'),
    'resolved_config':ctx.config_name,'resolved_config_sha256':sha(ctx.config_path),
    'source_profiles':[str(p) for p in ctx.profile_files], 'hardware':hardware,
    'active_converter_sha256':sha(converter),'reference_converter_sha256':sha(reference_converter),
    'converter_patch_sha256':sha(DEVICE/'patches/tools/adt-handoff.patch'),
    'firmware_map_sha256':sha(mapping),'owned_memory_bytes':owned,
    'generated_adt_sha256':sha(OUT/'kernel.macho.adt'),
    'adt_product':{'model':'J120AP','gamut':'sRGB','thin_bezel':1},
    'adt_buttons':{'names':['hold','voldown','volup'],'home_button_type':2},
    'root_data_trust_identity_preserved':True,
    'persistence_source_test':{'result':persist_output.strip(),'test_sha256':sha(ram/'Test/persist.cpp'),
                               'core_sha256':sha(ram/'PersistOverlay.h'),'actual_phone_persistence_verified':False},
    'direct_data_source_test':{'result':direct_output.strip(),'test_sha256':sha(ram/'Test/direct.cpp'),
                              'core_sha256':sha(ram/'DirectDisk.h'),'hardware_test':False},
    'peripheral_inventory_sha256':sha(OUT/'declared-peripherals.json'),
    'remaining_stage_gates':['Actual Data write/reboot/readback validation',
        'Known CPU-presented frame and completed swaps','Physical input protocol and event qualification'],
    'commands':commands,'phone_tested':False,
    'scope':'Host foundation/configuration correction and existing core checks; no claim that all front-stage drivers are complete'}
(DEVICE/'evidence/stage-foundation.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: resolved full config, pinned CPU/GIC/DRAM/reservations, actual typed ADT and persistence core tests')
print('Physical Data persistence, CPU frame/swap and input remain stage gates; no phone operation performed')
