#!/usr/bin/env python3
"""Pin DMM module/config, decode static config and run two original leaf functions.

Only two local ABS64 literals are relocated. No kernel module is loaded and no
kernel, OSAL, allocator, lock, file or device service executes.
"""
from pathlib import Path
import argparse,datetime,hashlib,io,json,struct,traceback
from elftools.elf.elffile import ELFFile
import capstone,unicorn
from unicorn import arm64_const as ar
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
import prepare_inputs as prep
MOD=STAGE/'inputs/dmm.ko';CFG=STAGE/'inputs/DmmCfg.bin'
MOD_SHA='1e28a4921b36cd8866330a6670d72627d347c556dbea8568cd5b3ab60853e65a'
CFG_SHA='820dc02b6a001636b93fff51d90baaced1ba75cf9bbaa90600dfc7fd7a705166'
TC=0x04000000;RO=0x05000000;BS=0x06000000
STACK=0x10000000;SP=STACK+0x20000;S=0x11000000;STOP=0x12000000
UNIT=S+0x2000;EXT=S+0x3000;DEST=S+0x5000;COUNT=S+0x6000
def sha(b):return hashlib.sha256(b).hexdigest()
def reg(n):return getattr(ar,'UC_ARM64_REG_'+n.upper())
def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')

def decode_cfg(raw):
    offset=0
    def take(n):
        nonlocal offset
        if not 0<=n<=len(raw)-offset:raise ValueError('truncated_config_at_'+hex(offset))
        a=offset;offset+=n;return a,raw[a:offset]
    groups={}
    for phase,limit in (('roots',2),('rules',1024)):
        out=[]
        for _ in range(limit+1):
            a,h=take(0x50);kind,selector=struct.unpack_from('<II',h,8)
            if kind==0xffffffff:break
            rows=[]
            for _ in range(0xc01):
                at,r=take(0x14);vals=list(struct.unpack('<5I',r))
                if vals[2]==0xffffffff:break
                rows.append({'offset':hex(at),'words':vals})
            else:raise ValueError('row_terminator_missing')
            out.append({'header_offset':hex(a),'header_bytes':h.hex(),'type':kind,'selector':selector,'rows':rows})
        else:raise ValueError('group_terminator_missing')
        groups[phase]=out
    units=[]
    for _ in range(0x401):
        a,h=take(8);kind,attr=struct.unpack('<II',h)
        if kind==0xffffffff:break
        refs=[]
        for _ in range(0xc01):
            at,b=take(4);v=struct.unpack('<I',b)[0]
            if v==0xffffffff:break
            refs.append(v)
        else:raise ValueError('unit_list_terminator_missing')
        units.append({'header_offset':hex(a),'unit_type':kind,'attribute_word':attr,'extent_types':refs})
    else:raise ValueError('unit_table_terminator_missing')
    at,version=take(44)
    if offset!=len(raw):raise ValueError('unexpected_trailing_bytes')
    if len({u['unit_type'] for u in units})!=len(units):raise ValueError('duplicate_unit_type')
    return {'roots':groups['roots'],'rules':groups['rules'],'units':units,'version_offset':hex(at),
        'version_ascii':version.decode('ascii'),'total_consumed_bytes':offset,
        'layout_inferred_from_pinned_native_init_not_full_native_parser_execution':True}

