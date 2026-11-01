#!/usr/bin/env python3
"""Offline display/input prerequisites: real copy core and retained target FDT.

Records controller inputs, not physical touch/brightness/timing success.
"""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tomllib

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
WORK=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root')
BASE=Path('/root/unixnu-build/UniXNU-sheng-base')
OUT=ROOT/'artifacts/venus-display-input-foundation';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(BASE/'scripts'))
from unixnu.devicetree import read_fdt
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,name):
    result=subprocess.run([str(v) for v in cmd],capture_output=True,text=True,timeout=180)
    (OUT/(name+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit(name+': '+result.stdout+result.stderr)
    return result.stdout
live_path=ROOT/'evidence/venus/20261025T020508Z/live.dtb'
assert sha(live_path)=='f0f1e0d1d9fc16ee520cceec87487523afc576cfb4b6b4f73ef58bc9ae3f3b2c'
live=read_fdt(live_path.read_bytes());nodes={};phandles={}
def walk(node,parent=''):
    path=parent+'/'+node.name if node.parent else ''
    nodes[path]=node
    for name in ('phandle','linux,phandle'):
        raw=node.properties.get(name)
        if raw:phandles[int.from_bytes(raw,'big')]=path
    for child in node.children:walk(child,path)
walk(live)
def cells(raw):return list(struct.unpack('>'+str(len(raw)//4)+'I',raw)) if len(raw)%4==0 else []
def entry(path,node,keys):
    properties={}
    string_keys={'compatible','label','interrupt-names','clock-names','fts,default-fw-name','fts,htp-fw-name',
                 'qcom,mdss-dsi-panel-name','qcom,mdss-dsi-panel-type',
                 'qcom,mdss-dsi-bl-pmic-control-type','qcom,bl-update-flag'}
    for key in keys:
        if key not in node.properties:continue
        raw=node.properties[key]
        if key in string_keys:value=node.strings(key)
        else:value=cells(raw) if raw else True
        properties[key]={'value':value,'hex':raw.hex()}
        if key.endswith(('-gpio','-supply')) or key in ('gpios','interrupt-parent','qcom,dsi-default-panel'):
            c=cells(raw)
            if c and c[0] in phandles:properties[key]['provider']=phandles[c[0]]
    return {'path':path,'enabled':node.enabled(),'properties':properties}
touch_path='/soc/spi@a8c000/fts@0';touch=nodes[touch_path]
assert touch.strings('compatible')==['st,spi']
assert cells(touch.properties['spi-max-frequency'])==[7000000]
assert cells(touch.properties['fts,x-max'])==[1440] and cells(touch.properties['fts,y-max'])==[3200]
touch_record=entry(touch_path,touch,('compatible','reg','interrupts','interrupt-parent','spi-max-frequency',
    'spi-cpol','spi-cpha','fts,irq-gpio','fts,reset-gpio','fts,x-max','fts,y-max',
    'fts,default-fw-name','fts,htp-fw-name','avdd-supply','avddold-supply','vdd-supply'))
bus=nodes['/soc/spi@a8c000']
bus_record=entry('/soc/spi@a8c000',bus,('compatible','reg','interrupts','interrupt-parent','clock-names','clocks',
    'qcom,clk-freq-out','qcom,master-id','qcom,slave-id','iommus','qcom,geni-se-id','qcom,wrapper-core'))
panel_keys=('qcom,mdss-dsi-panel-name','qcom,mdss-dsi-panel-type','qcom,dsi-default-panel',
    'qcom,mdss-dsi-bl-pmic-control-type','qcom,mdss-dsi-bl-min-level','qcom,mdss-dsi-bl-max-level',
    'qcom,mdss-brightness-max-level','qcom,mdss-dsi-bl-inverted-dbv','qcom,bl-update-flag',
    'qcom,mdss-dsi-panel-framerate','qcom,mdss-dsi-panel-width','qcom,mdss-dsi-panel-height',
    'qcom,platform-te-gpio','qcom,platform-reset-gpio','qcom,mdss-dsi-bpp')
default_panels={phandles[cells(node.properties['qcom,dsi-default-panel'])[0]] for node in nodes.values()
                if 'qcom,dsi-default-panel' in node.properties}
chosen=nodes.get('/chosen')
boot_tokens=[token for value in (chosen.strings('bootargs') if chosen else []) for token in value.split()
             if any(s in token.lower() for s in ('panel','dsi_display','display'))]
panels=[entry(path,node,panel_keys) for path,node in nodes.items()
        if any(k in node.properties for k in panel_keys) and
        ('mdss_dsi_k2' in path or 'qcom,dsi-default-panel' in node.properties or
         any(path==p or path.startswith(p+'/') for p in default_panels))]
button_keys=('compatible','label','reg','gpios','interrupts','interrupt-names','linux,code','debounce-interval',
    'qcom,pon-type','qcom,pull-up','qcom,support-reset','qcom,s1-timer','qcom,s2-timer','qcom,s2-type')
buttons=[entry(path,node,button_keys) for path,node in nodes.items()
         if any(s in path for s in ('/gpio_keys','/pon_hlos@1300','/pon@800','/pon_pbs@800'))]
gop=(WORK/'tree/drivers/GopFramebuffer').resolve()
reference=ROOT/'sources/UniXNU-guide/drivers/GopFramebuffer'
source_hashes={name:sha(gop/name) for name in ('NativeLegacyRequest.h','NativeLegacyDisplay.cpp','NativeGOPPresenter.cpp','NativeGOPWire.h')}
assert all(sha(reference/name)==digest for name,digest in source_hashes.items())
for name,test in (('request-state',gop/'Test/request-state.c'),('venus-frame',DEVICE/'tests/display_venus_frame.c')):
    run(['gcc','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fno-pie','-no-pie',
         '-fsanitize=address,undefined','-I',gop,test,'-o',OUT/name],name+'-build')
    run([OUT/name],name+'-test')
board=tomllib.loads((DEVICE/'board.toml').read_text());args=board['payload']['kernel_args']
assert {'offline-legacy-unit-scale=2','offline-legacy-cpu-present=1','sheng-fb-gpu=0','sheng-touch=0','sheng-backlight=0'}<=set(args)
report={'device':'venus','date':'2026-10-28','live_fdt_sha256':sha(live_path),'board_sha256':sha(DEVICE/'board.toml'),
    'copy_source_hashes':source_hashes,'copy_core_tests_passed':True,
    'display':{'width':1440,'height':3200,'stride_bytes':5760,'frame_bytes':18432000,
               'format':'BGRA8888 CPU/GOP path','software_scale':2,'logical_points':[720,1600],
               'requested_refresh_hz':int(next(a.split('=',1)[1] for a in args if a.startswith('sheng-vsync='))),
               'measured_refresh_hz':None,
               'known_os_frame_and_swap_verified':False,'panel_declarations':panels,
               'dt_default_panel_paths':sorted(default_panels),'retained_display_boot_tokens':boot_tokens},
    'input':{'touch':touch_record,'bus':bus_record,'button_declarations':buttons,
             'physical_input_verified':False},
    'remaining':['Verify active firmware panel mode and measured cadence rather than equating sheng-vsync with hardware refresh',
                 'Observe OS mode contract, a known CPU frame and swap retirement on Venus',
                 'Implement target DSI brightness, not Sheng KTZ8866 I2C control',
                 'Identify ST chip/firmware protocol and complete power/reset/GENI/IRQ ownership before physical reports',
                 'Map actual PMIC button ownership and press/release to HID'],
    'phone_operation_performed':False}
(DEVICE/'evidence/display-input-foundation.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: retained Venus touch/panel/button inputs decoded; current real CPU copy tests passed including 1440x3200')
print('Touch:',json.dumps(touch_record,ensure_ascii=False))
print('Physical touch, DSI brightness, measured refresh and OS frames/swaps remain unverified')
