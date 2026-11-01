#!/usr/bin/env python3
"""Execute actual native Metal runtime/AIR C ABI over host software Vulkan."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
ROOT=Path('/mnt/g/UniXNU-Port');WORK=Path('/root/unixnu-build/venus-metal-work-r5');TOOLS=Path('/root/unixnu-build/venus-metal-tools');RUST=TOOLS/'rust-1.98'
OUT=ROOT/'artifacts/venus-metal13/runtime-host-r2';OUT.mkdir(exist_ok=False)
env={**os.environ,'PATH':str(RUST/'bin')+':'+os.environ['PATH'],'CARGO_HOME':str(TOOLS/'cargo-home'),
    'NMB_FIXTURE_AIR':str(WORK/'bridge-build/runtime_examples.air'),'NMB_FC_AIR':str(WORK/'bridge-build/function_constant.air')}
with (OUT/'cargo.log').open('w') as log:
    result=subprocess.run([str(RUST/'bin/cargo'),'build','--release','--manifest-path',str(WORK/'bridge-build/Cargo.toml'),
        '--target','x86_64-unknown-linux-gnu','--target-dir',str(WORK/'cargo-target')],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
if result.returncode:print('FAILED; read',OUT/'cargo.log');raise SystemExit(result.returncode)
library=WORK/'cargo-target/x86_64-unknown-linux-gnu/release/libvenus_native_metal_bridge.a';binary=OUT/'bridge-smoke'
result=subprocess.run(['g++','-std=c++17','-O2','-I',str(WORK/'AdrenoMetal/bridge'),str(WORK/'AdrenoMetal/bridge/bridge_smoke.cpp'),str(ROOT/'ports/UniXNU-venus/tests/metal_host_coherent_cache.cpp'),str(library),'-ldl','-lpthread','-lm','-o',str(binary)],capture_output=True,text=True,timeout=180)
(OUT/'link.log').write_text(result.stdout+result.stderr)
if result.returncode:raise SystemExit(result.stderr)
cache=OUT/'cache';cache.mkdir();result=subprocess.run([str(binary),'/usr/lib/x86_64-linux-gnu/libvulkan.so.1',str(cache)],env=env,capture_output=True,text=True,timeout=300)
(OUT/'run.log').write_text(result.stdout+result.stderr)
record={'runtime_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'result':result.stdout,'returncode':result.returncode,
        'scope':'Actual AIR/Metal runtime C API execution on host software Vulkan; not phone/A660/Objective-C discovery qualification.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if result.returncode:raise SystemExit(result.returncode)
