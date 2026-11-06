"""Generate pinned inputs, compile/link own host code, run bounded test only."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv: list[str], timeout: int = 30) -> dict:
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True, timeout=timeout)
    return {"argv": argv, "exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def main() -> None:
    runs = []
    runs.append(run([sys.executable, "gen_inputs.py"]))
    runs.append(run([sys.executable, "audit.py"]))
    runs.append(run(["clang++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                     "veneer.cpp", "test_veneer.cpp", "-o", "veneer_host_test"]))
    if any(r["exit"] for r in runs):
        raise SystemExit("\n".join(str(r) for r in runs))
    runs.append(run(["./veneer_host_test", "genuine-input.bin"], 10))
    runs.append(run(["./veneer_host_test", "--trigger-unsupported"], 10))
    if runs[-2]["exit"] != 0 or runs[-1]["exit"] != 86 or \
       "FX6_BRIDGE_UNSUPPORTED_CALLBACK_SLOT=0" not in runs[-1]["stderr"]:
        raise SystemExit("host positive or nonreturning negative test failed: " + str(runs[-2:]))
    names = ("gen_inputs.py", "audit.py", "veneer.hpp", "veneer.cpp", "test_veneer.cpp",
             "build_and_test.py", "callback_map.hpp", "genuine-input.bin", "evidence.json",
             "veneer_host_test", "README.md")
    receipt = {"evidence_level": "pinned-original static analysis and own host compiled/linked tests only",
               "source_and_output_sha256": {n: sha(HERE/n) for n in names}, "runs": runs,
               "result": "host mapping and rejection fixtures pass; original Sony function not executed"}
    (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(receipt["result"])


if __name__ == "__main__":
    main()
