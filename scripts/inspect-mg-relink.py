#!/usr/bin/env python3
"""Record existing native link inputs for a standalone activation rebuild."""
import hashlib
import json
from pathlib import Path
import shlex

ROOT=Path(__file__).resolve().parents[3]
TREE=Path('/root/unixnu-build/venus-legacy-full/venus/ipados-17.7.11-21H461/venus_ufs_root/tree')
OBJ=TREE/'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
LINK=OBJ/'mach.development.bcm2837.link'
OUT=ROOT/'artifacts/venus-mg-query-008/activation-inspection'
record={name:shlex.split((LINK/('mach.development.bcm2837.'+name)).read_text())
        for name in ('linkarguments','linkarchives')}
record['native_images']={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in OBJ.glob('mach*') if p.is_file()}
record['kernel_objects_archive_sha256']=hashlib.sha256((LINK/'mach.development.bcm2837.a').read_bytes()).hexdigest()
(OUT/'relink-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
