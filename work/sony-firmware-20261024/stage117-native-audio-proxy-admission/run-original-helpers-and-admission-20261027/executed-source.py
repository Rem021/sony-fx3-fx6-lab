#!/usr/bin/env python3
"""Native app audio/proxy generation and stricter guest-only copy admission."""
from pathlib import Path
import argparse,datetime,hashlib,io,json,struct,sys,traceback
from elftools.elf.elffile import ELFFile
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage116-scoped-MAIN-frontend'));import frontend_trial as front
prev,core,pp,r,im=front.prev,front.core,front.pp,front.r,front.im
APP,SP=prev.APP,prev.SP;reg=front.reg;PARAM=pp.SCRATCH+0x6000;INPUT=prev.main.INPUT
PRIOR=BASE/'stage116-scoped-MAIN-frontend/final-receipt.json'
PRIOR_SHA='6581e2f8681055c025e341dc85316239609041e8abfa8fded2d328967416e3bb'
def sha(b):return hashlib.sha256(b).hexdigest()
def fields(b):return {'MAIN_core':list(struct.unpack_from('<3I',b,0x170)),
    'mainAudioParamComb':struct.unpack_from('<I',b,0x184)[0],'mainAudioChannel':struct.unpack_from('<I',b,0x188)[0],
    'proxy_active_byte':b[0x196],'proxyVideoParamComb':struct.unpack_from('<I',b,0x198)[0],
    'proxyVQuality':struct.unpack_from('<I',b,0x19c)[0],'proxyFrameRate':struct.unpack_from('<I',b,0x1a0)[0],
    'proxyAudioParamComb':struct.unpack_from('<I',b,0x1ac)[0],'proxyAudioChannel':struct.unpack_from('<I',b,0x1b0)[0]}

class AppGuest(prev.main.Guest):
    def __init__(self,seed):
        super().__init__(seed)
        self.allowed.extend([(0x2e5349c,0x2e53710),(0x2e50bf0,0x2e50e58),
            (0x2e6e628,0x2e6e638),(0x2e6f074,0x2e6f0a8)])
        self.boundaries.pop(0x2e5349c,None)
        self.boundaries.update({0x2f6fe3c:'before_audio_proxy_invalid_diagnostic',
            0x2e6e638:'after_original_param_memset_before_other_initializers',
            0x2e6f0a8:'after_original_audio_proxy_calls_before_model_diagnostics'})
        self.images=[(s['p_vaddr'],bytes(self.uc.mem_read(s['p_vaddr'],s['p_memsz']))) for s in APP.segments]
        pages=set()
        for s in front.LIBC.segments:pages.update(range((core.CBASE+s['p_vaddr'])&~4095,(core.CBASE+s['p_vaddr']+s['p_memsz']+4095)&~4095,4096))
        for a in sorted(pages):self.uc.mem_map(a,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
        for s in front.LIBC.segments:self.uc.mem_write(core.CBASE+s['p_vaddr'],s.data())
        self.images.extend((core.CBASE+s['p_vaddr'],bytes(self.uc.mem_read(core.CBASE+s['p_vaddr'],s['p_memsz']))) for s in front.LIBC.segments)
        s=front.LIBC.symbols['memset'];self.allowed.append((core.CBASE+s['va'],core.CBASE+s['va']+s['size']))
    def code(self,u,pc,n,user):
        if pc==0x1591b10:
            assert APP.plt[pc]=='memset';target=core.CBASE+front.LIBC.symbols['memset']['va']
            self.pcs.append(hex(pc));self.calls.append({'original_symbol_binding':'memset','PLT':hex(pc),'target':hex(target)})
            u.reg_write(reg('pc'),target);return
        return super().code(u,pc,n,user)
    def phase(self,label,start,outputs=(),complete=False,**regs):
        bs=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE));bc=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        for n,v in regs.items():self.uc.reg_write(reg(n),v)
        saved={n:self.uc.reg_read(reg(n)) for n in ['x'+str(i) for i in range(19,30)]+['d'+str(i) for i in range(8,16)]}
        self.reason=None;self.steps=0;self.pcs=[];self.stores=[];self.calls=[];self.writes=[]
        self.uc.emu_start(start,0,count=10000,timeout=1000000)
        assert self.reason=='returned' or self.reason and self.reason.startswith('boundary: '),self.reason
        for w in self.stores:
            a,n=int(w['address'],16),w['size'];assert SP-0xb00<=a and a+n<=SP or any(x<=a and a+n<=z for x,z in outputs),w
        front.outside_unchanged(bs,bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE)),pp.STACK_BASE,[(SP-0xb00,SP)])
        front.outside_unchanged(bc,bytes(self.uc.mem_read(pp.SCRATCH,0x10000)),pp.SCRATCH,outputs)
        for a,d in self.images:assert bytes(self.uc.mem_read(a,len(d)))==d
        assert all('stub' not in c for c in self.calls)
        if complete:
            assert self.reason=='returned' and self.uc.reg_read(reg('sp'))==SP
            assert all(self.uc.reg_read(reg(n))==v for n,v in saved.items())
        return {'label':label,'entry':hex(start),'reason':self.reason,'stop_pc':hex(self.uc.reg_read(reg('pc'))),
            'pcs':self.pcs,'stores':self.stores,'original_returns_and_bindings':self.calls,
            'stack_outside_declared_b00_unchanged':True,'scratch_outside_outputs_unchanged':True,
            'whole_mapped_APP_and_libc_unchanged':True,'saved_registers_checked_on_return':complete,
            'actual_logs_runtime_state_or_success_return_adapters':False}

