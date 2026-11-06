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
PAGE=32768
EXPORTS=('fx3_prepare_state','fx3_prepare_reason')
NAMES=('', '.text','.rodata','.init_array','.dynamic','.bss','.dynsym','.dynstr','.hash','.rela.dyn','.shstrtab')
FLAGS={'.text':6,'.rodata':2,'.init_array':3,'.dynamic':3,'.bss':3,'.dynsym':2,'.dynstr':2,'.hash':2,'.rela.dyn':2,'.shstrtab':0}
TYPES={'.text':1,'.rodata':1,'.init_array':14,'.dynamic':6,'.bss':8,'.dynsym':11,'.dynstr':3,'.hash':5,'.rela.dyn':4,'.shstrtab':3}
# Filled from the reviewed source, not inferred from a supplied object.
MODULE_SHA='e53673ea7e920a143e574009486f1624789b15cb5af5f5459362b865e8dcb4e4'
DYNAMIC_TAGS=(4,5,6,10,11,7,8,9,25,27,0)

RELOCATIONS={**L.RELOCATIONS,285:'LDST32_ABS_LO12_NC'}
def relocate(word,kind,place,target):
    if kind!=285:return L.relocate(word,kind,place,target)
    require(word&0xff800000==0xb9000000,'LDST32 unsigned load/store opcode mismatch')
    require(target%4==0,'LDST32 alignment mismatch')
    result=(word&~(0xfff<<10))|(((target&0xfff)//4)<<10)
    require(((result>>10)&0xfff)*4==target&0xfff,'LDST32 roundtrip differs')
    return result



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
        require(all(x['section']!=0 or x['name']=='__fx3_elf_base' for x in self.symbols[1:]),'external/undefined symbol rejected')
        base=[x for x in self.symbols if x['name']=='__fx3_elf_base'];require(len(base)==1 and base[0]['section']==0 and base[0]['value']==0 and base[0]['other']==2,'fixed hidden linker-provided module base required')
        globals_=[x for x in self.symbols if x['info']>>4 and x['name']!='__fx3_elf_base']
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
                require(kind==257 if target['type']==14 else kind in RELOCATIONS,'unsupported module relocation')
                self.relocations.append(dict(section=target['index'],offset=off,type=kind,symbol=info>>32,addend=addend))
        require(len(self.relocations)<=1024 and sum(x['type']==257 for x in self.relocations)==1,'one init ABS64 required')


def link(raw):
    obj=Object(raw);placements={};group_data={};group_sizes={}
    for group,base in [('text',0x8000),('rodata',0x10000),('bss',0x20000),('init_array',0x18000)]:
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
    output=bytearray(0x20000);relocations=[];runtime=[];changed=set()
    for group,base in [('text',0x8000),('rodata',0x10000),('init_array',0x18000)]:output[base:base+len(group_data[group])]=group_data[group]
    for r in obj.relocations:
        loc=placements[r['section']];s=obj.symbols[r['symbol']];require(s['section'] in placements or s['name']=='__fx3_elf_base','nonallocated relocation target')
        if s['name']=='__fx3_elf_base':
            require(s['section']==0 and s['value']==0 and r['addend']==0 and r['type'] in (275,277),'only fixed base ADRP/ADD allowed');va=0
        else:
            target=placements[s['section']];relative=s['value']+r['addend'];require(0<=relative<target['bytes'],'relocation target bounds');va=target['va']+relative
        at=loc['offset']+r['offset'];width=8 if r['type']==257 else 4
        require(not changed.intersection(range(at,at+width)),'overlapping relocation');changed.update(range(at,at+width))
        if r['type']==257:
            require(loc['group']=='init_array' and at==0x18000 and va==init_va,'unreviewed automatic entry')
            runtime.append((at,1027,va));continue
        before=struct.unpack_from('<I',output,at)[0];after=relocate(before,r['type'],at,va);struct.pack_into('<I',output,at,after)
        relocations.append(dict(kind=RELOCATIONS[r['type']],file_offset=at,target=va,before=before,after=after))
    for s in obj.sections:
        if s['index'] not in placements or s['type']==8:continue
        p=placements[s['index']];before=raw[s['offset']:s['offset']+s['bytes']];after=output[p['offset']:p['offset']+s['bytes']]
        require(all(a==b or p['offset']+i in changed for i,(a,b) in enumerate(zip(before,after))),'unrecorded source mutation')
    # Immutable metadata follows constants; pointer targets remain relative VAs.
    cursor=align(0x10000+group_sizes['rodata'],8);metadata={};dynstr=b'\0'+b'\0'.join(s.encode() for s in EXPORTS)+b'\0'
    dynsym=bytes(24)
    for name in EXPORTS:
        symbol=next(s for s in obj.symbols if s['name']==name)
        require(placements[symbol['section']]['group']=='text','export outside code')
        dynsym+=L.SYMBOL.pack(dynstr.index(name.encode()+b'\0'),0x12,0,1,exports[name],symbol['bytes'])
    bodies={'.dynstr':dynstr,'.dynsym':dynsym,'.hash':struct.pack('<6I',1,3,1,0,2,0),'.rela.dyn':b''.join(L.RELA.pack(*x) for x in runtime)}
    for name in ('.dynstr','.dynsym','.hash','.rela.dyn'):
        data=bodies[name];cursor=align(cursor,8);metadata[name]=(cursor,len(data));output[cursor:cursor+len(data)]=data;cursor+=len(data)
    require(cursor<=0x18000,'metadata overflow')
    values={4:metadata['.hash'][0],5:metadata['.dynstr'][0],6:metadata['.dynsym'][0],10:len(dynstr),11:24,
            7:metadata['.rela.dyn'][0],8:24,9:24,25:0x18000,27:8,0:0}
    dynamic=b''.join(struct.pack('<qQ',tag,values[tag]) for tag in DYNAMIC_TAGS);output[0x18008:0x18008+len(dynamic)]=dynamic
    ro_end=cursor;shstr=b'\0'+b'\0'.join(n.encode() for n in NAMES[1:])+b'\0';shstr_at=len(output);output.extend(shstr);shoff=align(len(output),8);output.extend(bytes(shoff-len(output)))
    specs={'.text':(0x8000,group_sizes['text'],0,0,4,0),'.rodata':(0x10000,group_sizes['rodata'],0,0,16,0),
           '.init_array':(0x18000,8,0,0,8,8),'.dynamic':(0x18008,len(dynamic),7,0,8,16),'.bss':(0x20000,group_sizes['bss'],0,0,16,0),
           '.dynsym':(*metadata['.dynsym'],7,1,8,24),'.dynstr':(*metadata['.dynstr'],0,0,1,0),'.hash':(*metadata['.hash'],6,0,4,4),
           '.rela.dyn':(*metadata['.rela.dyn'],6,0,8,24),'.shstrtab':(shstr_at,len(shstr),0,0,1,0)}
    output.extend(bytes(64))
    for name in NAMES[1:]:
        off,size,ln,info,alignment,entry=specs[name];va=off if FLAGS[name]&2 else 0
        output.extend(L.SECTION.pack(shstr.index(name.encode()+b'\0'),TYPES[name],FLAGS[name],va,off,size,ln,info,alignment,entry))
    ph=[(1,4,0,0,0,PAGE,PAGE,PAGE),(1,5,0x8000,0x8000,0x8000,group_sizes['text'],group_sizes['text'],PAGE),
        (1,4,0x10000,0x10000,0x10000,ro_end-0x10000,ro_end-0x10000,PAGE),
        (1,6,0x18000,0x18000,0x18000,PAGE,PAGE,PAGE),(1,6,0x20000,0x20000,0x20000,0,group_sizes['bss'],PAGE),
        (2,6,0x18008,0x18008,0x18008,len(dynamic),len(dynamic),8),
        (0x6474e552,4,0x18000,0x18000,0x18000,PAGE,PAGE,1),(0x6474e551,6,0,0,0,0,0,16)]
    output[:64]=L.HEADER.pack(b'\x7fELF\x02\x01\x01'+b'\0'*9,3,183,1,0,64,shoff,0,64,56,len(ph),64,len(NAMES),10)
    for i,p in enumerate(ph):L.PROGRAM.pack_into(output,64+56*i,*p)
    raw=bytes(output);report=inspect_layout(raw);report.update(object_sha256=sha256(obj.raw).hexdigest(),link_relocations=relocations,
        initializer_symbol='fx3_module_init',initializer_va=init_va,initializer_bytes=init['bytes'],initializer_code_sha256=sha256(output[init_va:init_va+init['bytes']]).hexdigest())
    return raw,report


def inspect_layout(raw):
    require(type(raw) is bytes and 0x20000<len(raw)<0x22000,'restricted module size')
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
    require(ph[5][:5]==(2,6,0x18008,0x18008,0x18008) and ph[5][5:]==(176,176,8),'dynamic segment layout')
    require(ph[6]==(0x6474e552,4,0x18000,0x18000,0x18000,PAGE,PAGE,1) and ph[7]==(0x6474e551,6,0,0,0,0,0,16),'RELRO/stack permissions')
    secs=[L.SECTION.unpack_from(raw,h[6]+i*64) for i in range(11)];require(secs[0]==(0,)*10,'nonzero null section')
    sn=secs[10];require(sn[1:5]==(3,0,0,0x20000) and sn[4]+sn[5]<=h[6],'section strings layout');strings=raw[sn[4]:sn[4]+sn[5]]
    named={}
    for index,s in enumerate(secs[1:],1):
        name=L.cstring(strings,s[0]);require(name==NAMES[index] and s[1]==TYPES[name] and s[2]==FLAGS[name],'section type/name/permission differs')
        require(s[5]>0 and s[5]<=2*PAGE and (s[1]==8 or s[4]+s[5]<=len(raw)),'section bounds')
        if s[2]&2:
            require(s[3]==s[4] and any(p['va']<=s[3] and s[3]+s[5]<=p['va']+p['memsz'] for p in segments),'allocated section outside load')
        named[name]=s
    for name,off,size,link,info,entry in [('.text',0x8000,ph[1][5],0,0,0),('.init_array',0x18000,8,0,0,8),('.dynamic',0x18008,176,7,0,16),('.bss',0x20000,ph[4][6],0,0,0)]:
        sec=named[name];require((sec[3],sec[4],sec[5],sec[6],sec[7],sec[9])==(off,off,size,link,info,entry),'fixed section layout differs')
    for name,link,info,entry in [('.dynsym',7,1,24),('.dynstr',0,0,0),('.hash',6,0,4),('.rela.dyn',6,0,24)]:
        sec=named[name];require((sec[6],sec[7],sec[9])==(link,info,entry) and 0x10000<=sec[3] and sec[3]+sec[5]<=0x10000+ph[2][5],'readonly metadata location/link differs')
    require(named['.rodata'][3]==named['.rodata'][4]==0x10000,'rodata location differs')
    ranges=sorted((named[n][3],named[n][3]+named[n][5]) for n in ('.rodata','.dynstr','.dynsym','.hash','.rela.dyn'))
    require(all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:])),'overlapping readonly metadata')
    tags=[struct.unpack_from('<qQ',raw,0x18008+16*i) for i in range(11)];require(tuple(x[0] for x in tags)==DYNAMIC_TAGS,'unsupported/reordered dynamic tags');d=dict(tags)
    require(d[0]==0 and d[11]==d[8]==d[9]==24 and d[25]==0x18000 and d[27]==8,'dynamic sizes/init layout')
    for tag,name in [(4,'.hash'),(5,'.dynstr'),(6,'.dynsym'),(7,'.rela.dyn')]:require(d[tag]==named[name][3],'dynamic pointer differs')
    require(d[10]==named['.dynstr'][5] and named['.dynsym'][5]==72 and named['.hash'][5]==24 and named['.rela.dyn'][5]==24,'dynamic metadata bounds')
    require(raw[d[4]:d[4]+24]==struct.pack('<6I',1,3,1,0,2,0),'unexpected SysV export hash')
    ds=raw[d[5]:d[5]+d[10]];require(ds==b'\0'+b'\0'.join(x.encode() for x in EXPORTS)+b'\0','dynamic names differ')
    require(raw[d[6]:d[6]+24]==bytes(24),'null dynsym differs');exports={}
    for i,name in enumerate(EXPORTS,1):
        n,info,other,section,value,size=L.SYMBOL.unpack_from(raw,d[6]+24*i)
        require(L.cstring(ds,n)==name and (info,other,section)==(0x12,0,1) and size>0
                and 0x8000<=value and value+size<=0x8000+ph[1][5],'unexpected export/import')
        exports[name]=dict(va=value,bytes=size)
    offset,info,addend=L.RELA.unpack_from(raw,d[7]);require(offset==0x18000 and info==1027 and 0x8000<=addend<0x8000+ph[1][5]
        and raw[0x18000:0x18008]==bytes(8),'only own init-array RELATIVE permitted')
    return dict(schema='fx3-restricted-own-ET_DYN-v1',sha256=sha256(raw).hexdigest(),bytes=len(raw),segments=segments,
        exports=exports,dynamic_tags=tags,runtime_relocations=[dict(offset=offset,type=1027,symbol=0,addend=addend)],
        init_array=[offset],has_DT_NEEDED_or_imports=False,initialization_behavior_verified_by_inspector=False,
        constructor_effect_authenticated_by_metadata=False,child_identity_guard_implemented=True,
        actual_Sony_loader_acceptance_verified=False,actual_body_or_loaded_driver_identity_verified=False,
        camera_transfer_or_launch_backend=False,camera_operations=0,**FALSE_FLAGS)


