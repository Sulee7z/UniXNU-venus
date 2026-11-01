#!/usr/bin/env python3
"""Retain pinned vendor touch/pinctrl references for the source-only audit."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
PIN = "df169d0b934bd8e372c5c5e2ffab5f9c50f3d052"
BASE = f"https://raw.githubusercontent.com/Evolution-X-Devices/kernel_xiaomi_venus/{PIN}/"
FILES = [
    "drivers/input/touchscreen/fts_spi/fts.c",
    "drivers/input/touchscreen/fts_spi/fts_lib/ftsHardware.h",
    "drivers/input/touchscreen/fts_spi/fts_lib/ftsSoftware.h",
    "drivers/input/touchscreen/fts_spi/fts_lib/ftsCore.c",
    "drivers/input/touchscreen/fts_spi/fts_lib/ftsIO.c",
    "drivers/pinctrl/qcom/pinctrl-msm.c",
    "drivers/pinctrl/qcom/pinctrl-lahaina.c",
]

def main():
    out = ROOT / "artifacts/venus-touch-audit-035/vendor"
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for name in FILES:
        target = out / name
        if not target.exists():
            request = urllib.request.Request(BASE + name, headers={"User-Agent": "UniXNU-venus-source-audit"})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                raise ValueError("Oversized reference: " + name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        data = target.read_bytes()
        records.append({"path": name, "url": BASE + name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    (out / "manifest.json").write_text(json.dumps({"commit": PIN, "files": records}, indent=2) + "\n", encoding="utf-8")
    print(f"Retained {len(records)} pinned vendor references at {out}")

if __name__ == "__main__":
    main()
