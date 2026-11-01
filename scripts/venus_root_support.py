"""Build the real iOS17 root-policy/Virtio/RamBlock providers and one storage alias set."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

def build(ctx, env, out):
    root = Path('/mnt/g/UniXNU-Port')
    upstream = root / 'sources/UniXNU-guide'
    deployment = root / 'artifacts/venus-deployment'
    image = json.loads((deployment / 'unixnu-root.json').read_text())
    def sha(path):
        with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
    if sha(Path(image['image'])) != image['image_sha256'] or not image['native_c_signatures_and_all_blocks_verified']:
        raise SystemExit('Root image must be fully verified first')
    support = out / 'support'; support.mkdir(exist_ok=True)
    objroot = ctx.tree / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
    cpp = json.loads((objroot / 'iokit/DEVELOPMENT/IOPlatformExpert.cpo.json').read_text().strip().rstrip(','))
    c = json.loads((objroot / 'bsd/DEVELOPMENT/bsd_init.o.json').read_text().strip().rstrip(','))
    kit = upstream / 'kits/VerifiedRoot'
    def compile(source, destination, record, extra=()):
        command = []; i = 0; original = record['arguments']
        while i < len(original):
            arg = original[i]
            if arg == record['file']: command.append(str(source))
            elif arg == '-o': command += ['-o', str(destination)]; i += 1
            elif arg in ('-MF','-MJ','-MT','-MQ'): i += 1
            elif arg == '-Xclang' and original[i+1].startswith('-W'): i += 1
            elif arg not in ('-MD','-MMD','-MP') and not arg.startswith('-W'): command.append(arg)
            i += 1
        command += ['-I', str(kit/'include'), '-I', str(ctx.tree/'build/storage-abi/include'),
                    '-I', str(ctx.tree/'.cache/xnu-work/osfmk'), '-mgeneral-regs-only',
                    '-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-c99-designator',
                    '-Wno-reorder-init-list','-Wno-deprecated-enum-enum-conversion','-Wno-unnecessary-virtual-specifier', *extra]
        result = subprocess.run(command, cwd=record['directory'], env=env, capture_output=True, text=True)
        destination.with_suffix('.log').write_text(result.stdout + result.stderr)
        if result.returncode: raise SystemExit('Root support compile failed: ' + str(destination.with_suffix('.log')))
    objects = {}
    for name, filename, flags in [
        ('VirtioMmioBlock','NativeVirtioBlock', ['-DNATIVE_VERIFIED_BLOCK=1','-DNATIVE_VERIFIED_BLOCK_MULTI_POLICY=1']),
        ('RamBlock','NativeRamBlock', []),
    ]:
        directory = support / name; directory.mkdir(exist_ok=True)
        obj = directory / (filename+'.o')
        compile(upstream/'drivers'/name/(filename+'.cpp'), obj, cpp, flags)
        subprocess.run(['python3', ctx.tree/'scripts/build-virtio-mmio-bindings.py', '--component', name,
                        '--directory', directory], env=env, check=True)
        objects[name] = obj
    # One exact absolute-alias object for all three concrete subclasses.
    records = {'ShengUfs': json.loads((out/'bindings.json').read_text())}
    for name in objects: records[name] = json.loads((support/name/'bindings.json').read_text())
    bindings = {}
    for record in records.values():
        for name, address in record['bindings'].items():
            if name in bindings and bindings[name] != address: raise SystemExit('Storage aliases disagree')
            bindings[name] = address
    assembly = support/'storage-bindings.S'
    assembly.write_text(''.join(f'.globl {name}\n.set {name}, {address}\n' for name,address in sorted(bindings.items())))
    alias = support/'storage-bindings.o'
    subprocess.run(['xcrun','clang','-target','arm64-apple-ios17.0','-c',assembly,'-o',alias], env=env, check=True)
    def archive(path, members):
        path.unlink(missing_ok=True)
        subprocess.run(['xcrun','ar','rcs',path,*members], env=env, check=True)
    archive(out/'libShengUfs.a', [out/'NativeUfs.o'])
    archive(support/'VirtioMmioBlock/libVirtioMmioBlock.a', [objects['VirtioMmioBlock'], alias])
    archive(support/'RamBlock/libRamBlock.a', [objects['RamBlock'], alias])
    # The official linker uses NativeRamBlock.o when Virtio is present, with
    # the audited alias subset checked against this consolidated record.
    virtual = records['VirtioMmioBlock']
    virtual['bindings'] = bindings
    virtual['shared_alias_consumers'] = {name: r['compiled_object_sha256'] for name,r in records.items()}
    (support/'VirtioMmioBlock/bindings.json').write_text(json.dumps(virtual, indent=2)+'\n')
    verified = support/'VerifiedRoot'; verified.mkdir(exist_ok=True)
    compiled = []
    for source in (kit/'src/verified_root.c', kit/'adapters/xnu_crypto.c', upstream/'scripts/qemu-entry/verified-root-probe.c'):
        obj = verified/(source.stem+'.o'); compile(source,obj,c); compiled.append(obj)
    windows = image['windows']
    key = deployment/'OS-policy/trusted-key.bin'
    if sha(key) != image['owner_anchor_sha256']: raise SystemExit('Owner key mismatch')
    samples = verified/'samples.bin'
    size = windows[0]['size']; count = (size+4095)//4096
    indices = [0,1,count//2,count-1]; lengths = [min(4096,size-index*4096) for index in indices]
    with Path(windows[0]['path']).open('rb') as source, samples.open('wb') as target:
        for index,length in zip(indices,lengths): source.seek(index*4096); target.write(source.read(length))
    text = '.section __DATA_CONST,__const\n.balign 8\n'
    for name, path in [('verified_root_manifest',windows[0]['policy_path']),
                       ('verified_root_systemos_manifest',windows[1]['policy_path']), ('verified_root_key',str(key))]:
        text += f'.globl _{name}\n_{name}:\n.incbin "{path}"\n.balign 8\n'
    for name, values in [('verified_root_manifest_bytes',[windows[0]['policy_bytes']]),
                         ('verified_root_sample_indices',indices), ('verified_root_sample_lengths',lengths)]:
        text += f'.globl _{name}\n_{name}:\n.quad '+','.join(map(str,values))+'\n'
    text += '.globl _verified_root_samples\n_verified_root_samples:\n.incbin "'+str(samples)+'"\n.balign 8\n'
    text += '.globl _verified_root_policies\n_verified_root_policies:\n'
    text += f'.quad _verified_root_manifest, {windows[0]["policy_bytes"]}\n.quad _verified_root_systemos_manifest, {windows[1]["policy_bytes"]}\n'
    text += '.globl _verified_root_policy_count\n_verified_root_policy_count:\n.quad 2\n'
    inputs = verified/'inputs.S'; inputs.write_text(text)
    subprocess.run(['xcrun','clang','-target','arm64-apple-ios17.0','-c',inputs,'-o',verified/'inputs.o'], env=env, check=True)
    archive(verified/'libVerifiedRootProbe.a', [*compiled,verified/'inputs.o'])
    files = {str(path.relative_to(support)): sha(path) for path in support.rglob('*')
             if path.is_file() and path.suffix in ('.a','.o','.json')}
    result = {'files':files,'owner_anchor_sha256':image['owner_anchor_sha256'],
              'root_image_sha256':image['image_sha256'],'windows':windows,
              'verified_root_revision':subprocess.check_output(['git','-C',kit,'rev-parse','HEAD'],text=True).strip(),
              'policy_sources':'actual full owner-signed OS/SystemOS policies, not synthetic stubs'}
    (out/'root-support.json').write_text(json.dumps(result, indent=2)+'\n')
    return support, result
