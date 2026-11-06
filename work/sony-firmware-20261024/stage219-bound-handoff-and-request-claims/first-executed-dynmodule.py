"""Pinned own-module ET_DYN builder. No native loader or camera backend."""
from pathlib import Path
from hashlib import sha256
import struct,subprocess
import sys
H=Path(__file__).resolve().parent;ROOT=H.parents[2];TOOL=ROOT/'outputs/fx3-recovery-adapter'
sys.path.insert(0,str(TOOL))
from fx3_recovery import elflink as L
from fx3_recovery.files import require,read_file,encode
from fx3_recovery.capture import PrivateDirectory,FALSE_FLAGS
from fx3_recovery import boot_worker as B
PAGE=65536
EXPORTS=('fx3_boot_read_window','fx3_module_status')
NAMES=('', '.text','.rodata','.init_array','.dynamic','.bss','.dynsym','.dynstr','.hash','.rela.dyn','.shstrtab')
FLAGS={'.text':6,'.rodata':2,'.init_array':3,'.dynamic':3,'.bss':3,'.dynsym':2,'.dynstr':2,'.hash':2,'.rela.dyn':2,'.shstrtab':0}
TYPES={'.text':1,'.rodata':1,'.init_array':14,'.dynamic':6,'.bss':8,'.dynsym':11,'.dynstr':3,'.hash':5,'.rela.dyn':4,'.shstrtab':3}
# Filled from the reviewed source, not inferred from a supplied object.
MODULE_SHA='0cb09f2ccfe6f7dedaaa031ec1ffe1c1ff936b7b64779be2ff0603bcdc17ad8f'
DYNAMIC_TAGS=(4,5,6,10,11,7,8,9,25,27,0)


def align(n,a):
    require(type(a) is int and 0<a<=PAGE and not a&(a-1),'bad alignment')
    return (n+a-1)&-a


class Object:
    def __init__(self,raw):
        require(type(raw) is bytes and 64<=len(raw)<=L.MAX_OBJECT,'object byte size')
        h=L.HEADER.unpack_from(raw)
        require(type(raw) is bytes and 64<=len(raw)<=L.MAX_OBJECT and h[0]==b'\x7fELF\x02\x01\x01'+b'\0'*9
                and h[1:4]==(1,183,1) and h[4]==h[5]==h[7]==h[10]==0 and h[8]==64
                and h[11]==64 and 0<h[12]<=64 and h[13]<h[12] and h[6]+64*h[12]<=len(raw),'unexpected object header')
        self.raw=raw;self.sections=[]
        for i in range(h[12]):
            fields=L.SECTION.unpack_from(raw,h[6]+i*64)
            row=dict(zip(('name_offset','type','flags','va','offset','bytes','link','info','align','entry_bytes'),fields));row['index']=i
            require(row['bytes']<=L.MAX_OBJECT and (row['type']==8 or row['offset']+row['bytes']<=len(raw)),'object section bounds')
            self.sections.append(row)
        names=self.sections[h[13]];require(names['type']==3,'section names missing');strings=raw[names['offset']:names['offset']+names['bytes']]
        for s in self.sections:
            s['name']=L.cstring(strings,s['name_offset']);require(s['type'] not in (6,9,11,15,16),'imports/REL/destructors unsupported')
            if s['flags']&2:
                require(s['type'] in (1,8,14) and not s['flags']&0x400 and not (s['flags']&1 and s['flags']&4),'unsupported allocated section')
                require(s['name'].startswith(('.text','.rodata','.bss')) or s['name']=='.init_array','unexpected module data')
                align(0,s['align'] or 1)
                if s['name'].startswith('.text'):require(s['type']==1 and s['flags']==6,'text permissions differ')
                elif s['name'].startswith('.rodata'):require(s['type']==1 and s['flags']&7==2 and not s['flags']&~50,'readonly constant permissions differ')
                elif s['name'].startswith('.bss'):require(s['type']==8 and s['flags']==3,'BSS permissions differ')
                if s['flags']&4:require(s['align']>=4 and s['bytes']%4==0,'unaligned module code')
                if s['type']==14:require(s['name']=='.init_array' and s['flags']==3 and s['bytes']==8 and s['align']==8,'only one init pointer allowed')
        tables=[x for x in self.sections if x['type']==2];require(len(tables)==1,'one symbol table required');table=tables[0]
        require(table['entry_bytes']==24 and table['bytes']%24==0 and table['link']<len(self.sections),'bad symbols')
        names=self.sections[table['link']];require(names['type']==3,'bad symbol strings');strings=raw[names['offset']:names['offset']+names['bytes']]
        self.symbols=[]
        for at in range(table['offset'],table['offset']+table['bytes'],24):
            n,info,other,section,value,size=L.SYMBOL.unpack_from(raw,at)
            self.symbols.append(dict(name=L.cstring(strings,n),info=info,other=other,section=section,value=value,bytes=size))
        require(all(x['section']!=0 for x in self.symbols[1:]),'external/undefined symbol rejected')
        globals_=[x for x in self.symbols if x['info']>>4]
        require(len(globals_)==2 and {x['name'] for x in globals_}==set(EXPORTS)
                and all(x['info']==0x12 and x['other']==0 for x in globals_),'unexpected export or binding')
        self.relocations=[]
        for s in self.sections:
            if s['type']!=4:continue
            require(s['entry_bytes']==24 and s['bytes']%24==0 and s['link']==table['index'] and s['info']<len(self.sections),'bad RELA section')
            target=self.sections[s['info']];require(target['flags']&2 and target['type'] in (1,14),'bad relocation owner')
            for at in range(s['offset'],s['offset']+s['bytes'],24):
                off,info,addend=L.RELA.unpack_from(raw,at);kind=info&0xffffffff;width=8 if target['type']==14 else 4
                require(info>>32<len(self.symbols) and off%width==0 and off+width<=target['bytes'],'relocation bounds')
                require(kind==257 if target['type']==14 else kind in L.RELOCATIONS,'unsupported module relocation')
                self.relocations.append(dict(section=target['index'],offset=off,type=kind,symbol=info>>32,addend=addend))
        require(len(self.relocations)<=1024 and sum(x['type']==257 for x in self.relocations)==1,'one init ABS64 required')


