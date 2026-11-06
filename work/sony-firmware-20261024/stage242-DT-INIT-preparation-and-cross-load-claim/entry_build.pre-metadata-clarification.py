"""Restricted static ELF construction for our two pinned worker sources only.

No linker installation, native loader, firmware execution or camera operation.
Unsupported object forms/relocations fail closed; this is not a general linker.
"""
from hashlib import sha256
from pathlib import Path
import sys
H=Path(__file__).resolve().parent;ROOT=H.parents[2]
sys.path.insert(0,str(ROOT/'outputs/fx3-recovery-adapter'))
from fx3_recovery import elflink as LEGACY
import struct
import subprocess
from fx3_recovery.files import read_file, require, encode
from fx3_recovery.capture import PrivateDirectory, FALSE_FLAGS

PAGE=65536
BASE=0
HEADER=struct.Struct('<16sHHIQQQIHHHHHH')
SECTION=struct.Struct('<IIQQQQIIQQ')
SYMBOL=struct.Struct('<IBBHQQ')
RELA=struct.Struct('<QQq')
PROGRAM=struct.Struct('<IIQQQQQQ')
ENTRY_SOURCE=(b'.section .text\n.global _start\n.type _start,%function\n_start:\n'
              b'    bl fx3_isolated_collector_core\n    mov x8, #93\n    svc #0\n    b .\n'
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


def link_objects(raw_objects):
    allowed={'_start','fx3_bridge_start','fx3_parent_receiver','fx3_isolated_collector_core','fx3_bridge_image_id','fx3_entry_init','fx3_entry_state','fx3_entry_reason'}
    require(type(raw_objects) is list and len(raw_objects)==5, 'only own parent/collector/bridge/entry objects are supported')
    objects=[Object(raw,name) for name,raw in raw_objects]
    placements={};groups=[];cursor=PAGE
    for flags in (5,4,6):
        content=bytearray(4096) if flags==6 else bytearray();mem=len(content);members=[]
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
                require(s['name'] in allowed or s['name']=='__capsule_base', 'external import rejected');continue
            require(binding==1 and s['info']&15==2 and s['name'] in allowed
                    and (oi,s['section']) in placements and s['name'] not in globals_, 'unexpected global definition')
            location=placements[(oi,s['section'])]
            require(location['flags']==5 and s['value']+s['bytes']<=location['bytes'], 'global function outside code')
            globals_[s['name']]=(oi,s)
    require(set(globals_)==allowed, 'missing entry or worker function')
    records=[];changed=set()
    for oi,obj in enumerate(objects):
        for r in obj.relocations:
            symbol=obj.symbols[r['symbol']];owner=oi
            location=placements[(oi,r['section'])]
            if symbol['section']==0 and symbol['name']=='__capsule_base':
                require(r['addend']==0 and r['type'] in (275,277),'header-base reference form differs')
                target=BASE;defined={'flags':4}
            else:
                if symbol['section']==0:
                    require(symbol['name'] in globals_, 'unresolved symbol');owner,symbol=globals_[symbol['name']]
                require((owner,symbol['section']) in placements, 'absolute/common/nonallocated symbol rejected')
                defined=placements[(owner,symbol['section'])];relative=symbol['value']+r['addend']
                require(0<=relative<defined['bytes'], 'relocation target outside allocated section')
                target=defined['va']+relative
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
    ph.extend((1,g['flags'],g['offset'],g['va'],g['va'],PAGE,PAGE,PAGE) for g in groups)
    init_oi,init_symbol=globals_['fx3_entry_init']
    initializer=placements[(init_oi,init_symbol['section'])]['va']+init_symbol['value']
    dynamic=[(4,8192),(5,8232),(6,8208),(10,1),(11,24),(12,initializer),(0,0)]
    for i,item in enumerate(dynamic):struct.pack_into('<qQ',output,3*PAGE+i*16,*item)
    output[8192:8208]=struct.pack('<4I',1,1,0,0)
    output[8208:8232]=bytes(24);output[8232]=0
    cfg=bytearray(256);cfg[:16]=b'FX3ENTRYCFGv2'.ljust(16,b'\0')
    struct.pack_into('<IIII',cfg,16,2,1,1,1);cfg[32:48]=b'\xbb'*16;cfg[48:80]=b'\xcc'*32;cfg[80:112]=b'\xdd'*32
    cfg[112:144]=bytes.fromhex('0bf01a5c42ea6a7591d30954fea8448d65c45dae28ec2c20b6769e12f188b1b4')
    struct.pack_into('<QQI',cfg,144,60000000000,262144,1)
    import zlib
    struct.pack_into('<I',cfg,252,zlib.crc32(cfg[:252]));output[4096:4352]=cfg
    ph.append((2,6,3*PAGE,3*PAGE,3*PAGE,112,112,8))
    ph.append((0x6474e551,6,0,0,0,0,0,16))
    ident=b'\x7fELF\x02\x01\x01'+b'\0'*9
    output[:64]=HEADER.pack(ident,3,183,1,entry,64,0,0,64,56,len(ph),0,0,0)
    for i,p in enumerate(ph):PROGRAM.pack_into(output,64+56*i,*p)
    raw=bytes(output);segments=read_executable(raw)
    return raw,{'schema':'fx3-own-worker-static-link-v1','entry':entry,'segments':segments,
        'objects':[{'name':o.name,'sha256':sha256(o.raw).hexdigest()} for o in objects],
        'placements':list(placements.values()),'global_offsets':{n:placements[(oi,s['section'])]['va']+s['value']-BASE for n,(oi,s) in globals_.items()},'relocations':records,'sha256':sha256(raw).hexdigest(),'bytes':len(raw),
        'runtime_loader_or_imports':False,'AArch64_machine_code_execution_verified_by_builder':False,'camera_operations':0,
        'camera_launch_or_transfer_verified':False, **FALSE_FLAGS}


def read_executable(raw):
    require(type(raw) is bytes and 4096<=len(raw)<=MAX_OBJECT, 'ELF executable size limit')
    h=HEADER.unpack_from(raw)
    require(h[0]==b'\x7fELF\x02\x01\x01'+b'\0'*9 and h[1:4]==(3,183,1)
            and h[5]==64 and h[6]==h[7]==0 and h[8:11]==(64,56,6) and h[11:]==(0,0,0),
            'restricted static ELF header differs')
    segments=[];pages=set();stack=0
    for i in range(h[10]):
        p=PROGRAM.unpack_from(raw,h[5]+i*56)
        kind,flags,offset,va,pa,filesz,memsz,alignment=p
        if kind==2:
            require((flags,offset,va,pa,filesz,memsz,alignment)==(6,3*PAGE,3*PAGE,3*PAGE,112,112,8),'dynamic layout differs');continue
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


def build(destination):
    out=PrivateDirectory(destination);names=['parent.c','collector.c','bridge.c','front.c'];pins={n:sha256(read_file(H/n,65536)).hexdigest() for n in names+['bridge_job.h','sha_impl.inc','core_support.inc','parent_ipc.inc']}
    entry=(b'.section .text\n.global _start\n.type _start,%function\n_start:\n'
           b'    bl fx3_entry_init\n    bl fx3_entry_state\n'
           b'    mov x8, #93\n    svc #0\n    b .\n'
           b'.size _start, .-_start\n.section .note.GNU-stack,"",%progbits\n')
    try:
        for n in pins:out.put(n,read_file(H/n,65536))
        objects=[];commands=[]
        for n in names:
            obj=n[:-2]+'.o';args=['/usr/bin/xcrun','clang','-target','aarch64-linux-gnu','-std=c11','-O2','-fPIC','-fvisibility=hidden','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-Wall','-Wextra','-Werror','-c',str(out.path/n),'-o',str(out.path/obj)]
            p=subprocess.run(args,capture_output=True,text=True,umask=0o077);out.put(obj+'.stderr.txt',p.stderr.encode());require(p.returncode==0,n+' compile: '+p.stderr[:2000]);commands.append(args);objects.append((obj,read_file(out.path/obj,MAX_OBJECT)))
        out.put('entry.s',entry);args=['/usr/bin/xcrun','clang','-target','aarch64-linux-gnu','-c',str(out.path/'entry.s'),'-o',str(out.path/'entry.o')];p=subprocess.run(args,capture_output=True,text=True,umask=0o077);require(p.returncode==0,'entry assembly: '+p.stderr[:1000]);objects.append(('entry.o',read_file(out.path/'entry.o',MAX_OBJECT)))
        raw,r=link_objects(objects)
        for n,d in pins.items():require(sha256(read_file(H/n,65536)).hexdigest()==d,'source changed during build')
        require(len(raw)==4*PAGE,'unexpected capsule file span');require(all(x['kind'] in ('ADR_PREL_PG_HI21','ADD_ABS_LO12_NC','LDST64_ABS_LO12_NC','LDST128_ABS_LO12_NC','LDST32_ABS_LO12_NC','CALL26') for x in r['relocations']),'nonrebasable relocation')
        r.update(ET_DYN_DT_INIT_zero_argument_entry_present=True,full_file_sha256=sha256(raw).hexdigest(),immutable_image_id=sha256(raw[:3*PAGE]+bytes(PAGE)).hexdigest(),dynamic_tags=[4,5,6,10,11,12,0],source_pins=pins,build_argv=commands,entry_source_sha256=sha256(entry).hexdigest(),all_file_pages_present_except_zero_BSS=True,
                 rebasing_requires_PAGE_alignment=True,header_base_is_only_synthetic_address_symbol=True,
                 real_Sony_loader_execution_or_camera_context_verified=False,full_boot_worker_integrated=False,deployable=False,first_flash_released=False)
        out.put('entry.so',raw);out.put('build.json',encode(r));return r
    finally:out.close()

if __name__=='__main__':
    import json
    r=build(sys.argv[1]);print(json.dumps(dict(sha256=r['sha256'],bytes=r['bytes'],relocations=len(r['relocations']),offsets=r['global_offsets'])))


