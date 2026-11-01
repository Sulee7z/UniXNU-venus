#!/usr/bin/env python3
"""Extract the pinned25F84 KDK executable providers for native prelink ABI audits."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

BASE = Path('/root/unixnu-build/zeta-venus-wsl/zeta/tree')
OUT = Path('/root/unixnu-build/venus-ios26-kdk')
PIN = 'faef4393becf65c88a2791770904909babf1826d23d2ea478bf878a6417851ab'


def main():
    source = BASE / 'scripts/kdk-headers.py'
    spec = importlib.util.spec_from_file_location('kdk_archive', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    dmg = BASE / '.cache/kdk/Kernel_Debug_Kit_26.5.2_build_25F84.dmg'
    if module.sha256(dmg) != PIN:
        raise RuntimeError('KDK source checksum differs')
    if not OUT.parent.is_dir():
        raise RuntimeError('Missing build parent')
    OUT.mkdir(exist_ok=True)
    receipt = OUT / 'providers.json'
    if receipt.exists():
        record = json.loads(receipt.read_text())
        if record['source_sha256'] != PIN:
            raise RuntimeError('KDK extraction belongs to another source')
        print('KDK providers already extracted:', receipt)
        return
    with tempfile.TemporaryDirectory(prefix='extract-', dir=OUT) as temporary:
        package = module.copy_pkg(dmg, Path(temporary))
        entries = module.xar_entries(package)
        offset, length, encoding = entries['KDK.pkg/Payload']
        if encoding != 'application/octet-stream':
            raise RuntimeError('Unexpected KDK payload encoding')
        with package.open('rb') as stream:
            stream.seek(offset)
            count = module.extract_cpio(module.Stream(module.pbzx_chunks(stream, length)),
                ('System/Library/Extensions/', 'System/Library/Kernels/'), OUT)
    if not count or not (OUT / 'System/Library/Extensions/apfs.kext/Contents/Info.plist').exists():
        raise RuntimeError('KDK has no extracted APFS provider')
    record = dict(source_sha256=PIN, extraction_script_sha256=module.sha256(source),
                  files=count, files_sha256={str(path.relative_to(OUT)): module.sha256(path)
                      for root in ('System/Library/Extensions', 'System/Library/Kernels')
                      for path in sorted((OUT / root).rglob('*')) if path.is_file()},
                  runtime_verified=False)
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    print(f'PASS:{count} KDK provider files extracted with source SHA verified')


if __name__ == '__main__':
    main()
