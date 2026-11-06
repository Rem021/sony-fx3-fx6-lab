#!/usr/bin/env python3
"""Guest-only original request -> compiled publication -> original channel path.

Real kernel services remain boundaries. No kernel task, allocator, USB response,
Sony hook deployment, consumer completion or hardware result is synthesized.
"""
from pathlib import Path
import argparse
import datetime
import io
import json
import struct
import subprocess
import sys
import time
import traceback
from elftools.elf.elffile import ELFFile

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage64-osal-offline-link'))
import native_osal as d
r,im,V,n,f=d.r,d.im,d.V,d.n,d.f
BASE,ROOT=d.BASE,d.ROOT
old=f.f61.old
COMMON=f.last.COMMON
COPY=COMMON+0xe010
SITE=V+0x21eeb4
BRIDGE=V+0x1100000
CONST=BRIDGE+0x10000
SONY={'sony_rate':V+0x225b7c,'sony_channel':V+0x21dd54}


def object_image(raw):
    e=ELFFile(io.BytesIO(raw));assert e['e_machine']=='EM_AARCH64' and e['e_type']=='ET_REL'
    assert e.elfclass==64 and e.little_endian and e.num_segments()==0
    text=e.get_section_by_name('.text');ro=e.get_section_by_name('.rodata');sy=e.get_section_by_name('.symtab')
    assert text['sh_flags']==6 and ro['sh_flags']==2 and len(ro.data())==136
    assert not any(s['sh_flags']&3==3 for s in e.iter_sections())
    bases={i:(BRIDGE if s.name=='.text' else BRIDGE+4096 if s.name=='.text.unlikely.' else CONST)
           for i,s in enumerate(e.iter_sections()) if s.name in ('.text','.text.unlikely.','.rodata')}
    functions={s.name:bases[s['st_shndx']]+s['st_value'] for s in sy.iter_symbols()
               if s['st_info']['type']=='STT_FUNC' and isinstance(s['st_shndx'],int)}
    assert set(functions)=={'fx3_channel_adapter','fx3_reject_boundary','fx3_channel_adapter.cold.1','fx3_channel_adapter.cold.2'}
    assert {s.name for s in sy.iter_symbols() if s.name and s['st_shndx']=='SHN_UNDEF'}==set(SONY)
    executable=[(i,s) for i,s in enumerate(e.iter_sections()) if s['sh_flags']&4]
    assert {s.name for i,s in executable}=={'.text','.text.unlikely.'}
    assert all(s['sh_flags']==6 and s['sh_size']<=4096 for i,s in executable)
    code=bytearray(max(bases[i]-BRIDGE+s['sh_size'] for i,s in executable));ranges=[]
    for i,s in executable:
        off=bases[i]-BRIDGE;code[off:off+s['sh_size']]=s.data();ranges.append((bases[i],bases[i]+s['sh_size']))
    pristine=bytes(code);changes=[];rate_returns=[]
    for sec in e.iter_sections():
        if sec['sh_type']!='SHT_RELA':continue
        assert sec['sh_info'] in {i for i,s in executable}
        symbols=e.get_section(sec['sh_link'])
        for rel in sec.iter_relocations():
            off,kind=rel['r_offset'],rel['r_info_type'];symbol=symbols.get_symbol(rel['r_info_sym'])
            guest_off=bases[sec['sh_info']]-BRIDGE+off
            at=BRIDGE+guest_off;target=SONY[symbol.name] if symbol['st_shndx']=='SHN_UNDEF' else bases[symbol['st_shndx']]+symbol['st_value']
            target+=rel['r_addend'];word=struct.unpack_from('<I',code,guest_off)[0]
            if kind in (282,283):
                assert word&0xfc000000==(0x94000000 if kind==283 else 0x14000000)
                new=int.from_bytes(f.f58.branch(at,target,kind==283),'little')
                displacement=new&0x3ffffff
                if displacement&(1<<25):displacement-=1<<26
                assert at+displacement*4==target
                if symbol.name=='sony_rate':assert kind==283;rate_returns.append(at+4)
            elif kind==275:
                assert word&0x9f000000==0x90000000
                delta=((target&-4096)-(at&-4096))>>12;assert -(1<<20)<=delta<(1<<20)
                bits=delta&0x1fffff;new=(word&~((3<<29)|(0x7ffff<<5)))|((bits&3)<<29)|((bits>>2)<<5)
            elif kind==277:
                assert word&0xffc00000==0x91000000
                new=(word&~(4095<<10))|((target&4095)<<10)
            else:raise AssertionError(('unsupported relocation',kind))
            struct.pack_into('<I',code,guest_off,new)
            changes.append({'section':e.get_section(sec['sh_info']).name,'offset':hex(off),'guest_offset':hex(guest_off),
                            'type':kind,'symbol':symbol.name,'target':hex(target),'original':hex(word),'relocated':hex(new)})
    assert len(rate_returns)==1
    touched={i for row in changes for i in range(int(row['guest_offset'],16),int(row['guest_offset'],16)+4)}
    assert all(a==b or i in touched for i,(a,b) in enumerate(zip(pristine,code)))
    return bytes(code),ro.data(),functions,changes,rate_returns,ranges


