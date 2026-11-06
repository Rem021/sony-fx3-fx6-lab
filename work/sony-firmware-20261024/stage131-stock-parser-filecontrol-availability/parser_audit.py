#!/usr/bin/env python3
"""Original Parse lookup on shipped pFunc tables; no callback, new or I/O executes."""
from pathlib import Path
import argparse,datetime,hashlib,io,json,struct,sys,traceback
from elftools.elf.elffile import ELFFile
import capstone,unicorn
from unicorn import arm64_const as ar
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage130-backup-read-path-side-effects'));import read_path_audit as previous
CORE=BASE/'stage2/extraction/files/nflasha15/lib/libsencore.so'
CORE_SHA='a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410'
S=0x11000000;SP=0x10020000;PACKET=S+0x100;GOT=0x6aec0;GLOBAL=0x6bfa0
def reg(s):return getattr(ar,'UC_ARM64_REG_'+s.upper())
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
class Image:
    def __init__(self):
        raw=CORE.read_bytes();assert sha(raw)==CORE_SHA;self.elf=ELFFile(io.BytesIO(raw))
        self.segs=[s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD'];self.sy=self.elf.get_section_by_name('.dynsym')
        self.symbols={s.name:s for s in self.sy.iter_symbols() if s.name};self.md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM)
        self.rels={r['r_offset']:r for r in self.elf.get_section_by_name('.rela.dyn').iter_relocations()};self.tables=[];self.links=[]
        rr=self.rels[GOT];sy=self.sy.get_symbol(rr['r_info_sym'])
        assert rr['r_info_type']==1025 and sy.name=='pFunc' and sy['st_value']==GLOBAL and rr['r_addend']==0
        self.links.append({'offset':GOT,'type':'R_AARCH64_GLOB_DAT','symbol':'pFunc','target':GLOBAL})
        for name in ('pFunc_level_A','pFunc_level_B','pFunc_level_C'):
            s=self.symbols[name];a=s['st_value'];n=s['st_size'];assert n%16==0;rows=[]
            for i in range(n//16):
                at=a+16*i;raw=self.read(at,16);key=struct.unpack_from('<H',raw)[0];rel=self.rels.get(at+8)
                if rel:
                    fun=self.sy.get_symbol(rel['r_info_sym']);assert rel['r_info_type']==257 and fun['st_shndx']!='SHN_UNDEF'
                    target=fun['st_value']+rel['r_addend'];self.links.append({'offset':at+8,'type':'R_AARCH64_ABS64','symbol':fun.name,'target':target})
                    row={'row':hex(at),'pFunc':key,'callback':fun.name,'target':hex(target)}
                else:
                    assert key==0 and struct.unpack_from('<Q',raw,8)[0]==0 and i+1==n//16
                    row={'row':hex(at),'pFunc':0,'callback':None,'target':'0x0'}
                rows.append(row)
            assert all(x['pFunc'] not in (0xff01,0xff03) for x in rows)
            self.tables.append({'name':name,'VA':a,'size':n,'raw_bytes':self.read(a,n).hex(),'rows':rows})
        assert len(self.links)==11
    def read(self,a,n):
        s=next(s for s in self.segs if s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz'])
        return s.data()[a-s['p_vaddr']:a-s['p_vaddr']+n]
    def listing(self,a,z):return {'range':[hex(a),hex(z)],'sha256':sha(self.read(a,z-a)),
        'instructions':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in self.md.disasm(self.read(a,z-a),a)]}
class Guest:
    def __init__(self,image):
        self.image=image;self.u=unicorn.Uc(unicorn.UC_ARCH_ARM64,unicorn.UC_MODE_ARM);pages={}
        for s in image.segs:
            flags=(unicorn.UC_PROT_READ if s['p_flags']&4 else 0)|(unicorn.UC_PROT_WRITE if s['p_flags']&2 else 0)|(unicorn.UC_PROT_EXEC if s['p_flags']&1 else 0)
            assert not flags&unicorn.UC_PROT_WRITE or not flags&unicorn.UC_PROT_EXEC
            for a in range(s['p_vaddr']&~4095,(s['p_vaddr']+s['p_memsz']+4095)&~4095,4096):pages[a]=flags
        for a,f in sorted(pages.items()):self.u.mem_map(a,4096,f)
        for s in image.segs:self.u.mem_write(s['p_vaddr'],s.data())
        for link in image.links:self.u.mem_write(link['offset'],struct.pack('<Q',link['target']))
        self.u.mem_map(S,0x10000);self.u.mem_map(0x10000000,0x20000)
        self.u.mem_write(S,bytes([0xa5])*0x10000);self.u.mem_write(0x10000000,bytes([0xc3])*0x20000)
        self.hooks=[self.u.hook_add(unicorn.UC_HOOK_CODE,self.code),self.u.hook_add(unicorn.UC_HOOK_MEM_WRITE,self.write)]
        self.reason=None;self.pcs=[];self.stores=[]
    def code(self,u,pc,n,user):
        self.pcs.append(hex(pc))
        if pc==0xea28:self.reason='before_original_callback_BLR';u.emu_stop();return
        if pc==0xa6b0:self.reason='before_original_fallback_allocation';u.emu_stop();return
        assert 0xe9f4<=pc<0xea48,hex(pc)
    def write(self,u,access,a,n,v,user):self.stores.append({'pc':hex(u.reg_read(reg('pc'))),'address':hex(a),'size':n})
    def trial(self,table,pfunc):
        ptr=table['VA'] if table else 0;self.u.mem_write(GLOBAL,struct.pack('<Q',ptr))
        pkt=bytearray(16);struct.pack_into('<IH',pkt,0,4,pfunc);self.u.mem_write(PACKET,bytes(pkt))
        before=[(s['p_vaddr'],bytes(self.u.mem_read(s['p_vaddr'],s['p_memsz']))) for s in self.image.segs]
        before.append((S,bytes(self.u.mem_read(S,0x10000))));stack=bytes(self.u.mem_read(0x10000000,0x20000))
        self.u.reg_write(reg('sp'),SP);self.u.reg_write(reg('x0'),PACKET)
        self.u.emu_start(0xe9f4,0,count=200,timeout=1000000);assert self.reason
        assert self.u.reg_read(reg('sp'))==SP-0x20
        assert all(SP-0x20<=int(w['address'],16) and int(w['address'],16)+w['size']<=SP for w in self.stores)
        assert bytes(self.u.mem_read(0x10000000,0x20000-0x20))==stack[:-0x20]
        assert all(bytes(self.u.mem_read(a,len(b)))==b for a,b in before)
        matched=next((r for r in table['rows'] if r['pFunc']==pfunc and r['callback']),None) if table else None
        if matched:
            assert self.reason=='before_original_callback_BLR' and self.u.reg_read(reg('x2'))==int(matched['target'],16)
            assert self.u.reg_read(reg('x0'))==PACKET
        else:assert self.reason=='before_original_fallback_allocation' and self.u.reg_read(reg('x0'))==8
        return {'declared_table':table['name'] if table else None,'declared_pFunc':hex(pfunc),'matched_callback':matched,
            'reason':self.reason,'stop_pc':hex(self.u.reg_read(reg('pc'))),'pcs':self.pcs,'stores':self.stores,
            'images_scratch_and_stack_outside_32_bytes_unchanged':True,
            'packet_transport_auth_real_table_selection_callback_allocator_or_IO_executed':False}
    def close(self):
        for h in self.hooks:self.u.hook_del(h)
def run(out):
    previous.previous.shared_volume_check();assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes());image=Image()
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(Path(__file__).read_bytes()),
        'stock_tables':image.tables,'local_guest_links':image.links,'cases':[],
        'actual_Mac_cache_camera_Windows_or_host_services_executed':False,'goal_complete':False,'persistent_write_release':False}
    try:
        for table in image.tables:
            for pfunc in (0x40,0xff01,0xff03):
                m=Guest(image)
                try:j['cases'].append(m.trial(table,pfunc))
                finally:m.close()
        m=Guest(image)
        try:j['cases'].append(m.trial(None,0x40))
        finally:m.close()
        assert len(j['cases'])==10
        # The absent-case fallback construction writes 0x80 at NoAction+0x10;
        # its DoExecute reads that byte into packet+0xb. These are static here.
        put(STAGE/'source-and-scope-audit.json',{'original_core_sha256':CORE_SHA,'stock_tables':image.tables,
            'local_guest_links':image.links,'full_dynamic_loader_relocation_or_body_load_address_proven':False,
            'listings':[image.listing(a,z) for a,z in ((0xe9f4,0xea84),(0xd4e8,0xd4f8),(0x1475c,0x1488c))],
            'pFunc_global_GOT':'0x6aec0','pFunc_variable':'0x6bfa0','three_shipped_tables_missing_ff01_and_ff03':True,
            'fallback_80_is_static_NoAction_field_not_observed_wire_response':True,
            'explicit_table_pointer_is_fixture_not_actual_authenticated_camera_level':True,
            'no_blanket_claim_about_patched_custom_tables_or_other_firmware_versions':True,
            'PMCA_fixed_source':'https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L916-L945',
            'PMCA_ff01_file_read_and_ff03_memory_dump_not_current_stock_table_routes':True})
        j['status']='PASS_STOCK_PFUNC_TABLES_EXCLUDE_FF01_FF03_WITH_ORIGINAL_PARSE_LOOKUP_NOT_DEVICE_PROTOCOL'
        put(out/'parser-results.json',j)
        print(json.dumps({'status':j['status'],'stock_tables':3,'native_lookup_cases':10,'callbacks_or_device_IO_executed':False}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc();put(out/'attempt-failure.json',j);raise
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);run(a.parse_args().out)
