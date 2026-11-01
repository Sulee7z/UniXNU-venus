#!/usr/bin/env python3
"""Keep the QEMU DT parser's bound consistent with the actual DarwinBoot loader."""
from pathlib import Path
source=Path('/root/unixnu-build/venus-guide-out/venus/ipados-17.7.11-21H461/venus/tree/scripts/qemu-entry/make-dt.py')
loader=Path('/mnt/g/UniXNU-Port/sources/UniXNU-guide/drivers/DarwinBoot/DarwinBootPkg/Driver/WindowSize.h')
assert 'size <= 0x200000000ULL' in loader.read_text()
code=source.read_text()
old='args.owned_memory_size <= 0x100000000'
assert code.count(old)==1
code=code.replace(old,'args.owned_memory_size <= 0x200000000').replace('256 MiB to 4 GiB','256 MiB to 8 GiB')
exec(compile(code,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})
