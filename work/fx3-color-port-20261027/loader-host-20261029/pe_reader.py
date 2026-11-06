#!/usr/bin/env python3
"""Bounded read-only PE32 imports/exports per Microsoft PE/COFF format.
https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
This never maps executable host memory or loads a DLL.
"""
import struct
class PE:
    def __init__(self,b):
        self.b=b;assert b[:2]==b'MZ';p=self.u32(0x3c);assert b[p:p+4]==b'PE\0\0'
        self.machine=self.u16(p+4);count=self.u16(p+6);assert 0<count<=96
        size=self.u16(p+20);op=p+24;assert self.u16(op)==0x10b
        self.base=self.u32(op+28);self.headers=self.u32(op+60);self.entry=self.u32(op+16)
        n=min(self.u32(op+92),16);self.dirs=[struct.unpack_from('<II',b,op+96+i*8) for i in range(n)]
        self.sections=[]
        for i in range(count):
            at=op+size+i*40;name=b[at:at+8].rstrip(b'\0').decode('ascii')
            vs,va,rs,rp=struct.unpack_from('<IIII',b,at+8);assert rp+rs<=len(b)
            self.sections.append(dict(name=name,VA=va,virtual_size=vs,raw_offset=rp,raw_size=rs))
    def u16(self,o):assert 0<=o<=len(self.b)-2;return struct.unpack_from('<H',self.b,o)[0]
    def u32(self,o):assert 0<=o<=len(self.b)-4;return struct.unpack_from('<I',self.b,o)[0]
    def off(self,rva,n=1):
        if rva<self.headers:assert rva+n<=len(self.b);return rva
        for s in self.sections:
            x=rva-s['VA']
            if 0<=x<s['raw_size']:
                assert x+n<=s['raw_size'];return s['raw_offset']+x
        raise ValueError(f'RVA has no file-backed range: {rva:#x}')
    def cstr(self,rva):
        o=self.off(rva);e=self.b.find(b'\0',o,min(len(self.b),o+4096));assert e>=o
        return self.b[o:e].decode('ascii')
    def exports(self):
        if not self.dirs or not self.dirs[0][0]:return []
        va,size=self.dirs[0];at=self.off(va,40)
        _,_,_,_,_,base,nf,nn,funcs,names,ords=struct.unpack_from('<IIHHIIIIIII',self.b,at)
        assert nn<=nf<=65536;rows=[]
        for i in range(nn):
            name=self.cstr(self.u32(self.off(names+i*4,4)));ordinal=self.u16(self.off(ords+i*2,2));assert ordinal<nf
            rva=self.u32(self.off(funcs+ordinal*4,4))
            row=dict(name=name,ordinal=base+ordinal,RVA=rva,VA=self.base+rva)
            if va<=rva<va+size:row['forwarded_to']=self.cstr(rva)
            elif rva:row['file_offset']=self.off(rva)
            rows.append(row)
        return rows
    def imports(self):
        if len(self.dirs)<2 or not self.dirs[1][0]:return []
        va,size=self.dirs[1];rows=[]
        for i in range(min(size//20+1,2048)):
            p=self.off(va+i*20,20);oft,stamp,chain,name,ft=struct.unpack_from('<5I',self.b,p)
            if not any([oft,stamp,chain,name,ft]):break
            dll=self.cstr(name);names=[]
            for j in range(65536):
                value=self.u32(self.off((oft or ft)+j*4,4))
                if not value:break
                label={'ordinal':value&0xffff} if value&0x80000000 else {'name':self.cstr(value+2)}
                names.append(dict(**label,IAT_RVA=ft+j*4,IAT_VA=self.base+ft+j*4))
            else:raise ValueError('Import thunk limit')
            rows.append(dict(DLL=dll,functions=names))
        return rows