class Image:
    def __init__(self):
        self.raw=MOD.read_bytes();assert sha(self.raw)==MOD_SHA
        self.elf=ELFFile(io.BytesIO(self.raw));assert self.elf['e_type']=='ET_REL' and self.elf['e_machine']=='EM_AARCH64'
        self.sy=self.elf.get_section_by_name('.symtab');self.md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM)
        self.text=bytearray(self.elf.get_section_by_name('.text').data());self.original_text=bytes(self.text)
        self.rodata=self.elf.get_section_by_name('.rodata').data();self.bss_size=self.elf.get_section_by_name('.bss')['sh_size']
        self.local_links=[]
        rels=list(self.elf.get_section_by_name('.rela.text').iter_relocations())
        self.relocs={r['r_offset']:r for r in rels}
        for at in (0x5ee8,0x9350):
            r=self.relocs[at];s=self.sy.get_symbol(r['r_info_sym']);sec=self.elf.get_section(s['st_shndx']).name
            assert r['r_info_type']==257 and sec in ('.rodata','.bss')
            target={'.rodata':RO,'.bss':BS}[sec]+s['st_value']+r['r_addend']
            old=bytes(self.text[at:at+8]);struct.pack_into('<Q',self.text,at,target)
            assert target<1<<64
            self.local_links.append({'text_offset':hex(at),'type':'R_AARCH64_ABS64','section':sec,
                'symbol_value':s['st_value'],'addend':r['r_addend'],'guest_target':hex(target),'original_bytes':old.hex()})
        changed={i for i,(a,b) in enumerate(zip(self.original_text,self.text)) if a!=b}
        assert changed<={i for at in (0x5ee8,0x9350) for i in range(at,at+8)}
        self.controller_global=struct.unpack_from('<Q',self.text,0x9350)[0]
    def listing(self,a,z):
        out=[]
        for i in self.md.disasm(self.original_text[a:z],a):
            rr=self.relocs.get(i.address);ref=None
            if rr:
                s=self.sy.get_symbol(rr['r_info_sym']);ref={'symbol':s.name,'type':rr['r_info_type'],'addend':rr['r_addend'],
                    'section':self.elf.get_section(s['st_shndx']).name if isinstance(s['st_shndx'],int) else s['st_shndx']}
            out.append({'section_offset':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str,'relocation':ref})
        return {'range':[hex(a),hex(z)],'sha256':sha(self.original_text[a:z]),'instructions':out}

class Guest:
    def __init__(self,image,seed):
        self.image=image;self.u=unicorn.Uc(unicorn.UC_ARCH_ARM64,unicorn.UC_MODE_ARM);self.seed=seed
        for a,b,flags in ((TC,bytes(image.text),unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC),
                          (RO,image.rodata,unicorn.UC_PROT_READ),
                          (BS,bytes(image.bss_size),unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)):
            self.u.mem_map(a,(len(b)+4095)&~4095,flags);self.u.mem_write(a,b)
        self.u.mem_map(STACK,0x20000);self.u.mem_map(S,0x10000);self.u.mem_map(STOP,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC)
        self.u.mem_write(STACK,bytes([seed])*0x20000);self.u.mem_write(S,bytes([seed^0x3c])*0x10000)
        for i in range(19,30):self.u.reg_write(reg('x'+str(i)),0x38000000+seed*0x1000+i*0x10)
        for i in range(8,16):self.u.reg_write(reg('d'+str(i)),0x1234567800000000+seed*256+i)
        self.hooks=[self.u.hook_add(unicorn.UC_HOOK_CODE,self.code),self.u.hook_add(unicorn.UC_HOOK_MEM_WRITE,self.write)]
        self.allowed=[];self.reason=None;self.pcs=[];self.stores=[]
    def code(self,u,pc,n,user):
        self.pcs.append(hex(pc))
        if pc==STOP:self.reason='returned';u.emu_stop();return
        assert any(a<=pc<z for a,z in self.allowed),hex(pc)
        ins=list(self.image.md.disasm(bytes(u.mem_read(pc,n)),pc));assert len(ins)==1
        assert ins[0].mnemonic not in ('mrs','msr','svc','hvc','smc','brk','blr','bl'),ins[0].mnemonic
    def write(self,u,access,a,n,v,user):
        self.stores.append({'pc':hex(u.reg_read(reg('pc'))),'address':hex(a),'size':n,'value':v&((1<<(n*8))-1)})
    def run(self,label,offset,outputs,**regs):
        self.allowed=[(TC+0x5e90,TC+0x5ee8),(TC+0x91e8,TC+0x9350)]
        before={a:bytes(self.u.mem_read(a,n)) for a,n in ((STACK,0x20000),(S,0x10000),(TC,len(self.image.text)),(RO,len(self.image.rodata)),(BS,self.image.bss_size))}
        for n,v in dict(sp=SP,x30=STOP,**regs).items():self.u.reg_write(reg(n),v)
        saved={n:self.u.reg_read(reg(n)) for n in ['x'+str(i) for i in range(19,30)]+['d'+str(i) for i in range(8,16)]}
        self.reason=None;self.pcs=[];self.stores=[];self.u.emu_start(TC+offset,0,count=1000,timeout=1000000)
        assert self.reason=='returned' and self.u.reg_read(reg('sp'))==SP
        assert all(self.u.reg_read(reg(n))==v for n,v in saved.items())
        allowed=[(SP-0x100,SP)]+outputs
        for w in self.stores:
            a,n=int(w['address'],16),w['size'];assert any(x<=a and a+n<=z for x,z in allowed),w
        for a,b in before.items():
            actual=bytes(self.u.mem_read(a,len(b)));changes=[a+i for i,(x,y) in enumerate(zip(b,actual)) if x!=y]
            assert all(any(x<=k<z for x,z in allowed) for k in changes),(hex(a),changes[:4])
        return {'label':label,'entry':hex(TC+offset),'return_u32':self.u.reg_read(reg('w0')),'pcs':self.pcs,'stores':self.stores,
            'SP_saved_registers_and_memory_outside_outputs_preserved':True,'kernel_OSAL_locks_allocator_or_device_executed':False}
    def close(self):
        for h in self.hooks:self.u.hook_del(h)