class Guest(d.Guest):
    def __init__(self,assets,modules,providers,adapter):
        super().__init__(assets,modules,providers)
        self.adapter_code,self.adapter_ro,self.adapter_functions,self.adapter_relocations,self.rate_return_pcs,self.adapter_ranges=adapter
        self.uc.mem_map(BRIDGE,0x10000,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
        self.uc.mem_map(CONST,4096,r.unicorn.UC_PROT_READ)
        self.uc.mem_write(BRIDGE,self.adapter_code);self.uc.mem_write(CONST,self.adapter_ro)
        self.ranges.extend(self.adapter_ranges)
        self.adapter_patch=f.f58.branch(SITE,self.adapter_functions['fx3_channel_adapter'],True)
        assert self.read(SITE,4)==f.f58.branch(SITE,SONY['sony_channel'],True)
        self.boundaries[self.adapter_functions['fx3_reject_boundary']]='before_OUR_unexecuted_rejection_body'
        self.prototype_limits=[(old.CONTROL,296),(COPY,256),(COMMON+0xe000,8),(r.STACK,r.STACK_SIZE)]
        self.adapter_entries=[];self.writer_entries=[];self.rate_entries=[];self.rate_returns=[]
        self.admitted_channel_entries=[];self.rejection_entries=[];self.adapter_stores=[]
        self.observed_pc=0
        self.watched_pcs={self.adapter_functions['fx3_channel_adapter'],self.functions['fx3_candidate'],
                          SONY['sony_rate'],SONY['sony_channel'],self.adapter_functions['fx3_reject_boundary'],*self.rate_return_pcs}

    def code(self,u,pc,size,user):
        self.observed_pc=pc
        if pc not in self.watched_pcs:return super().code(u,pc,size,user)
        rr=lambda i:u.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))
        sp=u.reg_read(r.reg.UC_ARM64_REG_SP)
        if pc==self.adapter_functions['fx3_channel_adapter']:
            self.adapter_entries.append({'pc':hex(pc),'SP':hex(sp),'LR':hex(rr(30)),
                'x0_x3':[hex(rr(i)) for i in range(4)],'selected_before':hex(struct.unpack('<Q',self.read(COMMON+0xe000,8))[0])})
        if pc==self.functions['fx3_candidate']:
            self.writer_entries.append({'pc':hex(pc),'SP':hex(sp),'LR':hex(rr(30)),
                                        'x0_x5':[hex(rr(i)) for i in range(6)]})
        if pc==SONY['sony_rate']:
            dest=rr(8)
            self.rate_entries.append({'pc':hex(pc),'SP':hex(sp),'LR':hex(rr(30)),
                                      'owner':hex(rr(0)),'result_pointer':hex(dest)})
            assert self.adapter_entries and sp<=dest and dest+24<=int(self.adapter_entries[-1]['SP'],16)
        if pc in self.rate_return_pcs:
            dest=int(self.rate_entries[-1]['result_pointer'],16)
            self.rate_returns.append({'pc':hex(pc),'SP':hex(sp),'result_pointer':hex(dest),
                                      'trace_target_cpb':list(struct.unpack('<3Q',self.read(dest,24)))})
        if pc==SONY['sony_channel']:
            self.admitted_channel_entries.append({'pc':hex(pc),'SP':hex(sp),'LR':hex(rr(30)),
                'x0_x3':[hex(rr(i)) for i in range(4)],
                'selected':hex(struct.unpack('<Q',self.read(COMMON+0xe000,8))[0]),
                'control':old.control(self)})
        if pc==self.adapter_functions['fx3_reject_boundary']:
            self.rejection_entries.append({'pc':hex(pc),'SP':hex(sp),'LR':hex(rr(30)),'reason':rr(0),
                                            'body_executed':False,'Sony_error_handling_executed':False})
        return super().code(u,pc,size,user)

    def store(self,u,access,a,size,value,user):
        pc=self.observed_pc
        if BRIDGE<=pc<BRIDGE+len(self.adapter_code):
            assert r.STACK<=a and a+size<=r.STACK+r.STACK_SIZE
            self.adapter_stores.append({'pc':hex(pc),'address':hex(a),'bytes':size})
        return super().store(u,access,a,size,value,user)