def link(raw):
    obj=Object(raw);placements={};group_data={};group_sizes={}
    for group,base in [('text',0x10000),('rodata',0x20000),('bss',0x40000),('init_array',0x30000)]:
        content=bytearray();mem=0
        for s in obj.sections:
            if not s['flags']&2 or not s['bytes']:continue
            actual='init_array' if s['type']==14 else 'bss' if s['type']==8 else 'text' if s['flags']&4 else 'rodata'
            if actual!=group:continue
            mem=align(mem,s['align'] or 1);placements[s['index']]=dict(va=base+mem,offset=base+mem,bytes=s['bytes'],group=group,name=s['name'])
            if s['type']!=8:
                content.extend(b'\0'*(mem-len(content)));content.extend(raw[s['offset']:s['offset']+s['bytes']])
            mem+=s['bytes']
        require(mem>0 and mem<=2*PAGE if group=='bss' else 0<mem<=PAGE,'missing/oversized group')
        group_data[group]=content;group_sizes[group]=mem
    require(group_sizes['init_array']==8 and group_data['init_array']==bytes(8),'unreviewed initializer slot')
    exports={s['name']:placements[s['section']]['va']+s['value'] for s in obj.symbols if s['name'] in EXPORTS}
    init=[s for s in obj.symbols if s['name']=='fx3_module_init'];require(len(init)==1,'initializer function missing');init=init[0]
    require(init['info']&15==2 and placements[init['section']]['group']=='text','initializer must be local code')
    init_va=placements[init['section']]['va']+init['value']
    output=bytearray(0x40000);relocations=[];runtime=[];changed=set()
    for group,base in [('text',0x10000),('rodata',0x20000),('init_array',0x30000)]:output[base:base+len(group_data[group])]=group_data[group]
    for r in obj.relocations:
        loc=placements[r['section']];s=obj.symbols[r['symbol']];require(s['section'] in placements,'nonallocated relocation target')
        target=placements[s['section']];relative=s['value']+r['addend'];require(0<=relative<target['bytes'],'relocation target bounds')
        va=target['va']+relative;at=loc['offset']+r['offset'];width=8 if r['type']==257 else 4
        require(not changed.intersection(range(at,at+width)),'overlapping relocation');changed.update(range(at,at+width))
        if r['type']==257:
            require(loc['group']=='init_array' and at==0x30000 and va==init_va,'unreviewed automatic entry')
            runtime.append((at,1027,va));continue
        before=struct.unpack_from('<I',output,at)[0];after=L.relocate(before,r['type'],at,va);struct.pack_into('<I',output,at,after)
        relocations.append(dict(kind=L.RELOCATIONS[r['type']],file_offset=at,target=va,before=before,after=after))
    for s in obj.sections:
        if s['index'] not in placements or s['type']==8:continue
        p=placements[s['index']];before=raw[s['offset']:s['offset']+s['bytes']];after=output[p['offset']:p['offset']+s['bytes']]
        require(all(a==b or p['offset']+i in changed for i,(a,b) in enumerate(zip(before,after))),'unrecorded source mutation')
    # Immutable metadata follows constants; pointer targets remain relative VAs.
    cursor=align(0x20000+group_sizes['rodata'],8);metadata={};dynstr=b'\0'+b'\0'.join(s.encode() for s in EXPORTS)+b'\0'
    dynsym=bytes(24)
    for name in EXPORTS:
        symbol=next(s for s in obj.symbols if s['name']==name)
        require(placements[symbol['section']]['group']=='text','export outside code')
        dynsym+=L.SYMBOL.pack(dynstr.index(name.encode()+b'\0'),0x12,0,1,exports[name],symbol['bytes'])
    bodies={'.dynstr':dynstr,'.dynsym':dynsym,'.hash':struct.pack('<6I',1,3,1,0,2,0),'.rela.dyn':b''.join(L.RELA.pack(*x) for x in runtime)}
    for name in ('.dynstr','.dynsym','.hash','.rela.dyn'):
        data=bodies[name];cursor=align(cursor,8);metadata[name]=(cursor,len(data));output[cursor:cursor+len(data)]=data;cursor+=len(data)
    require(cursor<=0x30000,'metadata overflow')
    values={4:metadata['.hash'][0],5:metadata['.dynstr'][0],6:metadata['.dynsym'][0],10:len(dynstr),11:24,
            7:metadata['.rela.dyn'][0],8:24,9:24,25:0x30000,27:8,0:0}
    dynamic=b''.join(struct.pack('<qQ',tag,values[tag]) for tag in DYNAMIC_TAGS);output[0x30008:0x30008+len(dynamic)]=dynamic
    ro_end=cursor;shstr=b'\0'+b'\0'.join(n.encode() for n in NAMES[1:])+b'\0';shstr_at=len(output);output.extend(shstr);shoff=align(len(output),8);output.extend(bytes(shoff-len(output)))
    specs={'.text':(0x10000,group_sizes['text'],0,0,4,0),'.rodata':(0x20000,group_sizes['rodata'],0,0,16,0),
           '.init_array':(0x30000,8,0,0,8,8),'.dynamic':(0x30008,len(dynamic),7,0,8,16),'.bss':(0x40000,group_sizes['bss'],0,0,16,0),
           '.dynsym':(*metadata['.dynsym'],7,1,8,24),'.dynstr':(*metadata['.dynstr'],0,0,1,0),'.hash':(*metadata['.hash'],6,0,4,4),
           '.rela.dyn':(*metadata['.rela.dyn'],6,0,8,24),'.shstrtab':(shstr_at,len(shstr),0,0,1,0)}
    output.extend(bytes(64))
    for name in NAMES[1:]:
        off,size,ln,info,alignment,entry=specs[name];va=off if FLAGS[name]&2 else 0
        output.extend(L.SECTION.pack(shstr.index(name.encode()+b'\0'),TYPES[name],FLAGS[name],va,off,size,ln,info,alignment,entry))
    ph=[(1,4,0,0,0,PAGE,PAGE,PAGE),(1,5,0x10000,0x10000,0x10000,group_sizes['text'],group_sizes['text'],PAGE),
        (1,4,0x20000,0x20000,0x20000,ro_end-0x20000,ro_end-0x20000,PAGE),
        (1,6,0x30000,0x30000,0x30000,PAGE,PAGE,PAGE),(1,6,0x40000,0x40000,0x40000,0,group_sizes['bss'],PAGE),
        (2,6,0x30008,0x30008,0x30008,len(dynamic),len(dynamic),8),
        (0x6474e552,4,0x30000,0x30000,0x30000,PAGE,PAGE,1),(0x6474e551,6,0,0,0,0,0,16)]
    output[:64]=L.HEADER.pack(b'\x7fELF\x02\x01\x01'+b'\0'*9,3,183,1,0,64,shoff,0,64,56,len(ph),64,len(NAMES),10)
    for i,p in enumerate(ph):L.PROGRAM.pack_into(output,64+56*i,*p)
    raw=bytes(output);report=inspect(raw);report.update(object_sha256=sha256(obj.raw).hexdigest(),link_relocations=relocations,
        initializer_symbol='fx3_module_init',initializer_va=init_va,initializer_bytes=init['bytes'],initializer_code_sha256=sha256(output[init_va:init_va+init['bytes']]).hexdigest())
    return raw,report