def length_case(image,kind,n):
    m=Guest(image,0xa5)
    try:
        m.u.mem_write(COUNT,struct.pack('<H',n));ev=m.run('original DMM reply length selector',0x5e90,[],x0=kind,x1=COUNT)
        variable_types=(0x8020,0x8021,0x8022,0x8024,0x8026,0x802a)
        expected=0x18+n*16 if kind in variable_types and 1<=n<=12 else 0x28
        assert ev['return_u32']==expected,(hex(kind),n,ev['return_u32'],expected)
        return {'reply_type':kind,'declared_count':n,'native_bytes':ev['return_u32'],'events':[ev],
            'fallback_length_not_count_rejection_or_buffer_validity_proof':True}
    finally:m.close()

def open_case(image,label,n=1,flags=1,state=1,opens=0,aux=0,generation=7,handle_generation=7,index=2,expected=0):
    assert 0<=n<=12
    m=Guest(image,0xc3)
    try:
        arr=bytearray(4*0x70);at=2*0x70;struct.pack_into('<II',arr,at,974,0x1234)
        arr[at+9]=opens;arr[at+0xa]=aux;arr[at+0xb]=generation;struct.pack_into('<HH',arr,at+0xc,state,n)
        expected_desc=bytearray()
        for i in range(n):
            ptr=EXT+i*0x80;struct.pack_into('<Q',arr,at+0x10+i*8,ptr)
            b=bytearray(0x50);base=0x70000000+i*0x01000000;off=i*0x1000;size=0x200000+i*0x1000
            struct.pack_into('<QII',b,8,base,off,size);m.u.mem_write(ptr,bytes(b))
            expected_desc+=struct.pack('<QI4x',base+off,size)
        m.u.mem_write(UNIT,bytes(arr));m.u.mem_write(image.controller_global+0x20,struct.pack('<Q',UNIT))
        before_unit=bytes(arr);before_dest=bytes(m.u.mem_read(DEST,0x100));before_count=bytes(m.u.mem_read(COUNT,2))
        handle=(handle_generation<<10)|index
        ev=m.run('original unit Open '+label,0x91e8,[(UNIT+at+9,UNIT+at+10),(UNIT+at+0xc,UNIT+at+0xe),(DEST,DEST+0x100),(COUNT,COUNT+2)],
            x0=handle,x1=flags,x2=DEST,x3=COUNT)
        assert ev['return_u32']==expected&0xffffffff
        after=bytes(m.u.mem_read(UNIT,len(arr)));dest=bytes(m.u.mem_read(DEST,0x100));count=struct.unpack('<H',bytes(m.u.mem_read(COUNT,2)))[0]
        wanted=bytearray(arr)
        if expected==0:
            assert count==n
            # The original writes address/size only; four padding bytes per row
            # retain their input. Compare only the native semantic fields.
            wanted_dest=bytearray(before_dest)
            for i in range(n):wanted_dest[i*16:i*16+12]=expected_desc[i*16:i*16+12]
            assert dest==bytes(wanted_dest)
            if flags in (0,1):wanted[at+9]=opens+1;struct.pack_into('<H',wanted,at+0xc,2)
            elif flags==4:wanted[at+9]=1;struct.pack_into('<H',wanted,at+0xc,3)
        else:
            assert dest==before_dest
            if expected not in (-0x205,-0x105):assert count==0
            else:assert bytes(m.u.mem_read(COUNT,2))==before_count
        assert after==bytes(wanted)
        return {'label':label,'n':n,'flags':flags,'state':state,'opens':opens,'aux':aux,'generation':generation,
            'handle_generation':handle_generation,'index':index,'expected_status':expected,
            'native_status_u32':ev['return_u32'],'native_count_storage_u16':count,
            'before_unit':before_unit.hex(),'after_unit':after.hex(),'native_descriptor_storage':dest.hex(),'events':[ev],
            'runtime_unit_extent_and_generation_inputs_are_declared':True,'real_allocation_mapping_owner_or_read_only_protocol_proven':False}
    finally:m.close()