def phase(m,label,start,**regs):
    global LAST_PHASE
    independent=regs.pop('independent',True)
    m.reason=None;m.pcs=[];m.writes=[];m.cpu_events=[]
    m.clear_calls=[];m.constructor_calls=[];m.pool_calls=[]
    if independent:m.regs(sp=r.SP,x30=r.STOP)
    m.regs(**regs);before_sp=m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    chunks=[];pc=start;began=time.monotonic()
    while m.reason is None:
        before_count=len(m.pcs);assert before_count<2000000 and time.monotonic()-began<120
        # An observation time slice is not a successful stop. Resume this same
        # Unicorn instance at its actual PC without changing registers/RAM.
        m.uc.emu_start(pc,0,count=2000000-before_count,timeout=3000000)
        end=m.uc.reg_read(r.reg.UC_ARM64_REG_PC)
        chunks.append({'start_pc':hex(pc),'end_pc':hex(end),'executed':len(m.pcs)-before_count,'reason':m.reason})
        if m.reason is None:assert len(m.pcs)>before_count
        pc=end
    result={'label':label,'start_pc':hex(start),'reason':m.reason,'stop_pc':hex(pc),
            'SP_before':hex(before_sp),'SP_after':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_SP)),
            'x0_after':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_X0)),
            'pcs':[hex(p) for p in m.pcs],'writes':list(m.writes),'native_clear_calls':list(m.clear_calls),
            'common_constructor_calls':list(m.constructor_calls),'pool_constructor_calls':list(m.pool_calls),
            'CPU_events':list(m.cpu_events),'independent_entry_fixture':independent,
            'native_output_or_PC_return_adapter':False,'same_instance_observation_slices':chunks,
            'instruction_limit':2000000,'wall_limit_seconds':120}
    LAST_PHASE=result;return result