def inspect(raw):
    require(type(raw) is bytes and 0x40000<len(raw)<0x42000,'restricted module size')
    h=L.HEADER.unpack_from(raw)
    require(h[0]==b'\x7fELF\x02\x01\x01'+b'\0'*9 and h[1:6]==(3,183,1,0,64) and h[7:]==(0,64,56,8,64,11,10),'restricted ET_DYN header')
    require(h[6]%8==0 and h[6]+11*64==len(raw),'module section table bounds')
    ph=[L.PROGRAM.unpack_from(raw,64+i*56) for i in range(8)];segments=[]
    for i,p in enumerate(ph[:5]):
        kind,flags,off,va,pa,fs,mem,alignment=p
        require(kind==1 and flags==(4,5,4,6,6)[i] and off==va==pa==i*PAGE and alignment==PAGE
                and 0<=fs<=mem<=2*PAGE and mem>0 and off+fs<=len(raw),'load permissions/layout/size')
        require(i==4 or fs==mem,'unexpected BSS group');segments.append(dict(flags=flags,offset=off,va=va,filesz=fs,memsz=mem))
    require(ph[0][5:7]==(PAGE,PAGE) and ph[3][5:7]==(PAGE,PAGE) and ph[4][5]==0,'header/relro/BSS layout')
    require(ph[5][:5]==(2,6,0x30008,0x30008,0x30008) and ph[5][5:]==(176,176,8),'dynamic segment layout')
    require(ph[6]==(0x6474e552,4,0x30000,0x30000,0x30000,PAGE,PAGE,1) and ph[7]==(0x6474e551,6,0,0,0,0,0,16),'RELRO/stack permissions')
    secs=[L.SECTION.unpack_from(raw,h[6]+i*64) for i in range(11)];require(secs[0]==(0,)*10,'nonzero null section')
    sn=secs[10];require(sn[1:5]==(3,0,0,0x40000) and sn[4]+sn[5]<=h[6],'section strings layout');strings=raw[sn[4]:sn[4]+sn[5]]
    named={}
    for index,s in enumerate(secs[1:],1):
        name=L.cstring(strings,s[0]);require(name==NAMES[index] and s[1]==TYPES[name] and s[2]==FLAGS[name],'section type/name/permission differs')
        require(s[5]>0 and s[5]<=2*PAGE and (s[1]==8 or s[4]+s[5]<=len(raw)),'section bounds')
        if s[2]&2:
            require(s[3]==s[4] and any(p['va']<=s[3] and s[3]+s[5]<=p['va']+p['memsz'] for p in segments),'allocated section outside load')
        named[name]=s
    for name,off,size,link,info,entry in [('.text',0x10000,ph[1][5],0,0,0),('.init_array',0x30000,8,0,0,8),('.dynamic',0x30008,176,7,0,16),('.bss',0x40000,ph[4][6],0,0,0)]:
        sec=named[name];require((sec[3],sec[4],sec[5],sec[6],sec[7],sec[9])==(off,off,size,link,info,entry),'fixed section layout differs')
    for name,link,info,entry in [('.dynsym',7,1,24),('.dynstr',0,0,0),('.hash',6,0,4),('.rela.dyn',6,0,24)]:
        sec=named[name];require((sec[6],sec[7],sec[9])==(link,info,entry) and 0x20000<=sec[3] and sec[3]+sec[5]<=0x20000+ph[2][5],'readonly metadata location/link differs')
    require(named['.rodata'][3]==named['.rodata'][4]==0x20000,'rodata location differs')
    ranges=sorted((named[n][3],named[n][3]+named[n][5]) for n in ('.rodata','.dynstr','.dynsym','.hash','.rela.dyn'))
    require(all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:])),'overlapping readonly metadata')
    tags=[struct.unpack_from('<qQ',raw,0x30008+16*i) for i in range(11)];require(tuple(x[0] for x in tags)==DYNAMIC_TAGS,'unsupported/reordered dynamic tags');d=dict(tags)
    require(d[0]==0 and d[11]==d[8]==d[9]==24 and d[25]==0x30000 and d[27]==8,'dynamic sizes/init layout')
    for tag,name in [(4,'.hash'),(5,'.dynstr'),(6,'.dynsym'),(7,'.rela.dyn')]:require(d[tag]==named[name][3],'dynamic pointer differs')
    require(d[10]==named['.dynstr'][5] and named['.dynsym'][5]==72 and named['.hash'][5]==24 and named['.rela.dyn'][5]==24,'dynamic metadata bounds')
    require(raw[d[4]:d[4]+24]==struct.pack('<6I',1,3,1,0,2,0),'unexpected SysV export hash')
    ds=raw[d[5]:d[5]+d[10]];require(ds==b'\0'+b'\0'.join(x.encode() for x in EXPORTS)+b'\0','dynamic names differ')
    require(raw[d[6]:d[6]+24]==bytes(24),'null dynsym differs');exports={}
    for i,name in enumerate(EXPORTS,1):
        n,info,other,section,value,size=L.SYMBOL.unpack_from(raw,d[6]+24*i)
        require(L.cstring(ds,n)==name and (info,other,section)==(0x12,0,1) and size>0
                and 0x10000<=value and value+size<=0x10000+ph[1][5],'unexpected export/import')
        exports[name]=dict(va=value,bytes=size)
    offset,info,addend=L.RELA.unpack_from(raw,d[7]);require(offset==0x30000 and info==1027 and 0x10000<=addend<0x10000+ph[1][5]
        and raw[0x30000:0x30008]==bytes(8),'only own init-array RELATIVE permitted')
    return dict(schema='fx3-restricted-own-ET_DYN-v1',sha256=sha256(raw).hexdigest(),bytes=len(raw),segments=segments,
        exports=exports,dynamic_tags=tags,runtime_relocations=[dict(offset=offset,type=1027,symbol=0,addend=addend)],
        init_array=[offset],has_DT_NEEDED_or_imports=False,initialization_behavior_verified_by_inspector=False,
        constructor_effect_authenticated_by_metadata=False,child_identity_guard_implemented=False,
        actual_Sony_loader_acceptance_verified=False,actual_body_or_loaded_driver_identity_verified=False,
        camera_transfer_or_launch_backend=False,camera_operations=0,**FALSE_FLAGS)


