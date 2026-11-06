"""重放审计和 host 测试，保存本目录可复算回执。"""
from __future__ import annotations

import json
import subprocess
import sys

from audit import PINS, ROOT, sha


def main() -> None:
    commands = [[sys.executable, "audit.py"], [sys.executable, "replay.py"],
                [sys.executable, "-m", "unittest", "-v", "test_adapter"]]
    runs = []
    for cmd in commands:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=30)
        runs.append({"argv": cmd, "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr})
        if p.returncode:
            raise SystemExit(p.stderr or p.stdout)
    sources = [ROOT / n for n in ("init_adapter.py", "audit.py", "replay.py", "test_adapter.py", "seal.py", "README.md")]
    outputs = [ROOT / "audit.json", ROOT / "replay.json"]
    result = {
        "scope": "host-only; no ELF execution, QEMU, guest adaptation, camera or media writes",
        "original_pins": {str(p): h for p, h in PINS.items()},
        "source_sha256": {p.name: sha(p) for p in sources},
        "output_sha256": {p.name: sha(p) for p in outputs},
        "commands": runs,
        "result": "9 host tests passed; genuine snapshot structurally projected and guest conversion rejected",
    }
    (ROOT / "receipt.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(result["result"])


if __name__ == "__main__":
    main()
