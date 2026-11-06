"""只在本目录重建回执；不调用 ELF、QEMU 或设备。"""
import json
import subprocess
import sys
from pathlib import Path

import audit


def main():
    audit.main()
    here = Path(__file__).resolve().parent
    proc = subprocess.run([sys.executable, "-B", "-m", "unittest", "-v", "test_adapter.py"],
                          cwd=here, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=True)
    if "Ran 5 tests" not in proc.stdout or "OK" not in proc.stdout:
        raise ValueError("host test receipt mismatch")
    receipt = {
        "result": "PASS_PINNED_HOST_STATIC_AND_BYTE_FIXTURES",
        "scope": "no_new_vm_no_guest_execution_no_device",
        "original_instruction_count": 91,
        "host_tests": 5,
        "test_output": proc.stdout,
        "files_sha256": {p.name: audit.digest(p) for p in
                         (here / "adapter.py", here / "audit.py", here / "test_adapter.py",
                          here / "seal.py", here / "README.md", here / "evidence.json")},
        "prior_vm_run_consumed": "mpr-ro-b22ccc48",
        "natural_movie_events_observed": False,
        "native_movie_callback_adapter_ready": False,
    }
    (here / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(receipt["result"], "5 tests, 91 pinned words")


if __name__ == "__main__":
    main()
