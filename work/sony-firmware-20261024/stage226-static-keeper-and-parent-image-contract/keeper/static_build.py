"""Restricted static ELF construction for our two pinned worker sources only.

No linker installation, native loader, firmware execution or camera operation.
Unsupported object forms/relocations fail closed; this is not a general linker.
"""
from hashlib import sha256
from pathlib import Path
import sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sys.path.insert(0,str(ROOT/'outputs/fx3-recovery-adapter'))
from fx3_recovery import elflink as LEGACY
import struct
import subprocess
from fx3_recovery.files import read_file, require, encode
from fx3_recovery.capture import PrivateDirectory, FALSE_FLAGS

PAGE=65536
BASE=0x400000
HEADER=struct.Struct('<16sHHIQQQIHHHHHH')
SECTION=struct.Struct('<IIQQQQIIQQ')
SYMBOL=struct.Struct('<IBBHQQ')
RELA=struct.Struct('<QQq')
PROGRAM=struct.Struct('<IIQQQQQQ')
SOURCE_SHA='d117b33f7e8a38864846e710df41d0491ce058c3099b1eaee66ad819ece035a2'
ENTRY_SOURCE=(b'.section .text\n.global _start\n.type _start,%function\n_start:\n'
              b'    bl fx3_keeper_run\n    mov x8, #93\n    svc #0\n    b .\n'
              b'.size _start, .-_start\n.section .note.GNU-stack,"",%progbits\n')
MAX_OBJECT=4*1024*1024
RELOCATIONS={275:'ADR_PREL_PG_HI21',277:'ADD_ABS_LO12_NC',286:'LDST64_ABS_LO12_NC',
             299:'LDST128_ABS_LO12_NC',283:'CALL26',285:'LDST32_ABS_LO12_NC'}


def align(value,unit):
    require(type(unit) is int and 0<unit<=PAGE and not unit&(unit-1), 'invalid section alignment')
    return (value+unit-1)&-unit


def cstring(table,offset):
    require(0<=offset<len(table), 'string offset outside table')
    end=table.find(b'\0',offset,offset+512)
    require(end>=0, 'unbounded ELF string')
    return table[offset:end].decode('ascii')


class Object:
    def __init__(self,raw,name):
        require(type(raw) is bytes and HEADER.size<=len(raw)<=MAX_OBJECT, 'object size limit')
        h=HEADER.unpack_from(raw)
        require(h[0]==b'\x7fELF\x02\x01\x01'+b'\0'*9 and h[1:4]==(1,183,1)
                and h[4]==h[5]==h[7]==h[10]==0 and h[8]==64 and h[11]==64
                and 0<h[12]<=1024 and h[13]<h[12], 'only static little-endian AArch64 ET_REL input')
        require(h[6]+h[12]*64<=len(raw), 'section table outside object')
        self.raw=raw;self.name=name;self.sections=[]
        for i in range(h[12]):
            values=SECTION.unpack_from(raw,h[6]+i*64)
            row=dict(zip(('name_offset','type','flags','va','offset','bytes','link','info','align','entry_bytes'),values))
            row['index']=i
            require(row['bytes']<=MAX_OBJECT and (row['type']==8 or row['offset']+row['bytes']<=len(raw)), 'section out of bounds')
            self.sections.append(row)
        names=self.sections[h[13]]
        require(names['type']==3, 'missing section name table')
        names=raw[names['offset']:names['offset']+names['bytes']]
        for row in self.sections:
            row['name']=cstring(names,row['name_offset'])
            require(row['type'] not in (6,11,14,15,16), 'dynamic or initializer section rejected')
            if row['flags']&2:
                require(row['type'] in (1,8) and not row['flags']&0x400
                        and not (row['flags']&1 and row['flags']&4), 'unsupported allocated section permissions/type')
                require(row['name'].startswith(('.text','.rodata','.data','.bss')), 'non-worker allocated section')
                align(0,row['align'] or 1)
                if row['flags']&4:require(row['align']>=4 and row['bytes']%4==0, 'unaligned AArch64 code')
        tables=[s for s in self.sections if s['type']==2]
        require(len(tables)==1, 'exactly one symbol table required')
        table=tables[0];require(table['entry_bytes']==24 and table['bytes']%24==0 and table['bytes']//24<=4096
                               and table['link']<len(self.sections), 'invalid symbol table')
        strings=self.sections[table['link']];require(strings['type']==3, 'invalid symbol strings')
        strings=raw[strings['offset']:strings['offset']+strings['bytes']]
        self.symbols=[];self.relocations=[]
        for offset in range(table['offset'],table['offset']+table['bytes'],24):
            n,info,other,section,value,size=SYMBOL.unpack_from(raw,offset)
            self.symbols.append({'name':cstring(strings,n),'info':info,'other':other,'section':section,'value':value,'bytes':size})
        for row in self.sections:
            if row['type']!=4:continue
            require(row['entry_bytes']==24 and row['bytes']%24==0 and row['link']==table['index']
                    and row['info']<len(self.sections), 'invalid RELA table')
            target=self.sections[row['info']]
            require(target['flags']&2 and target['type']==1, 'only allocated PROGBITS relocations')
            for at in range(row['offset'],row['offset']+row['bytes'],24):
                offset,info,addend=RELA.unpack_from(raw,at)
                require(info>>32<len(self.symbols) and info&0xffffffff in RELOCATIONS
                        and offset%4==0 and offset+4<=target['bytes'], 'unsupported or out-of-bounds relocation')
                self.relocations.append({'section':target['index'],'offset':offset,'type':info&0xffffffff,
                                         'symbol':info>>32,'addend':addend})
                require(len(self.relocations)<=1024, 'worker relocation count limit')
        require(not any(s['type']==9 for s in self.sections), 'REL without explicit addends rejected')


