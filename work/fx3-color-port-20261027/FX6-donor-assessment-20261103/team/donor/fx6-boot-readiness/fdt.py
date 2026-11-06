"""Bounded FDT v17 structure reader; no DTB edits or guest execution."""
from __future__ import annotations
import struct


def parse_fdt(data: bytes) -> dict:
    if len(data) < 40:
        raise ValueError("short FDT")
    magic,total,off_struct,off_strings,off_reserve,version,last,boot_cpu,size_strings,size_struct = struct.unpack_from(">10I",data)
    if magic != 0xd00dfeed or total > len(data) or off_struct+size_struct > total or off_strings+size_strings > total or off_reserve >= total:
        raise ValueError("invalid FDT header/bounds")
    strings=data[off_strings:off_strings+size_strings]
    pos=off_struct
    end=off_struct+size_struct
    stack=[]
    nodes={}
    while pos+4<=end:
        token,=struct.unpack_from(">I",data,pos);pos+=4
        if token==1:
            stop=data.find(b"\0",pos,end)
            if stop<0:raise ValueError("unterminated FDT node")
            name=data[pos:stop].decode("utf-8","replace")
            pos=(stop+4)&~3
            path=(stack[-1].rstrip("/")+"/"+name) if stack else "/"
            stack.append(path)
            nodes[path]={}
        elif token==2:
            if not stack:raise ValueError("FDT stack underflow")
            stack.pop()
        elif token==3:
            if not stack or pos+8>end:raise ValueError("FDT property header")
            length,nameoff=struct.unpack_from(">II",data,pos);pos+=8
            if pos+length>end or nameoff>=len(strings):raise ValueError("FDT property bounds")
            stop=strings.find(b"\0",nameoff)
            if stop<0:raise ValueError("FDT property name")
            key=strings[nameoff:stop].decode("utf-8","replace")
            nodes[stack[-1]][key]=data[pos:pos+length]
            pos=(pos+length+3)&~3
        elif token==4:
            continue
        elif token==9:
            if stack:raise ValueError("FDT unclosed nodes")
            break
        else:
            raise ValueError(f"unknown FDT token {token}")
    def decode_strings(raw):
        return [s.decode("utf-8","replace") for s in raw.split(b"\0") if s]
    summary={"version":version,"total_bytes":total,"node_count":len(nodes),"root_compatible":decode_strings(nodes.get("/",{}).get("compatible",b"")),"root_model":decode_strings(nodes.get("/",{}).get("model",b"")),"selected_nodes":[]}
    for path,props in nodes.items():
        compatible=decode_strings(props.get("compatible",b""))
        if any(x in path.lower() or any(x in c.lower() for c in compatible) for x in ("pcie","dma","pciatu","virtio","cxd90057","pl330")):
            summary["selected_nodes"].append({"path":path,"compatible":compatible,"status":decode_strings(props.get("status",b"")),"reg_hex":props.get("reg",b"").hex()[:256]})
    return summary
