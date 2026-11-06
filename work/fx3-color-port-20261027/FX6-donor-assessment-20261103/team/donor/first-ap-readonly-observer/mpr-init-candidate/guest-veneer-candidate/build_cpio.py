"""Repack only patched FX6 AP and one independent bridge member in fixed newc extent."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

HERE=Path(__file__).resolve().parent
DONOR=HERE.parents[2]
SOURCE=DONOR/"hybrid-ap-candidate/guest-three-entry.cpio"
SOURCE_SHA="bb618bd24f0b504edb14820da4d8204c4b1517cc225e4633eb43f5884f3fff02"
AP=HERE/"appFw-bridge.so"
BRIDGE=HERE/"libfx6diag.so"
OUT=HERE/"guest-veneer.cpio"
TARGET="usr/lib/appFw.so"
NEW="usr/lib/libfx6diag.so"


def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()


def records(f):
    off=0
    while True:
        f.seek(off);h=f.read(110)
        if len(h)!=110 or h[:6]!=b"070701":raise ValueError(f"newc at {off}")
        size=int(h[54:62],16);n=int(h[94:102],16)
        if not 1<=n<=4096:raise ValueError("name length")
        name=f.read(n)
        if not name.endswith(b"\0"):raise ValueError("name terminator")
        data=(off+110+n+3)&~3
        end=(data+size+3)&~3
        yield name[:-1].decode(),off,data,end,h
        if name==b"TRAILER!!!\0":break
        off=end


def copy(f,g,off,n):
    f.seek(off)
    while n:
        b=f.read(min(n,1<<20))
        if not b:raise ValueError("source truncation")
        g.write(b);n-=len(b)


def new_header(size:int)->bytes:
    name=NEW.encode()+b"\0"
    fields=(0xF6D1A6,0o100755,0,0,1,0,size,0,0,0,0,len(name),0)
    h=b"070701"+b"".join(f"{x:08x}".encode() for x in fields)
    if len(h)!=110:raise ValueError("newc header construction")
    return h+name+b"\0"*((-len(h)-len(name))&3)


def main()->None:
    if OUT.exists():raise FileExistsError(f"preserve candidate {OUT}")
    patch=json.loads((HERE/"ap-patch.json").read_text())
    if sha(SOURCE)!=SOURCE_SHA or sha(AP)!=patch["patched_sha256"]:
        raise ValueError("source CPIO or patched AP drift")
    if AP.stat().st_size!=50520424 or BRIDGE.stat().st_size>1<<20:
        raise ValueError("payload size bound")
    bridge_sha=sha(BRIDGE)
    tmp=OUT.with_suffix(".cpio.partial")
    if tmp.exists():raise FileExistsError(f"preserve partial {tmp}")
    count=0;changed=0;inserted=0;old_end=0;new_end=0
    try:
        with SOURCE.open("rb") as src,AP.open("rb") as ap,BRIDGE.open("rb") as bridge,tmp.open("xb") as dst:
            for name,off,data,end,h in records(src):
                if name==TARGET:
                    if int(h[54:62],16)!=AP.stat().st_size:raise ValueError("AP member length drift")
                    src.seek(data)
                    digest=hashlib.sha256()
                    left=AP.stat().st_size
                    while left:
                        b=src.read(min(left,1<<20));digest.update(b);left-=len(b)
                    if digest.hexdigest()!=patch["source_sha256"]:raise ValueError("AP member SHA drift")
                    copy(src,dst,off,data-off)
                    while True:
                        b=ap.read(1<<20)
                        if not b:break
                        dst.write(b)
                    dst.write(b"\0"*((-dst.tell())&3))
                    changed+=1
                else:
                    copy(src,dst,off,end-off)
                if name!="TRAILER!!!":count+=1
                if name==TARGET:
                    dst.write(new_header(BRIDGE.stat().st_size))
                    while True:
                        b=bridge.read(1<<20)
                        if not b:break
                        dst.write(b)
                    dst.write(b"\0"*((-dst.tell())&3))
                    inserted+=1;count+=1
                if name=="TRAILER!!!":
                    old_end=end;new_end=dst.tell()
            if changed!=1 or inserted!=1 or count!=1141 or new_end>=SOURCE.stat().st_size:
                raise ValueError("member count or padding bound")
            left=SOURCE.stat().st_size-new_end
            block=b"\0"*(1<<20)
            while left:
                n=min(left,len(block));dst.write(block[:n]);left-=n
            dst.flush();os.fsync(dst.fileno())
        if tmp.stat().st_size!=SOURCE.stat().st_size:raise ValueError("fixed initrd extent drift")
        tmp.rename(OUT)
    except Exception:
        if tmp.exists():tmp.unlink()
        raise
    result={"source_cpio_sha256":SOURCE_SHA,"candidate_sha256":sha(OUT),
            "candidate_bytes":OUT.stat().st_size,"members":count,
            "changed_existing_member":TARGET,"new_member":NEW,
            "patched_ap_sha256":patch["patched_sha256"],"bridge_sha256":bridge_sha,
            "source_trailer_end":old_end,"candidate_trailer_end":new_end,
            "zero_tail_bytes":OUT.stat().st_size-new_end,
            "state":"STATIC_ONLY_DO_NOT_LAUNCH"}
    (HERE/"cpio-build.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