def main(out):
    prep.volume();assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    assert sha(CFG.read_bytes())==CFG_SHA;image=Image();out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(Path(__file__).read_bytes()),
        'length_cases':[],'open_cases':[],'camera_Windows_host_services_or_module_loading':False,'goal_complete':False,'persistent_write_release':False}
    try:
        cfg=decode_cfg(CFG.read_bytes());decoded=STAGE/'DmmCfg-decoded.json'
        if decoded.exists():assert json.loads(decoded.read_text())==cfg
        else:put(decoded,cfg)
        assert len(cfg['roots'])==1 and len(cfg['rules'])==164 and len(cfg['units'])==348
        assert cfg['total_consumed_bytes']==43320 and max(len(u['extent_types']) for u in cfg['units'])==1
        failures=[]
        for cut in (0,79,0x18f,0x9343,len(CFG.read_bytes())-1):
            try:decode_cfg(CFG.read_bytes()[:cut])
            except ValueError as ex:failures.append({'cut_bytes':cut,'rejection':str(ex)})
            else:raise AssertionError('truncated config accepted')
        old=BASE/'stage126-native-DMM-buffer-to-Open/run-native-buffer-Open-20261027/buffer-Open-results.json'
        old_manifest=json.loads((old.parents[1]/'final-receipt.json').read_text())
        old_row=next(f for f in old_manifest['files'] if f['path']==str(old.relative_to(ROOT)))
        assert sha(old.read_bytes())==old_row['sha256']
        wanted=sorted({r['unit_type'] for c in json.loads(old.read_text())['cases'] for r in c['original_unit_rows']})
        actual={u['unit_type'] for u in cfg['units']};matches=sorted(actual.intersection(wanted))
        assert len(wanted)==20 and not matches
        j['config_binding']={'source_result':str(old.relative_to(ROOT)),'source_result_sha256':sha(old.read_bytes()),
            'version':cfg['version_ascii'],'unit_count':len(actual),'max_declared_extent_list':1,
            'target_MPR_unit_types':wanted,'matching_target_units':matches,'truncated_inputs_rejected':failures,
            'AP_runtime_or_MPR_config_binding_proven':False}
        for kind in (0x8020,0x8028,0x802a):
            for n in (0,1,8,9,10,12,13):j['length_cases'].append(length_case(image,kind,n))
        params=[('ordinary_1',{}),('ordinary_8',{'n':8}),('ordinary_12',{'n':12,'state':2,'opens':2}),
            ('inspect_9',{'n':9,'flags':0x1001,'state':2,'opens':2}),
            ('stale_generation',{'handle_generation':6,'expected':-0x205}),
            ('invalid_index',{'index':0x3ff,'expected':-0x105}),
            ('saturated_open',{'opens':255,'expected':-1}),
            ('exclusive_busy',{'flags':4,'opens':1,'expected':-0x3301}),
            ('exclusive_aux',{'flags':4,'aux':1,'expected':-1}),
            ('inspect_state3',{'flags':0x1001,'state':3,'opens':1}),
            ('ordinary_state3',{'state':3,'opens':1,'expected':-0x3301}),
            ('closed_state',{'state':0,'expected':-1}),('zero_extent',{'n':0}),
            ('bad_flags',{'flags':2,'expected':-4}),('exclusive_open',{'flags':4})]
        for label,kw in params:j['open_cases'].append(open_case(image,label,**kw))
        ro_rels=list(image.elf.get_section_by_name('.rela.rodata').iter_relocations())
        table=[]
        for name,base in (('msg_hdlr',0x110),('sync_msg_hdlr',0x280)):
            rr=next(r for r in ro_rels if r['r_offset']==base+0x20*8);sy=image.sy.get_symbol(rr['r_info_sym'])
            assert rr['r_info_type']==257 and image.elf.get_section(sy['st_shndx']).name=='.text' and sy['st_value']+rr['r_addend']==0x5488
            table.append({'table':name,'command':0x20,'relocation_offset':hex(rr['r_offset']),'type':'R_AARCH64_ABS64','target_section_offset':'0x5488'})
        listings=[image.listing(a,z) for a,z in ((0x4e40,0x4eb8),(0x5280,0x52d8),(0x5488,0x56e8),(0x5e90,0x5ee8),
            (0x71dc,0x71ec),(0x8200,0x8290),(0x8420,0x8440),(0x91e8,0x9350),(0x8b88,0x8df0),
            (0xa158,0xa250),(0xbce8,0xc0a0),(0x80,0x190))]
        put(STAGE/'source-and-scope-audit.json',{'created_utc':j['created_utc'],'module_sha256':MOD_SHA,'config_sha256':CFG_SHA,
            'local_leaf_literal_links_only':image.local_links,'full_module_relocation_or_kernel_initialization_proven':False,
            'reply_length_native_jump_table':[
                {'reply_type':hex(0x8020+k),'entry_byte':v,
                 'target_text_offset':hex(0x5eb4+struct.unpack('b',bytes([v]))[0]*4)}
                for k,v in enumerate(image.rodata[0xe0:0xeb])],
            'module_command20_tables':table,'native_listings':listings,
            'module_static_queue_ID':'0x61003c','queue_receive_call_relocation':{'offset':'0x8234','symbol':'osal_rcv_msg_tmo'},
            'queue_sync_registration_call_relocation':{'offset':'0x843c','symbol':'osal_reg_sync_msg_queue_cb'},
            'queue_registration_receive_dispatch_and_allocation_not_executed':True,
            'reply_length_1_to_12_computation_is_not_an_8_chunk_guard_or_rejection_function':True,
            'unit_Open_flags1_writes_open_count_and_state_not_read_only_query':True,
            'config_file_20_target_units_absent_and_runtime_binding_unproven':True,
            'source_context_and_inputs_are_fixed_official_package_not_device_capture':True})
        j['native_phases']=sum(len(c['events']) for k in ('length_cases','open_cases') for c in j[k])
        j['status']='PASS_DMM_STATIC_ROUTE_CONFIG_MISMATCH_AND_NATIVE_LEAF_SCOPE_NOT_RUNTIME_ALLOCATION'
        put(out/'provider-results.json',j)
        print(json.dumps({'status':j['status'],'native_phases':j['native_phases'],'config_units':len(actual),'target_matches':len(matches)}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc();put(out/'attempt-failure.json',j);raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
