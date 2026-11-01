#!/usr/bin/env python3
"""Cross-build the actual zeta-derived Metal runtime C ABI for iPadOS17."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path('/mnt/g/UniXNU-Port');WORK=Path('/root/unixnu-build/venus-metal-work-r5')
SOURCE=WORK/'metal2vulkan';METAL=WORK/'AdrenoMetal';OUT=WORK/'bridge-build';OUT.mkdir(exist_ok=True)
TOOLS=Path('/root/unixnu-build/venus-metal-tools');RUST=TOOLS/'rust-1.98';SDK=TOOLS/'sdks/iPhoneOS16.5.sdk'
LLVM=TOOLS/'llvm21';LLVM_ENV={**os.environ,'LD_LIBRARY_PATH':str(LLVM/'usr/lib/x86_64-linux-gnu')}
if not (SDK/'usr/include').is_dir():raise ValueError('Header/stub SDK missing')
air=OUT/'runtime_examples.air';fc=OUT/'function_constant.air'
for source,target in ((SOURCE/'crates/metal2vulkan-validation/fixtures/public/examples/runtime_examples.ll',air),
                      (SOURCE/'crates/metal2vulkan-validation/fixtures/public/kernel_function_constant_gate_fold.ll',fc)):
    result=subprocess.run([str(LLVM/'usr/lib/llvm-21/bin/llvm-as'),str(source),'-o',str(target)],env=LLVM_ENV,capture_output=True,text=True,timeout=90)
    if result.returncode:raise SystemExit(result.stderr)
manifest=OUT/'Cargo.toml'
manifest.write_text('\n'.join(['[package]','name = "venus-native-metal-bridge"','version = "0.1.0"','edition = "2024"','rust-version = "1.98"','[workspace]',
    '[lib]','crate-type = ["staticlib"]','path = '+json.dumps(str(METAL/'bridge/NativeMetalBridge.rs')),
    '[dependencies]','metal2vulkan = { path = '+json.dumps(str(SOURCE/'crates/metal2vulkan'))+', features = ["ash"] }',
    'metal2vulkan-runtime = { path = '+json.dumps(str(SOURCE/'crates/metal2vulkan-runtime'))+' }','libc = "0.2"','sha2 = { version = "0.10", features = ["asm"] }',
    '[profile.release]','panic = "unwind"','debug = 1',''])+'\n')
env={**os.environ,'PATH':str(RUST/'bin')+':'+os.environ['PATH'],'CARGO_HOME':str(TOOLS/'cargo-home'),
    'NMB_FIXTURE_AIR':str(air),'NMB_FC_AIR':str(fc),'IPHONEOS_DEPLOYMENT_TARGET':'17.0','SDKROOT':str(SDK),
    'CC_aarch64_apple_ios':'/root/unixnu-toolchain/llvm/bin/clang',
    'CFLAGS_aarch64_apple_ios':'-target arm64-apple-ios17.0 -isysroot '+str(SDK)}
command=[str(RUST/'bin/cargo'),'build','--release','--manifest-path',str(manifest),'--target','aarch64-apple-ios','--target-dir',str(WORK/'cargo-target')]
log=OUT/'build-ios.log'
with log.open('w') as stream:result=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=1800)
if result.returncode:print('FAILED; read',log);raise SystemExit(result.returncode)
library=WORK/'cargo-target/aarch64-apple-ios/release/libvenus_native_metal_bridge.a'
record={'library':str(library),'bytes':library.stat().st_size,'sha256':hashlib.sha256(library.read_bytes()).hexdigest(),
    'target':'aarch64-apple-ios17.0','rust_version':subprocess.check_output([str(RUST/'bin/rustc'),'--version'],text=True).strip(),
    'header_sdk':'iPhoneOS16.5 headers/stubs; deployment17.0; runtime original17 frameworks',
    'source_receipt':str(WORK/'source-receipt.json'),'command':command,'scope':'Built real Metal runtime/static C ABI; no device rendering test.'}
(OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
