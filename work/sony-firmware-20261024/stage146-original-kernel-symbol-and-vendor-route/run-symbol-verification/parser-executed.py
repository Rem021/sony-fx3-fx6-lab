"""Read compressed names/relative symbol addresses from one pinned kernel Image.

Table locations are obtained from the Image's original kallsyms instruction
literal operands, not by assuming that a reference build has the same layout.
No kernel code is loaded into the host or executed by this parser.
"""
from pathlib import Path
from hashlib import sha256
import struct

BASE=Path(__file__).resolve().parent.parent
K=0xffffff8008080000
KERNEL=BASE/'stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin'
KERNEL_SHA256='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'


class KernelSymbols:
    def __init__(self):
        self.raw=KERNEL.read_bytes()
        if sha256(self.raw).hexdigest()!=KERNEL_SHA256:raise ValueError('kernel Image pin mismatch')
        self.tables={}
        # These six LDR64-literal instructions are fixed by the Image hash.
        for name,pc in [('names',0x95bf8),('token_index',0x95c18),('token_table',0x95c20),
                        ('count',0x95d80),('offsets',0x95dd4),('relative_base',0x95dd8)]:
            word=self.u32(pc)
            if word&0xff000000!=0x58000000:raise ValueError('expected LDR64 literal')
            imm=(word>>5)&0x7ffff
            if imm&0x40000:imm-=0x80000
            literal=pc+4*imm
            table_address=self.u64(literal);off=table_address-K
            if not 0<=off<len(self.raw):raise ValueError('table outside original Image')
            self.tables[name]={'instruction_offset':pc,'literal_offset':literal,'file_offset':off}
        self.count=self.u64(self.tables['count']['file_offset'])
        self.relative_base=self.u64(self.tables['relative_base']['file_offset'])
        if not 1<=self.count<=100000 or self.relative_base!=K:raise ValueError('unsupported count or relative base')
        offsets=self.tables['offsets']['file_offset'];names=self.tables['names']['file_offset']
        token_table=self.tables['token_table']['file_offset'];token_index=self.tables['token_index']['file_offset']
        if offsets+4*self.count>self.tables['relative_base']['file_offset'] or token_index+512>len(self.raw):
            raise ValueError('table bounds overlap')
        self.tokens=[]
        for n in range(256):
            at=token_table+self.u16(token_index+2*n)
            if not token_table<=at<token_index:raise ValueError('invalid token pointer')
            end=self.raw.find(b'\0',at,token_index)
            if end<0 or end-at>128:raise ValueError('invalid token length')
            self.tokens.append(self.raw[at:end])
        cursor=names;rows=[];previous=0
        for n in range(self.count):
            compressed_offset=cursor-names
            if not names<=cursor<token_table:raise ValueError('name length outside table')
            size=self.raw[cursor];cursor+=1
            if not 1<=size or cursor+size>token_table:raise ValueError('invalid compressed name')
            expanded=b''.join(self.tokens[x] for x in self.raw[cursor:cursor+size]);cursor+=size
            if not 2<=len(expanded)<=256 or not all(32<=x<127 for x in expanded):raise ValueError('invalid expanded symbol')
            address=self.relative_base+self.u32(offsets+4*n)
            if not previous<=address<K+0x10000000:raise ValueError('unsorted or unsupported symbol addresses')
            previous=address
            rows.append({'index':n,'type':chr(expanded[0]),'name':expanded[1:].decode('ascii'),
                         'address':address,'file_offset':address-K,
                         'compressed_offset':compressed_offset,'compressed_next':cursor-names})
        self.rows=rows;self.names_end=cursor;self.by_name={}
        for row in rows:self.by_name.setdefault(row['name'],[]).append(row)

    def u16(self,offset):return struct.unpack_from('<H',self.raw,offset)[0]
    def u32(self,offset):return struct.unpack_from('<I',self.raw,offset)[0]
    def u64(self,offset):return struct.unpack_from('<Q',self.raw,offset)[0]

    def unique(self,name):
        rows=self.by_name.get(name,[])
        if len(rows)!=1:raise ValueError('symbol is absent or ambiguous: '+name)
        return rows[0]

    def span(self,name):
        row=self.unique(name);start=row['file_offset']
        later=next((x['file_offset'] for x in self.rows[row['index']+1:] if x['file_offset']>start),None)
        if row['type'] not in ('t','T') or later is None or not 0<=start<later<=len(self.raw):
            raise ValueError('no file-backed next-symbol code span')
        return start,later
