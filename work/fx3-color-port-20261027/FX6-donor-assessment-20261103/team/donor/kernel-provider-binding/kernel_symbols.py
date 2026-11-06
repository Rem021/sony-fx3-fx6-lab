#!/usr/bin/env python3
"""Recover FX6 kallsyms from this exact Image's original instructions and tables.

The old FX3 code provides a search signature only. Every address, count and
symbol in the output comes from the pinned FX6 original Image.
"""
from pathlib import Path
from hashlib import sha256
import struct

HERE=Path(__file__).resolve().parent
IMAGE=HERE.parent/'fat-files/nflasha3/vmlinux.bin'
PIN='bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9'
LOOKUP_SIGNATURE=bytes.fromhex('82040058040400114340208b42486038')
TOKEN_INDEX_SIGNATURE=bytes.fromhex('0000050009000c000f00150019001c00')


def unique_find(data,pattern):
    first=data.find(pattern)
    if first<0 or data.find(pattern,first+1)>=0:raise ValueError('absent/ambiguous FX6 original pattern')
    return first


class KernelSymbols:
    def __init__(self):
        self.raw=IMAGE.read_bytes()
        if sha256(self.raw).hexdigest()!=PIN:raise ValueError('FX6 kernel Image SHA mismatch')
        self.lookup_start=unique_find(self.raw,LOOKUP_SIGNATURE)
        token_index_offset=unique_find(self.raw,TOKEN_INDEX_SIGNATURE)
        # Offsets within the verified lookup/expand code sequence, not table addresses.
        instruction_delta={'names':0,'token_index':0x20,'token_table':0x28,
                           'count':0x188,'offsets':0x1dc,'relative_base':0x1e0}
        literal_values={}
        for name,delta in instruction_delta.items():
            pc=self.lookup_start+delta
            word=self.u32(pc)
            if word&0xff000000!=0x58000000:raise ValueError(('not original LDR literal',name,hex(pc)))
            imm=(word>>5)&0x7ffff
            if imm&0x40000:imm-=0x80000
            literal=pc+4*imm
            if literal<0 or literal+8>len(self.raw):raise ValueError('literal out of FX6 file')
            literal_values[name]={'instruction_offset':pc,'instruction_word':hex(word),
                                  'literal_offset':literal,'absolute_value':self.u64(literal)}
        self.base=literal_values['token_index']['absolute_value']-token_index_offset
        if self.base & 0xfff or self.base>>48 != 0xffff:raise ValueError('derived FX6 kernel VA base implausible')
        self.tables={}
        for name,row in literal_values.items():
            off=row['absolute_value']-self.base
            if not 0<=off<len(self.raw):raise ValueError(('table outside FX6 Image',name))
            self.tables[name]={**row,'file_offset':off}
        if self.tables['token_index']['file_offset']!=token_index_offset:
            raise ValueError('token-index independent structural locator mismatch')
        self.count=self.u64(self.tables['count']['file_offset'])
        self.relative_base=self.u64(self.tables['relative_base']['file_offset'])
        if not 1<=self.count<=100000 or self.relative_base!=self.base:
            raise ValueError('FX6 symbol count or relative-base self-check failed')
        offsets=self.tables['offsets']['file_offset'];names=self.tables['names']['file_offset']
        token_table=self.tables['token_table']['file_offset'];token_index=self.tables['token_index']['file_offset']
        if offsets+4*self.count>self.tables['relative_base']['file_offset'] or token_index+512>len(self.raw):
            raise ValueError('FX6 table bounds overlap')
        self.tokens=[]
        for n in range(256):
            at=token_table+self.u16(token_index+2*n)
            if not token_table<=at<token_index:raise ValueError('bad token pointer')
            end=self.raw.find(b'\0',at,token_index)
            if end<0 or end-at>128:raise ValueError('bad token')
            self.tokens.append(self.raw[at:end])
        cursor=names;rows=[];previous=0
        for n in range(self.count):
            compressed_offset=cursor-names
            if not names<=cursor<token_table:raise ValueError('name past table')
            size=self.raw[cursor];cursor+=1
            if not 1<=size or cursor+size>token_table:raise ValueError('invalid compressed symbol')
            expanded=b''.join(self.tokens[x] for x in self.raw[cursor:cursor+size]);cursor+=size
            if not 2<=len(expanded)<=256 or not all(32<=x<127 for x in expanded):
                raise ValueError('bad expanded symbol')
            address=self.relative_base+self.u32(offsets+4*n)
            if not previous<=address<self.base+0x10000000:raise ValueError('unsorted symbol VA')
            previous=address
            rows.append({'index':n,'type':chr(expanded[0]),'name':expanded[1:].decode('ascii'),
                         'address':address,'file_offset':address-self.base,
                         'compressed_offset':compressed_offset,'compressed_next':cursor-names})
        self.rows=rows;self.names_end=cursor;self.by_name={}
        for row in rows:self.by_name.setdefault(row['name'],[]).append(row)

    def u16(self,offset):return struct.unpack_from('<H',self.raw,offset)[0]
    def u32(self,offset):return struct.unpack_from('<I',self.raw,offset)[0]
    def u64(self,offset):return struct.unpack_from('<Q',self.raw,offset)[0]

    def unique(self,name):
        rows=self.by_name.get(name,[])
        if len(rows)!=1:raise ValueError('absent/ambiguous original symbol: '+name)
        return rows[0]

    def span(self,name):
        row=self.unique(name);start=row['file_offset']
        later=next((x['file_offset'] for x in self.rows[row['index']+1:] if x['file_offset']>start),None)
        if row['type'] not in ('t','T') or later is None or not 0<=start<later<=len(self.raw):
            raise ValueError('no file-backed next-symbol span')
        return start,later