def matrix_audio(m,a,b):
    m.uc.mem_write(PARAM,bytes([0x55])*0x1c0)
    e=m.phase('original audio parameter/channel helper',0x2e5349c,
        outputs=[(PARAM+0x184,PARAM+0x18c)],sp=SP,x30=pp.STOP,x0=a,x1=b,x2=PARAM+0x40,x3=PARAM+0x184,x4=PARAM+0x188)
    good=b<=11 and (b not in (9,11) or a<=3 and not(b==11 and a==0))
    assert (e['reason']=='returned')==good
    vals=list(struct.unpack('<2I',bytes(m.uc.mem_read(PARAM+0x184,8))))
    if good:
        expected=[1,2] if b==9 and a==0 else ([1,1] if b in (9,11) and a==1 else [0,1]);assert vals==expected
    return {'input44':a,'input48':b,'local_returned':good,'native_audio_pair':vals if good else None,'events':[e],
        'not_real_capture_format_or_full_parameter_admission':True}

def matrix_proxy(m,on,fmt,quality,frame=3):
    m.uc.mem_write(PARAM,bytes([0x55])*0x1c0)
    m.uc.mem_write(SP,struct.pack('<QQ',PARAM+0x1ac,PARAM+0x1b0))
    e=m.phase('original proxy format/quality/frame helper',0x2e50bf0,
        outputs=[(PARAM+0x196,PARAM+0x197),(PARAM+0x198,PARAM+0x1a4),(PARAM+0x1ac,PARAM+0x1b4)],
        sp=SP,x30=pp.STOP,x0=on,x1=fmt,x2=quality,x3=frame,
        x4=PARAM+0x196,x5=PARAM+0x198,x6=PARAM+0x1a0,x7=PARAM+0x19c)
    good=on in (1,2) or on==0 and fmt in (0,1) and quality<=3
    assert (e['reason']=='returned')==good
    f=fields(bytes(m.uc.mem_read(PARAM,0x1c0)))
    if good:
        expected=(0,13,255,12,5,255) if on in (1,2) else (1,6 if fmt==0 else 11,(6,26,26,28)[quality],frame,3,1)
        assert tuple(f[k] for k in ('proxy_active_byte','proxyVideoParamComb','proxyVQuality','proxyFrameRate','proxyAudioParamComb','proxyAudioChannel'))==expected
    return {'proxy_selector20':on,'format24':fmt,'quality28':quality,'declared_MAIN_frame':frame,
        'local_returned':good,'native_proxy_fields':f if good else None,'events':[e],
        'local_helper_does_not_validate_format_quality_pair_or_actual_frame':True}