def relocate(word,kind,place,target):
    # ADRP always uses the ISA 4096-byte page, independently of segment layout.
    if kind!=285:return LEGACY.relocate(word,kind,place,target)
    require(word&0xff800000==0xb9000000 and target%4==0,'LDST32 integer opcode/alignment mismatch')
    result=(word&~(0xfff<<10))|(((target&0xfff)//4)<<10)
    require(((result>>10)&0xfff)*4==target&0xfff,'LDST32 roundtrip differs')
    return result


def link_objects(raw_objects, worker_symbol='fx3_p1_read_window'):
    require(worker_symbol in ('fx3_p1_read_window','fx3_boot_read_window','fx3_keeper_run'), 'unreviewed worker entry rejected')
    require(type(raw_objects) is list and len(raw_objects)==2, 'only worker.o and entry.o are supported')
    objects=[Object(raw,name) for name,raw in raw_objects]
    placements={};groups=[];cursor=PAGE
    for flags in (5,4,6):
        content=bytearray();mem=0;members=[]
        for oi,obj in enumerate(objects):
            sections=sorted(obj.sections,key=lambda s:s['type']==8)
            for s in sections:
                if not s['flags']&2 or not s['bytes']:continue
                actual=5 if s['flags']&4 else 6 if s['flags']&1 else 4
                if actual!=flags:continue
                mem=align(mem,s['align'] or 1)
                members.append((oi,s['index']))
                placements[(oi,s['index'])]={'va':BASE+cursor+mem,'offset':cursor+mem,'bytes':s['bytes'],
                                             'flags':flags,'name':s['name'],'object':obj.name}
                if s['type']==1:
                    require(len(content)<=mem, 'PROGBITS following BSS rejected')
                    content.extend(b'\0'*(mem-len(content)))
                    content.extend(obj.raw[s['offset']:s['offset']+s['bytes']])
                mem+=s['bytes']
        require(mem>0, 'missing worker code, constants or BSS group')
        groups.append({'flags':flags,'offset':cursor,'va':BASE+cursor,'filesz':len(content),'memsz':mem,
                       'data':content,'members':members})
        cursor=align(cursor+max(len(content),1),PAGE)
    output=bytearray(cursor)
    for g in groups:output[g['offset']:g['offset']+g['filesz']]=g['data']
    globals_={}
    for oi,obj in enumerate(objects):
        for s in obj.symbols:
            binding=s['info']>>4
            if binding not in (1,2):continue
            if s['section']==0:
                require(s['name']==worker_symbol, 'external import rejected');continue
            require(binding==1 and s['info']&15==2 and s['name'] in ('_start',worker_symbol)
                    and (oi,s['section']) in placements and s['name'] not in globals_, 'unexpected global definition')
            location=placements[(oi,s['section'])]
            require(location['flags']==5 and s['value']+s['bytes']<=location['bytes'], 'global function outside code')
            globals_[s['name']]=(oi,s)
    require(set(globals_)=={'_start',worker_symbol}, 'missing entry or worker function')
    records=[];changed=set()
    for oi,obj in enumerate(objects):
        for r in obj.relocations:
            symbol=obj.symbols[r['symbol']];owner=oi
            if symbol['section']==0:
                require(symbol['name'] in globals_, 'unresolved symbol');owner,symbol=globals_[symbol['name']]
            require((owner,symbol['section']) in placements, 'absolute, common or nonallocated symbol rejected')
            defined=placements[(owner,symbol['section'])]
            relative=symbol['value']+r['addend']
            require(0<=relative<defined['bytes'], 'relocation target outside allocated section')
            target=defined['va']+relative;location=placements[(oi,r['section'])]
            at=location['offset']+r['offset'];place=location['va']+r['offset']
            require(not changed.intersection(range(at,at+4)), 'overlapping relocation writes')
            original=struct.unpack_from('<I',output,at)[0]
            patched=relocate(original,r['type'],place,target)
            if r['type']==283:require(defined['flags']==5, 'call into non-executable section')
            struct.pack_into('<I',output,at,patched);changed.update(range(at,at+4))
            records.append({'object':obj.name,'section':location['name'],'kind':RELOCATIONS[r['type']],
                'place':place,'target':target,'file_offset':at,'before':original,'after':patched})
    for oi,obj in enumerate(objects):
        for s in obj.sections:
            key=(oi,s['index'])
            if key not in placements or s['type']!=1:continue
            at=placements[key]['offset'];before=obj.raw[s['offset']:s['offset']+s['bytes']]
            require(all(a==b or at+i in changed for i,(a,b) in enumerate(zip(before,output[at:at+len(before)]))),
                    'section changed outside recorded relocation fields')
    oi,symbol=globals_['_start'];entry=placements[(oi,symbol['section'])]['va']+symbol['value']
    ph=[(1,4,0,BASE,BASE,PAGE,PAGE,PAGE)]
    ph.extend((1,g['flags'],g['offset'],g['va'],g['va'],g['filesz'],g['memsz'],PAGE) for g in groups)
    ph.append((0x6474e551,6,0,0,0,0,0,16))
    ident=b'\x7fELF\x02\x01\x01'+b'\0'*9
    output[:64]=HEADER.pack(ident,2,183,1,entry,64,0,0,64,56,len(ph),0,0,0)
    for i,p in enumerate(ph):PROGRAM.pack_into(output,64+56*i,*p)
    raw=bytes(output);segments=read_executable(raw)
    return raw,{'schema':'fx3-own-worker-static-link-v1','entry':entry,'segments':segments,
        'objects':[{'name':o.name,'sha256':sha256(o.raw).hexdigest()} for o in objects],
        'relocations':records,'sha256':sha256(raw).hexdigest(),'bytes':len(raw),
        'runtime_loader_or_imports':False,'AArch64_machine_code_execution_verified_by_builder':False,'camera_operations':0,
        'camera_launch_or_transfer_verified':False, **FALSE_FLAGS}


def read_executable(raw):
    require(type(raw) is bytes and 4096<=len(raw)<=MAX_OBJECT, 'ELF executable size limit')
    h=HEADER.unpack_from(raw)
    require(h[0]==b'\x7fELF\x02\x01\x01'+b'\0'*9 and h[1:4]==(2,183,1)
            and h[5]==64 and h[6]==h[7]==0 and h[8:11]==(64,56,5) and h[11:]==(0,0,0),
            'restricted static ELF header differs')
    segments=[];pages=set();stack=0
    for i in range(h[10]):
        p=PROGRAM.unpack_from(raw,h[5]+i*56)
        kind,flags,offset,va,pa,filesz,memsz,alignment=p
        if kind==0x6474e551:
            require(flags==6 and not any((offset,va,pa,filesz,memsz)) and alignment==16, 'executable/invalid stack')
            stack+=1;continue
        require(kind==1 and flags in (4,5,6) and alignment==PAGE and offset%PAGE==va%PAGE==0
                and va==pa==BASE+offset and offset+filesz<=len(raw) and filesz<=memsz<=MAX_OBJECT and memsz>0,
                'invalid segment, permissions or size')
        covered=set(range(va,align(va+memsz,PAGE),PAGE))
        require(not pages.intersection(covered), 'overlapping executable pages');pages.update(covered)
        segments.append({'flags':flags,'offset':offset,'va':va,'filesz':filesz,'memsz':memsz})
    require(stack==1 and len(segments)==4 and [s['flags'] for s in segments]==[4,5,4,6]
            and any(s['flags']==5 and s['va']<=h[4]<s['va']+s['filesz'] for s in segments), 'entry outside executable bytes')
    return segments


SOURCE_PINS={'roles_and_image.inc': '8bfac2dd11b19e7e1620560e107ca7d2b52312c21a2cb71af6bfc70433bc547e', 'core_support.inc': '17a4538be13f27bafe321e5b7a0ce2c61dc4613e9bf52d57cb347d60620e725d', 'launch_support.inc': 'a2728cccdf3643763ba408c7091aa5350243422c992db0a8f17df092d7173b63', 'host_recv.inc': '179b8a9583afbb241a74ed3191d85f7b7169bacd882982dbf6912a31f28e454c', 'keeper.c': 'd117b33f7e8a38864846e710df41d0491ce058c3099b1eaee66ad819ece035a2', 'output_validate.inc': '2a23706a03c3ec8f7d99ab0dff436107adc2cb313c1ef0934754eb0cac9539fe', 'parent_ipc.inc': '6a171f44715530e61bb494aa6afb33415c98596d1dd62acc815e6ce7af9b2add', 'keeper_identity.inc': '6e10d0644655fd2bcae5b9f3ac8fd38bf9c4b27a38453fefc6bdddb7ee8d2241', 'host_control.inc': '45580846e99f84b0b085ec536da493c54dcb59f208dd163a35d3cc8d83a0f2ac'}

def build(destination):
    def check():
        for name,digest in SOURCE_PINS.items():require(sha256(read_file(H/name,65536)).hexdigest()==digest,'worker source changed: '+name)
    check();out=PrivateDirectory(destination)
    try:
        out.put('entry.s',ENTRY_SOURCE)
        argv=['/usr/bin/xcrun','clang','-target','aarch64-linux-gnu','-std=c11','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-Wall','-Wextra','-Werror','-c',str(H/'keeper.c'),'-o',str(out.path/'worker.o')]
        result=subprocess.run(argv,capture_output=True,text=True,umask=0o077);require(result.returncode==0,'static child compile failed: '+result.stderr[:2000])
        entry_argv=['/usr/bin/xcrun','clang','-target','aarch64-linux-gnu','-c',str(out.path/'entry.s'),'-o',str(out.path/'entry.o')]
        result=subprocess.run(entry_argv,capture_output=True,text=True,umask=0o077);require(result.returncode==0,'entry compile failed')
        raw,report=link_objects([('worker.o',read_file(out.path/'worker.o',MAX_OBJECT)),('entry.o',read_file(out.path/'entry.o',MAX_OBJECT))],worker_symbol='fx3_keeper_run');check()
        report.update(role='own standalone keeper with private host control',source_pins=SOURCE_PINS,build_argv=argv,entry_argv=entry_argv,
            segment_alignment=65536,ADRP_instruction_page=4096,shared_library_or_constructor_or_Sony_loader_required=False,
            actual_target_exec_or_inherited_FDs_verified=False,parent_has_pinned_image_before_exec=False)
        out.put('worker.elf',raw);out.put('build.json',encode(report));return report
    finally:out.close()

if __name__=='__main__':
    import json
    print(json.dumps(build(sys.argv[1]),sort_keys=True))
