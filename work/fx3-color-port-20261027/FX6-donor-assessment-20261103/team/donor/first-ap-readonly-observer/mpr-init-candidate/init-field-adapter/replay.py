"""把一次真实参数快照投影为可审计 JSON，不生成 guest payload。"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from audit import OBS, ROOT, sha, PINS
from init_adapter import project


def genuine() -> bytes:
    if sha(OBS) != PINS[OBS]:
        raise ValueError("prior VM receipt drift")
    records = json.loads(OBS.read_text())["records"]
    call = next(r for r in records if r["kind"] == "call")
    return bytes.fromhex(call["parameter_0x290_hex"])


def main() -> None:
    p = project(genuine())
    out = dataclasses.asdict(p)
    out["preview_0x1f8"] = None
    out["evidence_level"] = "prior real snapshot input, host-only structural projection, rejected guest conversion"
    (ROOT / "replay.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"count": p.count, "slots": p.slots, "common_nonnull": sum(not r["source_null"] for r in p.callback_rows),
                      "extra_nonnull": len(p.fx6_extra_nonnull), "reject_reasons": len(p.rejected),
                      "preview": p.preview_0x1f8 is not None}, ensure_ascii=False))


if __name__ == "__main__":
    main()