def caller(seed,label,a,b,on,fmt,quality):
    m=AppGuest(seed)
    try:
        raw=bytearray(0x100);struct.pack_into('<4I',raw,0x10,15,6,2,0)
        struct.pack_into('<3I',raw,0x20,on,fmt,quality);struct.pack_into('<2I',raw,0x44,a,b)
        m.uc.mem_write(INPUT,bytes(raw))
        ev=[m.phase('original MAIN producer prologue before logger',0x2e6e5d8,sp=SP,x30=pp.STOP,x0=INPUT,x1=prev.main.OUTPUT)]
        assert ev[-1]['reason']=='boundary: before_original_app_logger'
        fp=m.uc.reg_read(reg('x29'));assert m.uc.reg_read(reg('x19'))==fp+0x310
        ev.append(m.phase('independent post-log original448-byte memset call',0x2e6e628))
        assert ev[-1]['reason']=='boundary: after_original_param_memset_before_other_initializers'
        assert bytes(m.uc.mem_read(fp+0x310,0x1c0))==bytes(0x1c0)
        ev.append(m.phase('independent MAIN body executes original audio and proxy helpers at original callsites',0x2e6ea58))
        assert ev[-1]['reason']=='boundary: after_original_audio_proxy_calls_before_model_diagnostics'
        param=bytes(m.uc.mem_read(fp+0x310,0x1c0));f=fields(param);assert f['MAIN_core']==[5,6,3]
        assert bytes(m.uc.mem_read(INPUT,0x100))==bytes(raw)
        return {'seed':seed,'label':label,'declared_inputs':[a,b,on,fmt,quality],
            'native_param_hex':param.hex(),'native_fields':f,'events':ev,
            'earlier_other_initializers_and_later_model_metadata_save_unexecuted':True,
            'whole_valid_source_or_real_configuration_proven':False}
    finally:m.close()

