#!/usr/bin/env python3
"""Fetch the pinned iPad7,1 21H461 kernelcache through the official IPSW range path."""
import hashlib
import shutil
import sys
from pathlib import Path
sys.path.insert(0,'/mnt/g/UniXNU-Port/sources/UniXNU-guide/scripts')
from unixnu.cli import parser
from unixnu.config import Context
from unixnu import ipsw
ctx=Context(parser().parse_args(['status','-D','/mnt/g/UniXNU-Port/ports/UniXNU-venus','--out','/root/unixnu-build/venus-legacy-full']))
if not ctx.board.get('ipsw'):raise SystemExit('Board/profile has no IPSW input')
source=ipsw.Ipsw(ctx)
path=Path(ipsw.kernelcache(ctx,source));expected='f18b4df865405f2a287b84977d7aca745e056d656d9fc9df1662970ce2969de7'
digest=hashlib.sha256(path.read_bytes()).hexdigest()
if digest!=expected:raise SystemExit('Unexpected kernelcache sha256 '+digest)
destination=Path('/mnt/g/UniXNU-Port/artifacts/venus-guide/ipsw/21H461/kernelcache.decompressed')
destination.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(path,destination)
print(str(destination))
print(digest)
