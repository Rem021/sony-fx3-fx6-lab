#!/usr/bin/env python3
"""Optional read-only public-source refresh. Saves metadata, not vendor code.

Not run by build_and_test.py: normal verification is fully offline.
"""
import datetime
import hashlib
import json
import subprocess
from resource_tools import ROOT, MAC

SOURCES = [
    ("Sony public Linux header", "DavidBuchanan314/Sony-ILCE-7M4-Linux", "fa5c6f6aba58f675691e5adf291b155b76e6e93e", "linux-kernel/include/linux/lz77.h", "Sony copyright; Dual BSD/GPL source"),
    ("Sony public Linux decoder", "DavidBuchanan314/Sony-ILCE-7M4-Linux", "fa5c6f6aba58f675691e5adf291b155b76e6e93e", "linux-kernel/lib/lz77/lz77_inflate.c", "Sony copyright; Dual BSD/GPL source"),
    ("Sony public Linux encoder", "DavidBuchanan314/Sony-ILCE-7M4-Linux", "fa5c6f6aba58f675691e5adf291b155b76e6e93e", "linux-kernel/lib/lz77/lz77_deflate.c", "Sony copyright; Dual BSD/GPL source"),
    ("fwtool Python decoder", "ma1co/fwtool.py", "cdba742b73eed5981480c326aeb30033aabf0223", "fwtool/lz77/__init__.py", "MIT"),
    ("A7C2 bounded C implementation", "chocotan/a7c2-qemu", "b3d7c1fed349f1d918acc4259f1d2b3a7c52a500", "runtime/analysis/sony-lz77.c", "MIT attribution to ma1co in source"),
    ("A7C2 interface", "chocotan/a7c2-qemu", "b3d7c1fed349f1d918acc4259f1d2b3a7c52a500", "runtime/analysis/sony-lz77.h", "repository context"),
]


def main():
    result={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"sources":[],"local_searches":[]}
    for title,repo,commit,path,license_name in SOURCES:
        url=f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
        body=subprocess.check_output(["curl","-fL","--retry","2","--max-time","30","-sS",url])
        text=body.decode()
        anchors={}
        for index,line in enumerate(text.splitlines(),1):
            if any(needle in line for needle in ("index_to_size", "len_table", "lengths", "LZ77_COMPRESSED", "LZ77_RAW", "WIN_BITS", "MIN_LEN", "MAX_LEN", "int lz77_inflate", "def inflateLz77", "block_start", "bd == 0", "!distance")):
                anchors.setdefault("relevant_line_numbers",[]).append(index)
        result['sources'].append({"title":title,"repo":repo,"commit":commit,"path":path,"url":url,
                 "browse_url":f"https://github.com/{repo}/blob/{commit}/{path}","bytes":len(body),
                 "sha256":hashlib.sha256(body).hexdigest(),"license_observed":license_name,**anchors})
    for local in [
        "work/sony-firmware-20261024/stage135-Fastboot-entry-discovery/a7iv-reference-source/ILCE-7M4-RE-2328d18ce640e6c8cd9341efcf0043ce9042a135",
        "work/sony-firmware-20261024/stage204-public-AP-boot-reference",
        "work/fx3-vm-20261101/lead-claude/research/a7c2-latest"]:
        proc=subprocess.run(["rg","-n","-i",r"uxd|ldec|lz77|lz.?77 decoder",str(MAC/local)],capture_output=True,text=True)
        if proc.returncode not in (0,1): raise RuntimeError(proc.stderr)
        result['local_searches'].append({"path":str(MAC/local),"regex":"uxd|ldec|lz77|lz.?77 decoder",
               "rg_exit":proc.returncode,"text_match_lines":len(proc.stdout.splitlines()),
               "note":"rg default text/ignore rules; negative search is bounded to this snapshot"})
    (ROOT/'results/public_sources.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('Recorded',len(result['sources']),'pinned public source receipts; no vendor source persisted')


if __name__=='__main__':main()
