#!/usr/bin/env python3
from pathlib import Path
import os
import shutil

WORK = Path("/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024")
STAGE278 = WORK / "stage278-bounded-header-failure-localization"
STAGE283 = WORK / "stage283-post-stop-096f-transition-compatibility"


def main():
    if STAGE283.exists():
        shutil.rmtree(STAGE283)
    STAGE283.mkdir(mode=0o700, parents=True, exist_ok=True)
    (STAGE283 / "artifacts").mkdir(mode=0o755, exist_ok=True)

    skip_ext = {".json", ".md"}
    skip_dirs = {"artifacts", "runs", "__pycache__"}
    for item in STAGE278.iterdir():
        if item.name in skip_dirs or item.suffix in skip_ext:
            continue
        if item.is_file():
            shutil.copy2(item, STAGE283 / item.name)

    print("Copied Stage 278 source baseline to Stage 283.")


if __name__ == "__main__":
    main()
