#!/usr/bin/env python3
"""Read-only ARM64 Mach-O view; no dyld loading or native/vendor code execution."""
from pathlib import Path
import struct


class MachO:
    def __init__(self,path):
        self.path=Path(path);self.file=self.path.read_bytes();b=self.file;self.slice_offset=0
        if b[:4]==b'\xca\xfe\xba\xbe':
            count=struct.unpack_from('>I',b,4)[0];assert 0<count<=16
            matches=[]
            for i in range(count):
                cpu,sub,off,size,alignment=struct.unpack_from('>5I',b,8+20*i)
                assert off+size<=len(b)
                if cpu==0x100000c:matches.append((off,size))
            assert len(matches)==1;self.slice_offset,size=matches[0];b=b[self.slice_offset:self.slice_offset+size]
        self.b=b;head=struct.unpack_from('<8I',b,0);assert head[0]==0xfeedfacf and head[1]==0x100000c
        self.segments=[];self.sections=[];self.commands=[];pos=32
        for _ in range(head[4]):
            cmd,size=struct.unpack_from('<2I',b,pos);assert size>=8 and pos+size<=32+head[5]
            self.commands.append((cmd,pos,size))
            if cmd==0x19:
                _,_,name,va,vmbytes,off,filebytes,maxprot,initprot,nsect,flags=struct.unpack_from('<II16s4Q4I',b,pos)
                segment=dict(name=name.rstrip(b'\0').decode(),va=va,vm_bytes=vmbytes,file_offset=off,file_bytes=filebytes,protection=initprot)
                assert off+filebytes<=len(b);self.segments.append(segment)
                for i in range(nsect):
                    values=struct.unpack_from('<16s16s2Q8I',b,pos+72+80*i)
                    self.sections.append(dict(name=values[0].rstrip(b'\0').decode(),segment=values[1].rstrip(b'\0').decode(),va=values[2],bytes=values[3],file_offset=values[4],flags=values[8],reserved1=values[9],reserved2=values[10],index=len(self.sections)+1))
            pos+=size
        assert pos==32+head[5]
        self.symbols=[];self.function_starts=[]
        for cmd,pos,size in self.commands:
            if cmd==2:
                symoff,nsyms,stroff,strbytes=struct.unpack_from('<4I',b,pos+8);strings=b[stroff:stroff+strbytes]
                assert symoff+nsyms*16<=len(b) and len(strings)==strbytes
                for i in range(nsyms):
                    nameoff,kind,section,desc,va=struct.unpack_from('<IBBHQ',b,symoff+16*i)
                    assert nameoff<len(strings)
                    end=strings.find(b'\0',nameoff);assert end>=nameoff
                    name=strings[nameoff:end].decode('utf-8',errors='replace')
                    self.symbols.append(dict(name=name,kind=kind,section=section,va=va,index=i))
            if cmd==0x26:
                off,n=struct.unpack_from('<2I',b,pos+8);data=b[off:off+n];assert len(data)==n
                cursor=0;address=next(s['va'] for s in self.segments if s['name']=='__TEXT')
                while cursor<len(data):
                    value=0;shift=0
                    while True:
                        byte=data[cursor];cursor+=1;value|=(byte&127)<<shift;shift+=7;assert shift<=64
                        if byte<128:break
                    if not value:break
                    address+=value;self.function_starts.append(address)
        self.stubs={}
        for cmd,pos,size in self.commands:
            if cmd==0xb:
                fields=struct.unpack_from('<20I',b,pos)
                indirectoff,indirectcount=fields[14:16]
                assert indirectoff+indirectcount*4<=len(b)
                indirect=struct.unpack_from('<'+str(indirectcount)+'I',b,indirectoff)
                for sec in self.sections:
                    if sec['flags']&0xff!=8:continue
                    step=sec['reserved2'];assert step and sec['bytes']%step==0
                    for i in range(sec['bytes']//step):
                        ix=sec['reserved1']+i;assert ix<len(indirect)
                        sym=indirect[ix]
                        if sym&0xc0000000:continue
                        assert sym<len(self.symbols)
                        self.stubs[sec['va']+step*i]=self.symbols[sym]['name']

    def read(self,va,size):
        for seg in self.segments:
            start=seg['va'];off=seg['file_offset']+va-start
            if start<=va and va+size<=start+seg['file_bytes']:return self.b[off:off+size]
        raise ValueError(('not file-backed',hex(va),size))

    def function(self,va):
        assert va in self.function_starts
        ends=[a for a in self.function_starts if a>va];assert ends
        return self.read(va,min(ends)-va)
