#!/usr/bin/env python3
"""Decode original GCC LSDA and CFI; do not execute a runtime unwinder."""
from pathlib import Path
from hashlib import sha256
import io
import json
import struct
from elftools.elf.elffile import ELFFile
from elftools.dwarf.callframe import FDE

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
LIB=BASE/'stage2/extraction/files/nflasha15/lib/libJiritsu.so'
LIB_SHA='bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9'
FUNCTIONS=['adj_cmd_get_file2','_ZN11CFileAccess4statEPKcP13tag_FILE_INFO','_ZN11CFileAccess4openEPKci',
    '_ZN11CFileAccess4readEPvm','_ZN11CFileAccess5fsyncEv','_ZN11CFileAccess5closeEv']


class Metadata:
    def __init__(self):
        raw=LIB.read_bytes();assert sha256(raw).hexdigest()==LIB_SHA
        self.elf=ELFFile(io.BytesIO(raw));self.segments=[s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD']
        sy=self.elf.get_section_by_name('.dynsym');self.symbols={s.name:s for s in sy.iter_symbols() if s.name}
        self.by_address={s['st_value']:s.name for s in sy.iter_symbols() if s['st_shndx']!='SHN_UNDEF' and s.name}
        self.relocations={r['r_offset']:{'type':r['r_info_type'],'addend':r['r_addend'],
            'symbol':sy.get_symbol(r['r_info_sym']).name,'defined':sy.get_symbol(r['r_info_sym'])['st_shndx']!='SHN_UNDEF',
            'value':sy.get_symbol(r['r_info_sym'])['st_value']} for r in self.elf.get_section_by_name('.rela.dyn').iter_relocations()}
        self.frames={f['initial_location']:f for f in self.elf.get_dwarf_info().EH_CFI_entries() if isinstance(f,FDE)}
        sec=self.elf.get_section_by_name('.gcc_except_table');self.lo=sec['sh_addr'];self.hi=self.lo+sec['sh_size']

    def read(self,a,n):
        s=next(s for s in self.segments if s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz'])
        return s.data()[a-s['p_vaddr']:a-s['p_vaddr']+n]
    def leb(self,p,signed=False):
        start=p;value=0;shift=0
        for _ in range(10):
            assert self.lo<=p<self.hi
            byte=self.read(p,1)[0];p+=1;value|=(byte&127)<<shift;shift+=7
            if not byte&128:
                if signed and byte&64:value-=1<<shift
                return value,p
        raise ValueError(('LEB exceeds64-bit bound',hex(start)))
    def encoded(self,p,encoding):
        kind=encoding&15;start=p
        if kind in (1,9):value,p=self.leb(p,signed=kind==9)
        else:
            fmt={0:'<Q',2:'<H',3:'<I',4:'<Q',10:'<h',11:'<i',12:'<q'}[kind]
            n=struct.calcsize(fmt);value=struct.unpack(fmt,self.read(p,n))[0];p+=n
        if value and encoding&0x70:
            assert encoding&0x70==0x10,hex(encoding)
            value+=start
        assert not encoding&0x80,'resolve indirect type entries explicitly'
        return value,p
    def type_entry(self,base,encoding,index):
        assert encoding==0x9b,hex(encoding)
        at=base-4*index;raw=struct.unpack('<i',self.read(at,4))[0]
        if not raw:return {'filter':index,'entry':hex(at),'catch_all':True,'RTTI_symbol':None,'target':0}
        slot=at+raw;rel=self.relocations.get(slot)
        if rel:
            assert rel['type'] in [257,1025]
            return {'filter':index,'entry':hex(at),'indirect_slot':hex(slot),'catch_all':False,
                'RTTI_symbol':rel['symbol'],'target':rel['value']+rel['addend'] if rel['defined'] else None,'relocation':rel}
        target=struct.unpack('<Q',self.read(slot,8))[0]
        return {'filter':index,'entry':hex(at),'indirect_slot':hex(slot),'catch_all':False,
            'RTTI_symbol':self.by_address.get(target),'target':target}
    def decode(self,name):
        symbol=self.symbols[name];start=symbol['st_value'];f=self.frames[start];p=f.lsda_pointer
        assert self.lo<=p<self.hi
        begin=p;lp_encoding=self.read(p,1)[0];p+=1
        if lp_encoding==255:lpstart=start
        else:lpstart,p=self.encoded(p,lp_encoding)
        type_encoding=self.read(p,1)[0];p+=1;type_base=None
        if type_encoding!=255:
            offset,p=self.leb(p);type_base=p+offset
        call_encoding=self.read(p,1)[0];p+=1;length,p=self.leb(p)
        action_table=p+length;assert action_table<=self.hi
        rows=[];types={}
        while p<action_table:
            at=p;cs,p=self.encoded(p,call_encoding);n,p=self.encoded(p,call_encoding);lp,p=self.encoded(p,call_encoding);action,p=self.leb(p)
            assert p<=action_table and cs+n<=f['address_range']
            chain=[];seen=set();record=action_table+action-1 if action else None
            while record is not None:
                assert record not in seen and self.lo<=record<self.hi;seen.add(record)
                filter_value,next_field=self.leb(record,signed=True);displacement,_=self.leb(next_field,signed=True)
                entry={'VA':hex(record),'filter':filter_value,'displacement':displacement}
                if filter_value>0:
                    assert type_base is not None
                    types[filter_value]=self.type_entry(type_base,type_encoding,filter_value);entry['type']=types[filter_value]
                elif filter_value<0:entry['unsupported_exception_specification']=True
                chain.append(entry);record=next_field+displacement if displacement else None
            rows.append({'entry':hex(at),'start':hex(start+cs),'end_exclusive':hex(start+cs+n),
                'landing_pad':hex(lpstart+lp) if lp else None,'action_index':action,'actions':chain})
        assert p==action_table
        # Only fields used by the actual rows define the evidence span; CFI is
        # decoded separately and no OS runtime personality is executed.
        end=max([action_table]+[int(t['entry'],16)+4 for t in types.values()]+[
            int(a['VA'],16)+2 for row in rows for a in row['actions']])
        return {'function':name,'start':hex(start),'end_exclusive':hex(start+symbol['st_size']),
            'FDE_range':f['address_range'],'LSDA':hex(begin),'LSDA_evidence_span':end-begin,
            'LSDA_evidence_sha256':sha256(self.read(begin,end-begin)).hexdigest(),
            'LPStart_encoding':hex(lp_encoding),'LPStart':hex(lpstart),'TType_encoding':hex(type_encoding),
            'TType_base':hex(type_base) if type_base is not None else None,'call_encoding':hex(call_encoding),
            'action_table':hex(action_table),'call_sites':rows,'types':list(types.values())}

    def choose_exact(self,decoded,return_ip,thrown_symbol):
        ip=return_ip-1
        row=next((r for r in decoded['call_sites'] if int(r['start'],16)<=ip<int(r['end_exclusive'],16)),None)
        if row is None:return {'kind':'terminate_no_callsite','return_ip':hex(return_ip)}
        if row['landing_pad'] is None:return {'kind':'continue_no_landing_pad','row':row}
        if row['action_index']==0:return {'kind':'cleanup','filter':0,'landing_pad':row['landing_pad'],'row':row}
        for action in row['actions']:
            if action['filter']>0 and (action['type']['catch_all'] or action['type']['RTTI_symbol']==thrown_symbol):
                return {'kind':'handler','filter':action['filter'],'landing_pad':row['landing_pad'],'row':row,
                    'exact_symbol_or_catch_all_only_no_inheritance_or_foreign_exception_model':True}
        return {'kind':'continue_no_exact_type_match','row':row}


def main():
    m=Metadata();functions=[m.decode(n) for n in FUNCTIONS]
    decisions=[]
    for f in functions:
        for row in f['call_sites']:
            if row['landing_pad']:
                decisions.append({'function':f['function'],'at_return_ip':row['end_exclusive'],
                    'for_exact_FileAccessException':m.choose_exact(f,int(row['end_exclusive'],16),'_ZTI19FileAccessException')})
    result={'status':'PASS_ORIGINAL_LSDA_TYPE_AND_LANDING_PAD_PARSE_NOT_RUNTIME_UNWIND_ACCEPTANCE',
        'original_library_sha256':LIB_SHA,'compiler_comment':m.elf.get_section_by_name('.comment').data().decode().split('\0'),
        'functions':functions,'callsite_count':sum(len(f['call_sites']) for f in functions),
        'exact_type_decisions':decisions,'actual_personality_unwinder_or_camera_executed':False,
        'upstream_reference_is_not_exact_Sony_runtime':True}
    with (HERE/'original-LSDA-review.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    (HERE/'LSDA-parser-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'functions':len(functions),'callsite_rows':result['callsite_count'],
        'handlers':{f['function']:f['types'] for f in functions},'actual_runtime_or_device':False}))


if __name__=='__main__':main()
