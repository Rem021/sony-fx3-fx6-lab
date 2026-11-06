"""Read only the two fixed FX3 guest linker inputs from the pinned CPIO."""
from __future__ import annotations

import hashlib
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[2]/"hybrid-ap-candidate/guest-three-entry.cpio"
SOURCE_SHA="bb618bd24f0b504edb14820da4d8204c4b1517cc225e4633eb43f5884f3fff02"
NAMES={"lib/libc-2.25.so","lib/libdl-2.25.so"}


def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()


def main()->None:
    if sha(SOURCE)!=SOURCE_SHA:raise ValueError("source CPIO SHA drift")
    target=HERE/"link-inputs";target.mkdir(exist_ok=True)
    seen={}
    with SOURCE.open("rb") as f:
        off=0
        while True:
            f.seek(off);h=f.read(110)
            if len(h)!=110 or h[:6]!=b"070701":raise ValueError("newc header")
            size=int(h[54:62],16);n=int(h[94:102],16)
            if not 1<=n<=4096:raise ValueError("newc name")
            name=f.read(n)
            if not name.endswith(b"\0"):raise ValueError("newc terminator")
            name=name[:-1].decode()
            data=(off+110+n+3)&~3
            if name in NAMES:
                f.seek(data);b=f.read(size)
                if len(b)!=size or b[:4]!=b"\x7fELF":raise ValueError("link ELF")
                out=target/Path(name).name
                if out.exists() and out.read_bytes()!=b:raise ValueError("link input drift")
                if not out.exists():out.write_bytes(b)
                seen[name]={"size":size,"sha256":hashlib.sha256(b).hexdigest()}
            if name=="TRAILER!!!":break
            off=(data+size+3)&~3
    if set(seen)!=NAMES:raise ValueError("guest link dependencies missing")
    print(seen)


if __name__=="__main__":main()