def linked(assets,modules,providers,adapter):
    m=Guest(assets,modules,providers,adapter)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    events=[n.link(m)]
    for binding in m.import_bindings:
        assert m.read(int(binding['actual_avcam_slot'],16),8)==r.p64(int(binding['original_module_target'],16))
    assert sum(int.from_bytes(m.read(V+0x1ec+i*8,8),'little')!=0 for i in range(211))==5
    m.uc.mem_write(f.f58.SITE,m.patch);m.uc.mem_write(SITE,m.adapter_patch)
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    m.expected_data={f.f59.GUARD:1,f.f59.MUTE:0,f.f59.CAT1:1,f.f59.CAT2:1}
    for a,value in m.expected_data.items():assert m.blob[a-V]==0;m.uc.mem_write(a,bytes([value]))
    m.uc.mem_protect(f.f59.MUTE&-4096,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    e=phase(m,'original mute setter on declared initialized logger',V+0x27d898,x0=f.f59.LOG,x1=1)
    assert e['reason']=='returned';events.append(e);m.expected_data[f.f59.MUTE]=1
    lo=f.G&-4096;hi=(f.G+f.GSIZE+4095)&-4096
    m.uc.mem_protect(lo,hi-lo,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    return m,events


def prepare(m,events,descriptor,seed,negative):
    q=f.last
    m.uc.mem_write(q.MANAGER,bytes([seed])*q.MANAGER_SIZE);m.uc.mem_write(q.CTX,bytes(0x390))
    m.uc.mem_write(q.FACTORY,bytes([seed])*q.FACTORY_SIZE)
    for label,start,at,size,args in (
        ('original manager constructor',0x22cc8c,q.MANAGER,q.MANAGER_SIZE,{'x0':q.MANAGER}),
        ('original factory construction and bindings',0x226d2c,q.FACTORY,q.FACTORY_SIZE,{'x0':q.FACTORY,'x1':q.MANAGER}),
        ('original factory free-queue reset',0x2270d4,q.FACTORY,q.FACTORY_SIZE,{'x0':q.FACTORY})):
        before=m.read(r.ARENA,r.ARENA_SIZE)
        e=phase(m,label,V+start,**args);assert e['reason']=='returned'
        assert e['SP_before']==e['SP_after']==hex(r.SP)
        after=m.read(r.ARENA,r.ARENA_SIZE);lo=at-r.ARENA;hi=lo+size
        assert before[:lo]==after[:lo] and before[hi:]==after[hi:]
        e['full_guest_arena_outside_constructed_object_unchanged']=True
        e['constructed_object_range']=[hex(at),hex(at+size)];events.append(e)
    assert not m.all_logs and len(m.manager_bindings)==8
    assert q.word(m,q.FACTORY+8)==8 and q.word(m,q.FACTORY+0x55ec8)==6
    m.uc.mem_write(q.CTX+0x108,struct.pack('<I',1));m.uc.mem_write(q.CTX+0x118,r.p64(q.MESSAGE))
    m.uc.mem_write(q.MESSAGE,bytes(0xc0));m.uc.mem_write(q.MESSAGE+8,r.p64(q.IDENTITY))
    m.uc.mem_write(q.IDENTITY,struct.pack('<I',d.p.UID));m.uc.mem_write(q.MESSAGE+0x20,descriptor)
    m.uc.mem_write(r.SP-0x2000,bytes([seed])*0x3000)
    values=[old.MAGIC,old.SESSION,old.EPOCH,old.EPOCH,COMMON,1,0,0,1,0,0,0,0]
    if negative=='closed':values[5]=0
    elif negative=='epoch':values[3]+=1
    elif negative=='owner':values[4]+=0xe518
    elif negative=='magic':values[0]^=1
    elif negative=='lock':values[11]=1
    else:assert negative is None
    m.uc.mem_write(old.CONTROL,struct.pack('<13Q',*values)+bytes(192))


def assert_images(m):
    raw=bytearray(m.read(V,len(m.blob)))
    assert raw[0x1ec:0x884]==m.read(n.MDATA,0x698);raw[0x1ec:0x884]=m.blob[0x1ec:0x884]
    for a,patch in ((f.f58.SITE,m.patch),(SITE,m.adapter_patch)):
        assert raw[a-V:a-V+4]==patch;raw[a-V:a-V+4]=m.blob[a-V:a-V+4]
    for a,value in m.expected_data.items():assert raw[a-V]==value;raw[a-V]=m.blob[a-V]
    flag=struct.unpack('<Q',raw[f.FLAG-V:f.FLAG-V+8])[0];assert flag in (0,1)
    if flag:raw[f.G-V:f.G-V+f.GSIZE]=m.blob[f.G-V:f.G-V+f.GSIZE]
    assert raw==m.blob
    for a,data in [(f.f58.BRIDGE,m.code_bytes),(f.f58.CONST,m.ro_bytes),(old.CODE,m.writer_code),
                   (old.RODATA,m.writer_ro),(BRIDGE,m.adapter_code),(CONST,m.adapter_ro)]:
        assert m.read(a,len(data))==data
    for module in m.modules.values():
        for section in module.sections.values():assert m.read(section['base'],section['size'])==bytes(section['data'])
    assert not m.module_writes


def one_case(assets,modules,providers,adapter,label,descriptor,seed,row,target=False,negative=None):
    m,events=linked(assets,modules,providers,adapter);prepare(m,events,descriptor,seed,negative)
    e=phase(m,'original queued request through guest-only channel call adapter '+label,V+0x22f34c,x0=f.last.CTX)
    events.append(e)
    assert m.real_returns[0]['W0']==row
    source=int(m.bridge_entries[0]['source'],16);original_source=m.read(source,152)
    assert original_source[:136]==descriptor and m.read(COMMON+0xe110,136)==descriptor
    assert len(m.adapter_entries)==1 and m.adapter_entries[0]['LR']==hex(SITE+4)
    args=m.adapter_entries[0]['x0_x3'];assert args[0]==hex(COMMON)
    control=old.control(m)
    if negative:
        expected={'closed':3,'epoch':4,'owner':0x1001,'magic':1,'lock':2}[negative]
        assert e['reason']=='boundary: before_OUR_unexecuted_rejection_body',e['reason']
        assert len(m.rejection_entries)==1 and m.rejection_entries[0]['reason']==expected
        assert not m.admitted_channel_entries and not m.rate_entries and not m.kernel_service_entries
        assert not m.message_entries and m.read(COMMON+0xe000,8)==r.p64(V+0x3c5798)
        assert control['live']==0 and control['phase']==0
        if negative=='lock':assert control['lock']==1
        assert not any(COPY<=int(w['address'],16)<COPY+256 for w in m.prototype_stores)
    else:
        assert e['reason']=='boundary: before_original_buffer_channel_preparation',e['reason']
        assert len(m.admitted_channel_entries)==1 and m.admitted_channel_entries[0]['x0_x3']==args
        if target:
            assert len(m.writer_entries)==len(m.rate_entries)==len(m.rate_returns)==1
            assert BRIDGE<=int(m.writer_entries[0]['LR'],16)<BRIDGE+len(m.adapter_code)
            assert m.writer_entries[0]['x0_x5']==[hex(old.CONTROL),'0x0','0x0','0x0',hex(old.EPOCH),hex(old.SESSION)]
            assert m.rate_returns[0]['trace_target_cpb']==[25999360,16000000,26000000]
            assert m.read(COMMON+0xe000,8)==r.p64(COPY)
            copy=m.read(COPY,256);original=m.blob[0x3c5798:0x3c5898]
            assert [i for i,(a,b) in enumerate(zip(original,copy)) if a!=b]==[0xb0,0xb1,0xb2]
            assert control['live']==control['phase']==1 and control['lock']==0
        else:
            assert not m.writer_entries and not m.rate_entries and not m.rate_returns
            assert control['live']==control['phase']==0 and not m.prototype_stores
        snapshot=m.read(old.CONTROL,296)
        m.boundaries.pop(SONY['sony_channel'])
        e2=phase(m,'same active original channel request to original OSAL/kernel boundary '+label,SONY['sony_channel'],independent=False)
        events.append(e2)
        assert e2['reason']=='boundary: before_original_unexecuted_kernel_service',e2['reason']
        assert len(m.kernel_service_entries)==1 and m.kernel_service_entries[0]['names']==['_raw_spin_lock_irqsave']
        assert len(m.module_alloc_entries)==len(m.message_entries)==1
        assert m.read(old.CONTROL,296)==snapshot
        assert m.read(source,152)==original_source and m.read(COMMON+0xe110,136)==descriptor
        if target:assert m.read(COMMON+0xe000,8)==r.p64(COPY)
    assert_images(m)
    return {'label':label,'target':target,'negative':negative,'seed':seed,'row':row,'source98_hex':original_source.hex(),
            'original_source_and_common_descriptor_preserved':True,'adapter_entry':m.adapter_entries,
            'actual_writer_calls_from_adapter':m.writer_entries,'actual_original_rate_calls':m.rate_entries,
            'actual_original_rate_returns':m.rate_returns,'actual_original_channel_entries':m.admitted_channel_entries,
            'our_unexecuted_rejection_entries':m.rejection_entries,'writer_native_stores':m.prototype_stores,
            'adapter_stack_stores':m.adapter_stores,'control_at_stop':old.control(m),
            'resource_messages':m.message_entries,'kernel_service_boundary':m.kernel_service_entries,'events':events,
            'actual_camera_hook_Linux_services_HAL_or_recording':False,'completion_or_rollback_notifications_synthesized':False}


def run(out):
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    cmd=['/usr/bin/clang',*old.old.FLAGS,'-c',str(STAGE/'channel_adapter.c'),'-o',str(out/'channel_adapter.a64.o')]
    built=subprocess.run(cmd,capture_output=True,text=True)
    im.write_json(out/'compile-receipt.json',{'command':cmd,'returncode':built.returncode,'stdout':built.stdout,'stderr':built.stderr})
    assert built.returncode==0,built.stderr
    adapter=object_image((out/'channel_adapter.a64.o').read_bytes())
    modules,providers,kernel=d.link.build()
    matchobj=f.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o'
    code,ro,_=f.f58.object_image(matchobj.read_bytes())
    writerobj=old.STAGE/'run-bounded-stores-20261026/resource_alias.a64.o'
    wcode,wro,functions,_=old.object_image(writerobj.read_bytes());assert functions['fx3_candidate']==0x13000000
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes();assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    liro=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    assets=(blob,liro,kernel,code,ro,wcode,wro,functions);inputs=d.p.inputs()
    cases=[one_case(assets,modules,providers,adapter,'target FH priorA5',inputs[0][1],0xa5,386,True),
           one_case(assets,modules,providers,adapter,'target FH priorC3',inputs[0][1],0xc3,386,True),
           one_case(assets,modules,providers,adapter,'artificial FF control',inputs[1][1],0xc3,386),
           one_case(assets,modules,providers,adapter,'stock UHD control',inputs[3][1],0xc3,431)]
    for negative in ('closed','epoch','owner','magic','lock'):
        cases.append(one_case(assets,modules,providers,adapter,'target rejection '+negative,inputs[0][1],0xc3,386,True,negative))
    proof={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'status':'PASS_GUEST_ONLY_NATIVE_CHANNEL_CALLSITE_PUBLICATION_TO_OSAL_BOUNDARY',
           'cases':cases,'bounded_fragments':sum(len(c['events']) for c in cases),
           'adapter':{'object_sha256':im.sha((out/'channel_adapter.a64.o').read_bytes()),'code_bytes':len(adapter[0]),
                      'rodata_bytes':len(adapter[1]),'functions':{k:hex(v) for k,v in adapter[2].items()},'relocations':adapter[3]},
           'guest_callsite':hex(SITE),'original_call':f.f58.branch(SITE,SONY['sony_channel'],True).hex(),
           'two_guest_BL_changes':['existing matcher at av-cam+0x21ed18','new channel call at av-cam+0x21eeb4'],
           'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),'C_source_sha256':im.sha((STAGE/'channel_adapter.c').read_bytes()),
                             'match_object_sha256':im.sha(matchobj.read_bytes()),'writer_object_sha256':im.sha(writerobj.read_bytes()),
                             'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(liro),'kernel_sha256':im.sha(kernel)},
           'scope':['Publication writer is now invoked by compiled code at a declared original guest callsite, on its actual live call stack.',
                    'Adapter calls original rate getter before original channel preparation; exact FH identity remains, 16M coefficient is private.',
                    'Native constructor/queues and original resource message/LIRO-bound OSAL path continue to the unexecuted kernel IRQ-lock entry.',
                    'Control/session/epoch, muted logger and guest storage are fixtures, not trustworthy Sony runtime state or shared locks.',
                    'One producer lease stays live. No real consumer completion, restoration, code unload or safe failure return is claimed.',
                    'Negative cases stop before OUR rejection body, not a proven Sony rollback/error path.',
                    'Full Linux/OSAL initialization, actual hooking/MMU/cache sync, downstream 16M packing and hardware main recording remain incomplete.'],
           'UU_or_Windows_or_camera_operations_by_this_script':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'channel-callpath-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    (out/'compiled-source.c').write_bytes((STAGE/'channel_adapter.c').read_bytes())
    print(json.dumps({'status':proof['status'],'cases':len(cases),'bounded_fragments':proof['bounded_fragments'],
                      'target_native_rate':[25999360,16000000,26000000],'goal_complete':False}))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    im.volume();out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        (out/'attempt-source.c').write_bytes((STAGE/'channel_adapter.c').read_bytes())
        latest=globals().get('LAST_PHASE',getattr(d,'LAST_PHASE',None))
        if latest:im.write_json(out/'last-phase-at-failure.json',latest)
        if 'CURRENT_GUEST' in globals():
            m=CURRENT_GUEST
            im.write_json(out/'failure-live-state.json',{'pc':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
                'reason':m.reason,'instruction_count':len(m.pcs),'last_pcs':[hex(x) for x in m.pcs[-12:]],
                'adapter_entries':m.adapter_entries,'writer_entries':m.writer_entries,'rate_entries':m.rate_entries,
                'rate_returns':m.rate_returns,'rejection_entries':m.rejection_entries})
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        raise


if __name__=='__main__':main()
