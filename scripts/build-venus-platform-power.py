#!/usr/bin/env python3
"""Adapt the pinned original-PMGR build recipe to Venus paths, retaining ABI gates."""
import hashlib
import json
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
reference = Path(os.environ.get('VENUS_PMGR_REFERENCE',
    '/mnt/g/UniXNU-Port/artifacts/venus-guide-virtual-timer/kernel/kernel.macho'))
kernelcache = Path(os.environ.get('UNIXNU_KERNELCACHE',
    '/mnt/g/UniXNU-Port/artifacts/venus-guide/ipsw/21H461/kernelcache.decompressed'))
recipe = Path('/mnt/g/UniXNU-Port/sources/UniXNU-sheng-reference/scripts/build-sheng-platform-power.py')
data = reference.read_bytes()
plan = json.loads(reference.with_suffix('.json').read_text())
if hashlib.sha256(data).hexdigest() != plan['candidate_sha256']:
    raise SystemExit('PMGR bootstrap reference does not match its prelink report')
code = recipe.read_text()
replacements = {
    "ROOT / 'kits/sheng/ShengPlatformPower.cpp'": "ROOT / 'kits/venus/ShengPlatformPower.cpp'",
    "ROOT / 'build/xnu-prelink/native-owner-ufs-rootauth3-candidate.macho'": f'Path({str(reference)!r})',
    "['python3', ROOT / 'scripts/audit-amfi-pmgr-contract.py']":
        f"['python3', ROOT / 'scripts/audit-amfi-pmgr-contract.py', '--candidate', {str(reference)!r}, '--kernelcache', {str(kernelcache)!r}]",
    "run(['llvm-objcopy', '--remove-section=__DATA,__mod_init_func',\n     '--globalize-symbol=__GLOBAL__sub_I_ShengPlatformPower.cpp', obj, late])":
        "run(['python3', ROOT / 'scripts/macho-late-init.py', obj, late, '--initializer', '__GLOBAL__sub_I_ShengPlatformPower.cpp'])",
}
for before, after in replacements.items():
    if code.count(before) != 1:
        raise SystemExit('Pinned PMGR recipe changed: ' + before)
    code = code.replace(before, after)
out = root / 'build/sheng-platform-power'
out.mkdir(parents=True, exist_ok=True)
(out / 'venus-inputs.json').write_text(json.dumps({'reference_sha256': plan['candidate_sha256'],
    'reference_kernelcache_sha256': plan['original_sha256'],
    'reference_recipe_sha256': hashlib.sha256(recipe.read_bytes()).hexdigest(),
    'reference_repository_revision': '0e1f6e52638137db15905db8d775ad73757f39fa',
    'host_recipe_replacements': replacements, 'mmio_backend_provided': False}, indent=2) + '\n')
exec(compile(code, str(recipe), 'exec'), {'__name__': '__main__', '__file__': str(root / 'scripts/build-venus-platform-power.py')})