SOURCE_PINS={'prepare.c': 'e53673ea7e920a143e574009486f1624789b15cb5af5f5459362b865e8dcb4e4', 'core_support.inc': '17a4538be13f27bafe321e5b7a0ce2c61dc4613e9bf52d57cb347d60620e725d', 'parent_ipc.inc': '2c7db2013151b833f157f8202c7c2a4364ea403e9703d93999d2705e1f376044'}

CONFIG_AT=4096;NORM_AT=4352
WORKER_SHA='c711f6ab13666c45249cc255d2ab09ec283496214d8941d11b9f1569124c47ec'
def fixture_config():
    import zlib
    data=bytearray(256);data[:16]=b'FX3PREPCONFIGv1'.ljust(16,b'\0');struct.pack_into('<IIII',data,16,1,1,1,1)
    data[32:48]=b'\xbb'*16;data[48:80]=b'\xcc'*32;data[80:112]=b'\xdd'*32;data[112:144]=bytes.fromhex(WORKER_SHA)
    struct.pack_into('<QQI',data,144,60_000_000_000,131864,1);struct.pack_into('<I',data,252,zlib.crc32(data[:252]));return bytes(data)
def normalized(raw):
    return raw[:NORM_AT]+bytes(32)+raw[NORM_AT+32:]