def new_image():
    e=ELFFile(io.BytesIO((STAGE/'scoped_frontend.a64.o').read_bytes()));sy=e.get_section_by_name('.symtab')
    assert [(s.name,s['sh_flags']) for s in e.iter_sections() if s['sh_flags']&2]==[('.text',6)]
    text=bytearray(e.get_section_by_name('.text').data());image=bytearray(0x2000);proof=[]
    targets={'sony_type':0xc9e84,'sony_ctor':0x9a2ac,'sony_copy':core.CBASE+front.LIBC.symbols['memcpy']['va']}
    for i,rr in enumerate(e.get_section_by_name('.rela.text').iter_relocations()):
        n=sy.get_symbol(rr['r_info_sym']).name;assert rr['r_info_type']==283 and rr['r_addend']==0
        at=rr['r_offset'];v=front.CODE+0x1000+i*16;assert struct.unpack_from('<I',text,at)[0]==0x94000000
        struct.pack_into('<I',text,at,0x94000000|(((v-front.CODE-at)//4)&0x3ffffff))
        struct.pack_into('<IIQ',image,0x1000+i*16,0x58000050,0xd61f0200,targets[n]);proof.append({'symbol':n,'target':hex(targets[n]),'offset':hex(at)})
    assert len(proof)==3;image[:len(text)]=text
    s=next(s for s in sy.iter_symbols() if s.name=='fx3_prepare_main');return bytes(image),front.CODE+s['st_value'],s['st_size'],proof
IMAGE,ENTRY,SIZE,LINKS=new_image()

def admit(source,mutation=None):
    m=front.Guest(source['seed'])
    try:
        m.uc.mem_write(front.CODE,IMAGE);m.images=[(a,d) for a,d in m.images if a!=front.CODE]+[(front.CODE,IMAGE)]
        m.allowed=[(a,z) for a,z in m.allowed if not(front.CODE<=a<front.CODE+0x2000)]+[(front.CODE,front.CODE+SIZE),(front.CODE+0x1000,front.CODE+0x1030)]
        front.fixture(m,source['seed'],0x2e6f9b0)
        p=bytearray.fromhex(source['native_param_hex'])
        if mutation=='audio_channel':struct.pack_into('<2I',p,0x184,0,2)
        if mutation=='proxy_frame':struct.pack_into('<I',p,0x1a0,12)
        m.uc.mem_write(front.SRC,bytes(p))
        f=fields(p);good=source['label'] in ('proxy_disabled','HEVC16','HEVC9','AVC6') and mutation is None
        e=m.phase('new compiled frontend admits recognized audio/proxy combinations only',ENTRY,
            outputs=[(front.DST,front.DST+0x1c0)] if good else [],abi=True,
            sp=SP,x30=pp.STOP,x0=front.GATE,x1=front.SRC,x2=front.DST,x3=0x2e6f9b0,x4=front.EPOCH)
        assert e['return_u32_if_returned']==(0 if good else 6)
        if good:
            candidate=bytes(m.uc.mem_read(front.DST,0x1c0));want=bytearray(p);struct.pack_into('<I',want,0x170,6)
            assert candidate==bytes(want) and fields(candidate)|{'MAIN_core':[5,6,3]}==f
        assert bytes(m.uc.mem_read(front.SRC,0x1c0))==bytes(p)
        return {'seed':source['seed'],'source_label':source['label'],'explicit_mutation':mutation,
            'admitted_in_guest':good,'source_fields':f,'events':[e],
            'actual_live_profile_or_full_audio_proxy_hardware_support_proven':False}
    finally:m.close()

def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for x in json.loads(PRIOR.read_text())['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source':str(Path(__file__).relative_to(ROOT)),'source_sha256':sha(Path(__file__).read_bytes()),
        'C_sha256':sha((STAGE/'scoped_frontend.c').read_bytes()),'object_sha256':sha((STAGE/'scoped_frontend.a64.o').read_bytes()),
        'own_link_veneers':LINKS,'audio_matrix':[],'proxy_matrix':[],'caller_cases':[],'admission_cases':[],'MPR_queries':[],
        'goal_complete':False,'persistent_write_release':False,'Windows_UU_camera_operations':False,
        'actual_MAIN_audio_proxy_file_or_recovery_proven':False}
    try:
        profiles=[('proxy_disabled',0,0,1,0,0),('HEVC16',1,9,0,0,0),('HEVC9',0,9,0,0,1),
            ('AVC6',2,11,0,1,3),('unlisted_HEVC6',0,0,0,0,3),('unlisted_AVC16',0,0,0,1,0)]
        for seed in (0xa5,0xc3):
            m=AppGuest(seed)
            try:
                for b in (0,9,11,12):
                    for a in range(5):j['audio_matrix'].append({'seed':seed,**matrix_audio(m,a,b)})
                for fmt in (0,1):
                    for quality in range(5):j['proxy_matrix'].append({'seed':seed,**matrix_proxy(m,0,fmt,quality)})
                for args in [(0,2,0,3),(1,2,4,3),(2,2,4,3),(3,0,0,3),(0,0,0,0),(0,0,0,12)]:
                    j['proxy_matrix'].append({'seed':seed,**matrix_proxy(m,*args)})
            finally:m.close()
            for label,a,b,on,fmt,quality in profiles:
                c=caller(seed,label,a,b,on,fmt,quality);j['caller_cases'].append(c);j['admission_cases'].append(admit(c))
            base=next(x for x in j['caller_cases'] if x['seed']==seed and x['label']=='HEVC16')
            for mutation in ('audio_channel','proxy_frame'):j['admission_cases'].append(admit(base,mutation))
        m=prev.QGuest(0xa5)
        try:
            for q,expected in ((6,16000),(26,9000),(28,6000)):
                e,value=m.call_slices('original proxy nominal quality query',0x2c0ce0,[q]);assert value==expected
                j['MPR_queries'].append({'quality':q,'native_nominal_value':value,'events':e})
        finally:m.close()
        groups=('audio_matrix','proxy_matrix','caller_cases','admission_cases','MPR_queries')
        j['bounded_phases']=sum(len(c['events']) for k in groups for c in j[k])
        j['status']='PASS_NATIVE_AUDIO_PROXY_PRODUCTION_AND_GUEST_ONLY_ADMISSION_REFINEMENT'
        (out/'audio-proxy-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:len(j[k]) for k in groups}|{'bounded_phases':j['bounded_phases'],'status':j['status']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
