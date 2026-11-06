"""Restricted static ELF construction for our two pinned worker sources only.

No linker installation, native loader, firmware execution or camera operation.
Unsupported object forms/relocations fail closed; this is not a general linker.
"""
from hashlib import sha256
from pathlib import Path
import struct
import subprocess
from .files import read_file, require, encode
from .capture import PrivateDirectory, FALSE_FLAGS

PAGE=4096
BASE=0x400000
HEADER=struct.Struct('<16sHHIQQQIHHHHHH')
SECTION=struct.Struct('<IIQQQQIIQQ')
SYMBOL=struct.Struct('<IBBHQQ')
RELA=struct.Struct('<QQq')
PROGRAM=struct.Struct('<IIQQQQQQ')
SOURCE_SHA='22d6e613fb2c33861eac93653c7148e34ad22dd3b5b14ac0d4c75d5b903efb29'
ENTRY_SOURCE=(b'.section .text\n.global _start\n.type _start,%function\n_start:\n'
              b'    bl fx3_p1_read_window\n    mov x8, #93\n    svc #0\n    b .\n'
              b'.size _start, .-_start\n.section .note.GNU-stack,"",%progbits\n')
MAX_OBJECT=4*1024*1024
RELOCATIONS={275:'ADR_PREL_PG_HI21',277:'ADD_ABS_LO12_NC',286:'LDST64_ABS_LO12_NC',
             299:'LDST128_ABS_LO12_NC',283:'CALL26'}


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
    if kind==275:
        require(word&0x9f000000==0x90000000, 'ADRP opcode mismatch')
        value=((target&-PAGE)-(place&-PAGE))//PAGE
        require(-(1<<20)<=value<(1<<20), 'ADRP out of range')
        v=value&0x1fffff
        result=(word&~((3<<29)|(0x7ffff<<5)))|((v&3)<<29)|((v>>2)<<5)
        signed=((result>>29)&3)|(((result>>5)&0x7ffff)<<2)
        if signed&(1<<20):signed-=1<<21
        require((place&-PAGE)+signed*PAGE==target&-PAGE, 'ADRP roundtrip differs')
    elif kind==277:
        require(word&0xffc00000==0x91000000, 'unshifted ADD64 opcode mismatch')
        result=(word&~(0xfff<<10))|((target&0xfff)<<10)
        require((result>>10)&0xfff==target&0xfff, 'ADD roundtrip differs')
    elif kind in (286,299):
        scale=8 if kind==286 else 16
        if scale==8:require(word&0xff800000 in (0xf9000000,0xfd000000), 'LDST64 opcode mismatch')
        else:require(word&0x3f800000==0x3d800000, 'LDST128 opcode mismatch')
        require(target%scale==0, 'LDST target alignment mismatch')
        result=(word&~(0xfff<<10))|(((target&0xfff)//scale)<<10)
        require(((result>>10)&0xfff)*scale==target&0xfff, 'LDST roundtrip differs')
    elif kind==283:
        require(word&0xfc000000==0x94000000, 'CALL26 opcode mismatch')
        value=target-place;require(value%4==0 and -(1<<27)<=value<(1<<27), 'CALL26 out of range')
        result=(word&0xfc000000)|((value//4)&0x3ffffff)
        signed=result&0x3ffffff
        if signed&(1<<25):signed-=1<<26
        require(place+signed*4==target, 'CALL26 roundtrip differs')
    else:raise ValueError('unsupported AArch64 relocation')
    return result


def link_objects(raw_objects):
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
                require(s['name']=='fx3_p1_read_window', 'external import rejected');continue
            require(binding==1 and s['info']&15==2 and s['name'] in ('_start','fx3_p1_read_window')
                    and (oi,s['section']) in placements and s['name'] not in globals_, 'unexpected global definition')
            location=placements[(oi,s['section'])]
            require(location['flags']==5 and s['value']+s['bytes']<=location['bytes'], 'global function outside code')
            globals_[s['name']]=(oi,s)
    require(set(globals_)=={'_start','fx3_p1_read_window'}, 'missing entry or worker function')
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


def build_worker(destination):
    tool=Path(__file__).resolve().parents[1]
    source=tool/'native/fx3_p1_reader.c';entry=tool/'native/entry.S'
    require(sha256(read_file(source,65536)).hexdigest()==SOURCE_SHA and read_file(entry,1024)==ENTRY_SOURCE,
            'worker or explicit entry source pin differs')
    directory=PrivateDirectory(destination)
    try:
        directory.put('plan.json',encode({'worker_source_sha256':SOURCE_SHA,'entry_source_sha256':sha256(ENTRY_SOURCE).hexdigest(),
                                         'camera_operations':0, **FALSE_FLAGS}))
        builds=[];objects=[]
        for path,name in ((source,'worker.o'),(entry,'entry.o')):
            out=directory.path/name;require(not out.exists(), 'object output already exists')
            argv=['/usr/bin/xcrun','clang','-target','aarch64-linux-gnu','-O2','-ffreestanding','-fno-builtin',
                  '-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables',
                  '-Wall','-Wextra','-Werror','-c',str(path),'-o',str(out)]
            result=subprocess.run(argv,text=True,capture_output=True,umask=0o077)
            require(result.returncode==0, 'cross-compile failed: '+result.stderr[:512])
            data=read_file(out,MAX_OBJECT);objects.append((name,data));builds.append({'argv':argv,'sha256':sha256(data).hexdigest()})
        raw,report=link_objects(objects)
        require(sha256(read_file(source,65536)).hexdigest()==SOURCE_SHA and read_file(entry,1024)==ENTRY_SOURCE,
                'source changed during build')
        directory.put('worker.elf',raw)
        require(read_file(directory.path/'worker.elf',MAX_OBJECT)==raw, 'linked file readback differs')
        report['builds']=builds;directory.put('link.json',encode(report))
        return report
    finally:directory.close()