def inspect(raw):
    report=inspect_layout(raw);require(raw[CONFIG_AT:CONFIG_AT+256]==fixture_config(),'only fixed synthetic configuration permitted by this host inspector')
    require(raw[NORM_AT:NORM_AT+32]==sha256(normalized(raw)).digest(),'normalized complete image mismatch')
    report.update(normalized_image_sha256=sha256(normalized(raw)).hexdigest(),normalization_field=dict(offset=NORM_AT,bytes=32),embedded_config_offset=CONFIG_AT,
        embedded_config_sha256=sha256(fixture_config()).hexdigest(),expected_worker_sha256=WORKER_SHA,expected_worker_bytes=131864,
        fixed_synthetic_associations_only=True,normalized_self_consistency_is_authentication_or_live_body_attestation=False,
        child_identity_guard_implemented=False,no_child_lifecycle_in_this_component=True,
        full_host_binary_sha256_required_before_any_future_transfer=True,prepare_only_no_child_source_USB_or_firmware_backend=True)
    return report


def build(destination):
    def check():
        for name,digest in SOURCE_PINS.items():require(sha256(read_file(H/name,65536)).hexdigest()==digest,'parent source differs: '+name)
        require(sha256(read_file(TOOL/'native/fx3_boot_reader.c',65536)).hexdigest()==B.SOURCE_SHA,'formal support source changed')
    check();out=PrivateDirectory(destination)
    try:
        argv=['/usr/bin/xcrun','clang','-target','aarch64-linux-gnu','-std=c11','-O2','-fPIC','-fvisibility=hidden','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-Wall','-Wextra','-Werror','-c',str(H/'prepare.c'),'-o',str(out.path/'module.o')]
        result=subprocess.run(argv,text=True,capture_output=True,umask=0o077);require(result.returncode==0,'parent compile failed: '+result.stderr[:2000])
        raw,report=link(read_file(out.path/'module.o',L.MAX_OBJECT));check();patched=bytearray(raw)
        require(patched[CONFIG_AT:CONFIG_AT+256]==bytes(256) and patched[NORM_AT:NORM_AT+32]==bytes(32),'header profile overlaps existing bytes')
        patched[CONFIG_AT:CONFIG_AT+256]=fixture_config();patched[NORM_AT:NORM_AT+32]=sha256(normalized(bytes(patched))).digest();raw=bytes(patched);report.update(inspect(raw))
        report.update(role='own fixed synthetic RAM-plan preparation constructor',source_pins=SOURCE_PINS,build_argv=argv,
            header_injections=[dict(offset=CONFIG_AT,bytes=256),dict(offset=NORM_AT,bytes=32)],source_initializer_creates_RAM_plan=True,
            private_staging_and_no_replace_publication_implemented=True,actual_target_renameat2_or_tmpfs_verified=False,
            source_or_worker_execution_backend=False,actual_target_global_namespace_or_IPC_verified=False,
            persistent_restart_completion_reconstruction=False,exclusive_authority_or_full_loaded_image_attested=False)
        out.put('parent-module.so',raw);out.put('build.json',encode(report));return report
    finally:out.close()

if __name__=='__main__':
    import json,sys
    print(json.dumps(build(sys.argv[1]),sort_keys=True))
