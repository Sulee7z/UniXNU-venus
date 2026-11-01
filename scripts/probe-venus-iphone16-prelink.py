import json
import sys
from pathlib import Path

ROOT=Path('/mnt/g/UniXNU-Port')
sys.path.insert(0,str(ROOT/'sources/UniXNU-guide/kits/XnuPrelink'))
import native_prelink as n

missing={}
def collector(address, original_exports, native_by_name):
    names=original_exports.get(address,[])
    choices={new for name in names for new in native_by_name.get(name,set())}
    if len(choices)==1:return next(iter(choices))
    for name in names:missing[name]=missing.get(name,0)+1
    return address
n.unique_kernel_binding=collector
roots=['com.apple.filesystems.apfs','com.apple.driver.AppleMobileFileIntegrity','com.apple.iokit.IOStorageFamily','com.apple.kec.corecrypto']
try:
    report=n.plan((ROOT/'artifacts/venus-metal-touch/kernel-link-37/kernel.macho').read_bytes(),
                  (ROOT/'artifacts/venus-iphone-inputs/20H392/kernelcache.decompressed').read_bytes(),
                  roots,-0x1000000)
    ok=True;detail=None
except Exception as error:
    ok=False;detail=f'{type(error).__name__}: {error}'
(ROOT/'artifacts/venus-iphone16-prelink-probe').mkdir(parents=True,exist_ok=True)
(ROOT/'artifacts/venus-iphone16-prelink-probe/missing.json').write_text(json.dumps({'ok':ok,'detail':detail,'missing':missing},indent=2)+'\n')
print(json.dumps({'ok':ok,'detail':detail,'missing':missing},indent=2))
