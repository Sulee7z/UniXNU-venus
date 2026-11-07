#!/usr/bin/env python3
"""Validate the immutable storage header closure before the aggregate source build."""
import os
from pathlib import Path
import subprocess
import sys
import tomllib

value = os.environ.get('XNU_REPRO_CONFIG')
if not value:
    raise ValueError('The selected source-replay configuration is required')
marker = Path(value).resolve()
document = tomllib.loads(marker.read_text())
repo = (marker.parent / document['device_directory']).resolve()
manifest = repo / document['source_manifest']
subprocess.run([sys.executable, '-B', str(repo / 'repro/check_source.py'), str(manifest.parent)], check=True)
print('Pinned public and adapted storage headers belong to the verified source closure')
