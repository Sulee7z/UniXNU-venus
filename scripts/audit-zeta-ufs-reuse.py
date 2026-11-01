#!/usr/bin/env python3
"""Compare zeta's SM8350 transport inputs with the retained Venus FDT/vendor source."""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

root = Path('/mnt/g/UniXNU-Port')
sys.path.insert(0, str(root / 'sources/UniXNU-guide/scripts'))
from unixnu.devicetree import read_fdt, registers

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

live = root / 'evidence/venus/20261025T020508Z/live.dtb'
if sha(live) != 'f0f1e0d1d9fc16ee520cceec87487523afc576cfb4b6b4f73ef58bc9ae3f3b2c':
    raise SystemExit('Unexpected target FDT')
nodes = list(read_fdt(live.read_bytes()).walk())
host = next(n for n in nodes if n.name == 'ufshc@1d84000')
phy = next(n for n in nodes if n.name == 'ufsphy_mem@1d87000')
archive = root / 'downloads/venus-kernel-df169d0b934bd8e372c5c5e2ffab5f9c50f3d052.zip'
if sha(archive) != '9bab05ab7205d6524d3c96b98501ffc3435634291093fefef28d8965d661ed91':
    raise SystemExit('Vendor source archive hash differs')
out = root / 'diagnostics/venus-zeta-reference'
out.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(archive) as source:
    files = [n for n in source.namelist() if n.endswith('/gcc-lahaina.c')]
    if len(files) != 1:
        raise SystemExit('Expected one pinned gcc-lahaina.c')
    raw = source.read(files[0])
(out / 'gcc-lahaina.c').write_bytes(raw)
text = raw.decode()
expected = {'gcc_ufs_phy_axi_clk': 0x77010, 'gcc_ufs_phy_ahb_clk': 0x77018,
            'gcc_ufs_phy_unipro_core_clk': 0x7705c, 'gcc_aggre_ufs_phy_axi_clk': 0x770cc}
clocks = {}
for name, offset in expected.items():
    block = re.search(r'static struct clk_branch\s+' + name + r'\s*=\s*\{(.*?)\n\};', text, re.S)
    if not block:
        raise SystemExit('Clock definition missing: ' + name)
    values = {key: int(value, 16) for key, value in re.findall(r'\.(halt_reg|enable_reg)\s*=\s*(0x[0-9a-fA-F]+)', block[1])}
    if values.get('halt_reg') != offset or values.get('enable_reg') != offset:
        raise SystemExit('Clock register mismatch: ' + name)
    clocks[name] = values
patch = root / 'sources/UniXNU-zeta-core/patches/drivers/NativeUfs-sm8350.patch'
result = {'zeta_device_revision': '825d75028a3aefc2035164591ba9074837e39979',
          'zeta_core_revision': '68c513467bb6c44106c053c410582c1d14f96dd7',
          'zeta_sm8350_patch_sha256': sha(patch),
          'venus_vendor_revision': 'df169d0b934bd8e372c5c5e2ffab5f9c50f3d052',
          'vendor_clock_source': files[0], 'vendor_clock_source_sha256': hashlib.sha256(raw).hexdigest(),
          'live_fdt_sha256': sha(live), 'ufs_registers': registers(host), 'phy_registers': registers(phy),
          'ufs_compatible': host.strings('compatible'), 'phy_compatible': phy.strings('compatible'),
          'interrupts': host.cells('interrupts'), 'iommus': host.cells('iommus'), 'clock_offsets': clocks,
          'same_primary_host': registers(host)[0] == (0x1d84000, 0x3000),
          'same_phy': registers(phy) == [(0x1d87000, 0xe10)],
          'same_interrupt': host.cells('interrupts') == [0, 265, 4],
          'same_stream_id': len(host.cells('iommus')) >= 2 and host.cells('iommus')[1] == 0xe0,
          'runtime_ufs_qualified': False,
          'limits': ['Zeta storage builder targets XNU 12377/iOS26; Venus uses XNU10063/iPadOS17.',
                     'Only resource/source compatibility is checked, not live clocks, SMMU ownership or DMA.',
                     'Do not import zeta LUN/GPT/volume UUIDs or fixed firmware queue addresses.',
                     'Port the transport against the selected storage ABI; avoid duplicate IOStorageFamily implementations.']}
(root / 'ports/UniXNU-venus/evidence/zeta-ufs-reuse.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