def build(destination):
    source=H/'boot_module.c';worker=TOOL/'native/fx3_boot_reader.c'
    require(sha256(read_file(source,65536)).hexdigest()==MODULE_SHA and sha256(read_file(worker,65536)).hexdigest()==B.SOURCE_SHA,'fixed module/worker source differs')
    inner=H/'inner_boot_reader.c'
    require(sha256(read_file(inner,65536)).hexdigest()=='a1459db35501716dc414b45479aaa25c1ddb252ec440bd24258c4db7dbd78683','derived inner source differs')
    require(sha256(read_file(H/'handoff_impl.inc',65536)).hexdigest()=='d847b27881257858bde10e15c7139cc69de8cced8b891f9440f061d189e27a4e','handoff implementation differs')
    out=PrivateDirectory(destination)
    try:
        argv=['/usr/bin/xcrun','clang','-target','aarch64-linux-gnu','-std=c11','-O2','-fPIC','-fvisibility=hidden','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-Wall','-Wextra','-Werror','-c',str(source),'-o',str(out.path/'module.o')]
        result=subprocess.run(argv,text=True,capture_output=True,umask=0o077);require(result.returncode==0,'PIC compile failed: '+result.stderr[:512])
        raw,report=link(read_file(out.path/'module.o',L.MAX_OBJECT));report.update(module_source_sha256=MODULE_SHA,worker_source_sha256=B.SOURCE_SHA,build_argv=argv,source_initializer_calls_worker_or_syscall=False,fixed_shell_process_filter_implemented=True,exclusive_request_attestation_verified=False,request_binding_and_pending_claims_implemented=True,cross_request_global_exclusion_implemented=False)
        require(sha256(read_file(source,65536)).hexdigest()==MODULE_SHA and sha256(read_file(worker,65536)).hexdigest()==B.SOURCE_SHA and sha256(read_file(inner,65536)).hexdigest()=='a1459db35501716dc414b45479aaa25c1ddb252ec440bd24258c4db7dbd78683','source drifted during build')
        out.put('boot-module.so',raw);require(read_file(out.path/'boot-module.so',L.MAX_OBJECT)==raw,'module readback differs')
        out.put('build.json',encode(report));return report
    finally:out.close()


if __name__=='__main__':
    import json
    print(json.dumps(build(sys.argv[1]),sort_keys=True))
