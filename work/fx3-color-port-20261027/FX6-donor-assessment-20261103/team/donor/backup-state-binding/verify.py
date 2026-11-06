#!/usr/bin/env python3
"""Dependency-free cross-check of the immutable inputs and this stage's receipts."""
import hashlib
import json
from pathlib import Path

from parse_bk4 import SOURCES, read_record
from inspect_history import SOURCES as HISTORY

HERE=Path(__file__).resolve().parent
FILES=["bk4-receipt.json","history-receipt.json","search-replay.json","static-receipt.json","parse_bk4.py","inspect_history.py","replay_search.py","analyze_static.py","verify.py","prepare.sh","README.md"]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    bk=json.loads((HERE/"bk4-receipt.json").read_text())
    hist=json.loads((HERE/"history-receipt.json").read_text())
    replay=json.loads((HERE/"search-replay.json").read_text())
    static=json.loads((HERE/"static-receipt.json").read_text())
    assert replay["status"]==static["status"]=="PASS"
    assert len(replay["cases"])==4
    assert len(static["av"]["send_common_direct_callers"])==len(static["fx3_av"]["send_common_direct_callers"])==6
    assert static["limited_id_writer_scan"]["ap_elfs_scanned"]==363
    assert not static["limited_id_writer_scan"]["ap_hits"]
    for name,(path,expected) in SOURCES.items():
        assert sha(path)==expected==bk["sources"][name]["sha256"]
        data=path.read_bytes()
        for r in bk["sources"][name]["records"]:
            live,_=read_record(data,r["record_file_offset"])
            assert live==r and live["selected"]["length"]==1 and live["selected"]["raw_hex"]=="00"
    for name,(path,expected) in HISTORY.items():
        assert sha(path)==expected==hist["sources"][name]["sha256"]
        data=path.read_bytes()
        for r in hist["sources"][name]["records"]:
            live,_=read_record(data,r["record_file_offset"],require_checksum=False)
            assert live==r and live["selected"]["raw_hex"]=="00"
    for c in replay["cases"]:
        assert c["positive"]["returned_x0"]>0 and c["size"]["returned_x0"]==1
        assert all(c[k]["returned_x0"]==0 for k in ("missing_subsystem","missing_unit","sentinel"))
        for k in ("positive","size","missing_subsystem","missing_unit","sentinel"):
            assert c[k]["instruction_count"]<=c[k]["budget"] and not c[k]["writes"]
    for model in ("fx6","fx3"):
        assert sha(Path(static["backup_modules"][model]["path"]))==static["backup_modules"][model]["sha256"]
    assert sha(Path(static["av"]["path"]))==static["av"]["sha256"]
    assert sha(Path(static["fx3_av"]["path"]))==static["fx3_av"]["sha256"]
    assert sha(Path(static["liro"]["path"]))==static["liro"]["sha256"]
    out={"status":"PASS","evidence_levels":["original static bytes","isolated CPU Data_SearchId/Data_GetSize","historical FX3 VM RAM, read-only, not natural FX6 runtime"],"checked_pinned_default_files":len(SOURCES),"checked_historical_ram_files":len(HISTORY),"original_cpu_cases":len(replay["cases"]),"negative_lookup_branches":3*len(replay["cases"]),"event_producer_direct_calls_FX6":6,"event_producer_direct_calls_FX3":6,"output_files":{name:sha(HERE/name) for name in FILES},"device_or_VM_operations":0}
    print(json.dumps(out,indent=2))


if __name__=="__main__":main()
