#!/usr/bin/env python3
"""Guest-only frontend copy plus independent original Set/Get copy slices."""
from pathlib import Path
import argparse,datetime,hashlib,io,json,struct,sys,traceback
from elftools.elf.elffile import ELFFile
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage115-native-main-quality-domains'));import quality_domains as prev
sys.path.insert(0,str(BASE/'stage108-original-Dataflow-copy'));import dataflow_copy as core
pp,r,im=core.pp,core.r,core.im;MPR,LIBC=core.MPR,core.LIBC;reg=core.reg;SP=core.SP
CODE=0x04000000;GATE=pp.SCRATCH+0xd000;SRC=pp.SCRATCH+0x1000;DST=pp.SCRATCH+0x3000
READBACK=pp.SCRATCH+0x5000;ALT=pp.SCRATCH+0x8000;AUX=pp.SCRATCH+0xb000;AUX2=pp.SCRATCH+0xb100
GLOBAL=0x38c810;AUXSTORE=0x38cc78;MAGIC=0x46583346524f4e54;EPOCH=17
PRIOR=BASE/'stage115-native-main-quality-domains/final-receipt.json'
PRIOR_SHA='65233d6955194133f55a8124da89d0c9867ead7c2584a3e2d8231fdb2c424b6d'
def sha(b):return hashlib.sha256(b).hexdigest()
def q(m,a):return struct.unpack('<Q',bytes(m.uc.mem_read(a,8)))[0]

def linked_object():
    raw=(STAGE/'scoped_frontend.a64.o').read_bytes();elf=ELFFile(io.BytesIO(raw));sy=elf.get_section_by_name('.symtab')
    assert elf['e_machine']=='EM_AARCH64' and elf['e_type']=='ET_REL'
    assert [(s.name,s['sh_flags']) for s in elf.iter_sections() if s['sh_flags']&2]==[('.text',6)]
    text=bytearray(elf.get_section_by_name('.text').data());image=bytearray(0x2000);proof=[]
    targets={'sony_type':0xc9e84,'sony_ctor':0x9a2ac,'sony_copy':core.CBASE+LIBC.symbols['memcpy']['va']}
    for i,rr in enumerate(elf.get_section_by_name('.rela.text').iter_relocations()):
        name=sy.get_symbol(rr['r_info_sym']).name;assert rr['r_info_type']==283 and rr['r_addend']==0
        at=rr['r_offset'];veneer=CODE+0x1000+i*16;target=targets[name]
        assert struct.unpack_from('<I',text,at)[0]==0x94000000
        struct.pack_into('<I',text,at,0x94000000|(((veneer-(CODE+at))//4)&0x3ffffff))
        struct.pack_into('<IIQ',image,0x1000+i*16,0x58000050,0xd61f0200,target)
        proof.append({'own_object_call_offset':hex(at),'symbol':name,'veneer':hex(veneer),'original_target':hex(target),
            'veneer_scope':'Own native LDR/BR address veneer only; original target executes and returns itself.'})
    assert {p['symbol'] for p in proof}==set(targets)
    image[:len(text)]=text;s=next(s for s in sy.iter_symbols() if s.name=='fx3_prepare_main')
    return bytes(image),CODE+s['st_value'],s['st_size'],proof
IMAGE,ENTRY,CODE_SIZE,LINKS=linked_object()

def outside_unchanged(a,b,base,allowed):
    cursor=0
    for x,z in sorted(allowed):
        lo=max(0,x-base);hi=min(len(a),z-base)
        if lo>=hi:continue
        assert a[cursor:lo]==b[cursor:lo];cursor=max(cursor,hi)
    assert a[cursor:]==b[cursor:]

class Guest(core.Guest):
    def __init__(self,seed):
        super().__init__(MPR,seed,[(CODE,CODE+CODE_SIZE),(CODE+0x1000,CODE+0x1030),
            (0xc9e84,0xc9fcc),(0x9a2ac,0x9a2c8),(0xf0ff0,0xf10c8),(0xf1110,0xf1120),(0xf1238,0xf1274)])
        self.uc.mem_map(CODE,len(IMAGE),r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC);self.uc.mem_write(CODE,IMAGE)
        self.images.append((CODE,IMAGE));self.imports[0x7d6b0]='memset'
        s=LIBC.symbols['memset'];self.allowed.append((core.CBASE+s['va'],core.CBASE+s['va']+s['size']))
        self.uc.mem_protect(0x38c000,0x1000,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
        self.boundaries={0xf0ec0:'before_SetMovieRecParam_diagnostic',0x7fd00:'before_original_parameter_check',
            0x7c5f0:'before_original_setter_mutex',0x82530:'before_original_write_lock',
            0x81860:'before_original_read_lock',0x82f40:'before_original_rw_unlock'}
    def phase(self,label,entry,outputs=(),image_outputs=(),abi=False,**regs):
        bs=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE));bc=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        bi=[(a,bytes(self.uc.mem_read(a,len(d)))) for a,d in self.images]
        for n,v in regs.items():self.uc.reg_write(reg(n),v)
        saved={n:self.uc.reg_read(reg(n)) for n in ['x'+str(i) for i in range(19,30)]+['d'+str(i) for i in range(8,16)]}
        self.reason=None;self.steps=0;self.pcs=[];self.calls=[];self.stores=[];self.writes=[];self.reads=[]
        self.uc.emu_start(entry,0,count=15000,timeout=1000000)
        assert self.reason=='returned' or self.reason and self.reason.startswith('boundary: '),self.reason
        for w in self.stores:
            a,n=int(w['address'],16),w['size']
            assert SP-0x800<=a and a+n<=SP or any(x<=a and a+n<=z for x,z in tuple(outputs)+tuple(image_outputs)),w
        ass=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE));outside_unchanged(bs,ass,pp.STACK_BASE,[(SP-0x800,SP)])
        outside_unchanged(bc,bytes(self.uc.mem_read(pp.SCRATCH,0x10000)),pp.SCRATCH,outputs)
        for a,d in bi:outside_unchanged(d,bytes(self.uc.mem_read(a,len(d))),a,image_outputs)
        assert all('stub' not in x for x in self.calls)
        if abi:
            assert self.reason=='returned' and self.uc.reg_read(reg('sp'))==SP
            assert all(self.uc.reg_read(reg(n))==v for n,v in saved.items())
        return {'label':label,'entry':hex(entry),'reason':self.reason,'stop_pc':hex(self.uc.reg_read(reg('pc'))),
            'return_u32_if_returned':self.uc.reg_read(reg('w0')) if self.reason=='returned' else None,
            'pcs':self.pcs,'stores':self.stores,'original_imports_and_returns':self.calls,
            'stack_outside2048_unchanged':True,'scratch_outside_outputs_unchanged':True,
            'images_outside_declared_data_outputs_unchanged':True,'native_saved_registers_preserved':abi,
            'actual_lock_check_log_setter_completion_or_device_executed':False}

def fixture(m,seed,site,auxsize=0,kind='positive'):
    source=bytearray(((i*29+seed)&255) for i in range(0x1c0));struct.pack_into('<3I',source,0x170,5,6,3)
    struct.pack_into('<I',source,0x118,auxsize);struct.pack_into('<Q',source,0x120,AUX if auxsize else 0)
    dst=DST;src=SRC;gate=[MAGIC,1,0x1234,EPOCH,EPOCH,1,src,dst,0x1c0,0x1c0];epoch=EPOCH
    expected=0
    if kind=='bad_magic':gate[0]^=1;expected=1
    elif kind=='closed':gate[1]=0;expected=2
    elif kind=='busy':gate[5]=0;expected=2
    elif kind=='epoch':epoch+=1;expected=3
    elif kind=='observed_epoch':gate[4]+=1;expected=3
    elif kind=='wrong_site':site+=4;expected=4
    elif kind=='short_destination':gate[9]=0x1bf;expected=5
    elif kind=='overlap':dst=src+8;gate[7]=dst;expected=5
    elif kind=='gate_destination':dst=GATE;gate[7]=dst;expected=5
    elif kind=='outside_source':src=0xfffffffffffffff0;gate[6]=src;expected=5
    elif kind=='wrong_quality':struct.pack_into('<I',source,0x174,8);expected=6
    elif kind=='wrong_frame':struct.pack_into('<I',source,0x178,4);expected=6
    elif kind=='aux_overlap':struct.pack_into('<I',source,0x118,48);struct.pack_into('<Q',source,0x120,dst);expected=5
    elif kind=='aux_outside':struct.pack_into('<I',source,0x118,48);struct.pack_into('<Q',source,0x120,0xfffffffffffffff0);expected=5
    elif kind=='aux_gate':struct.pack_into('<I',source,0x118,48);struct.pack_into('<Q',source,0x120,GATE);expected=5
    m.uc.mem_write(SRC,bytes(source));m.uc.mem_write(GATE,struct.pack('<10Q',*gate))
    aux=bytes((seed^i) for i in range(48));m.uc.mem_write(AUX,aux)
    return bytes(source),aux,src,dst,site,epoch,expected

def setter_copy(m,source,auxsize,label):
    # Independent original post-check/post-mutex/post-rwlock frame. No service
    # returns are supplied or claimed; these omitted conditions stay unproved.
    return m.phase(label,0xf1088,image_outputs=[(GLOBAL,GLOBAL+0x1bd),(AUXSTORE,AUXSTORE+auxsize)],
        x20=source,x23=GLOBAL,x19=0x38c000,x22=0x38c000)

def trial(seed,site,auxsize=0,kind='positive'):
    m=Guest(seed)
    try:
        source,aux,src,dst,site,epoch,expected=fixture(m,seed,site,auxsize,kind)
        ev=[m.phase('compiled guest-only scoped frontend with original type/constructor/memcpy',ENTRY,
            outputs=[(dst,dst+0x1c0)] if expected==0 else [],abi=True,
            sp=SP,x30=pp.STOP,x0=GATE,x1=src,x2=dst,x3=site,x4=epoch)]
        assert ev[-1]['return_u32_if_returned']==expected
        assert bytes(m.uc.mem_read(SRC,0x1c0))==source and bytes(m.uc.mem_read(AUX,48))==aux
        result={'seed':seed,'kind':kind,'declared_site':hex(site),'declared_aux_bytes':auxsize,'return_status':expected,'events':ev,
            'gate_is_guest_fixture_not_trusted_Sony_epoch_or_idle_state':True,'actual_hook_app_profile_or_camera_proven':False}
        if expected:return result
        candidate=bytes(m.uc.mem_read(DST,0x1c0));wanted=bytearray(source[:0x1bd]+bytes(3));struct.pack_into('<I',wanted,0x170,6)
        assert candidate==bytes(wanted) and list(struct.unpack_from('<3I',candidate,0x170))==[6,6,3]
        result['semantic_changed_offsets']=[i for i,(a,b) in enumerate(zip(source[:0x1bd],candidate)) if a!=b]
        assert result['semantic_changed_offsets']==[0x170]
        assert candidate[0x1bd:]==bytes(3)
        ev.append(m.phase('original setter prologue, memset and full445-byte stack copy before diagnostic',0xf0ff0,
            sp=SP,x30=pp.STOP,x0=DST))
        assert ev[-1]['reason']=='boundary: before_SetMovieRecParam_diagnostic'
        sfp=m.uc.reg_read(reg('x29'));assert bytes(m.uc.mem_read(sfp+0x50,0x1bd))==candidate[:0x1bd]
        ev.append(setter_copy(m,DST,auxsize,'independent original saved-param and auxiliary-data copy'))
        assert ev[-1]['reason']=='boundary: before_original_rw_unlock'
        stored=bytes(m.uc.mem_read(GLOBAL,0x1bd));stored_expected=bytearray(candidate[:0x1bd])
        struct.pack_into('<Q',stored_expected,0x120,AUXSTORE if auxsize else 0);assert stored==bytes(stored_expected)
        if auxsize:assert bytes(m.uc.mem_read(AUXSTORE,auxsize))==aux[:auxsize]
        ev.append(m.phase('original getter prologue before read lock',0xf1238,sp=SP,x30=pp.STOP,x0=READBACK))
        assert ev[-1]['reason']=='boundary: before_original_read_lock'
        ev.append(m.phase('independent original getter post-lock445-byte copy',0xf1258,
            outputs=[(READBACK,READBACK+0x1bd)]))
        assert ev[-1]['reason']=='boundary: before_original_rw_unlock' and bytes(m.uc.mem_read(READBACK,0x1bd))==stored
        result['original_getter_aux_pointer']=hex(q(m,READBACK+0x120))
        result['native_setter_aux_copy_and_getter_pointer_alias_proven_under_inputs']=bool(auxsize)
        if auxsize:
            newer=bytes((0x80^b) for b in aux);m.uc.mem_write(AUX2,newer)
            alt=bytearray(candidate);struct.pack_into('<Q',alt,0x120,AUX2);m.uc.mem_write(ALT,bytes(alt))
            ev.append(setter_copy(m,ALT,auxsize,'second independent original setter replaces shared auxiliary copy'))
            assert ev[-1]['reason']=='boundary: before_original_rw_unlock'
            assert bytes(m.uc.mem_read(READBACK,0x1bd))==stored and q(m,READBACK+0x120)==AUXSTORE
            assert bytes(m.uc.mem_read(AUXSTORE,auxsize))==newer[:auxsize]
            result['prior_getter_struct_unchanged_but_pointed_data_changed_after_second_setter']=True
        result['actual_synchronization_full_setter_return_or_owned_runtime_snapshot_proven']=False
        return result
    finally:m.close()

def app_site(seed,site):
    m=prev.main.Guest(seed)
    try:
        m.allowed.extend([(0x2e6f7b8,0x2e6f7c0),(0x2e6f9ac,0x2e6f9b4)])
        m.boundaries[0x15944f0]='before_original_APP_SetMovieRecParam_import'
        e=m.phase('independent original app callsite passes whole parameter pointer',site-4,
            sp=SP,x30=pp.STOP,x19=SRC)
        assert e['reason']=='boundary: before_original_APP_SetMovieRecParam_import'
        assert m.uc.reg_read(reg('x0'))==SRC and m.uc.reg_read(reg('x30'))==site+4
        return {'seed':seed,'site':hex(site),'original_param_pointer':hex(SRC),'events':[e],
            'actual_prior_app_full_construction_or_adapter_interposition_proven':False}
    finally:m.close()

def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for x in json.loads(PRIOR.read_text())['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source':str(Path(__file__).relative_to(ROOT)),'source_sha256':sha(Path(__file__).read_bytes()),
        'C_source_sha256':sha((STAGE/'scoped_frontend.c').read_bytes()),'object_sha256':sha((STAGE/'scoped_frontend.a64.o').read_bytes()),
        'own_link_veneers':LINKS,'positive_cases':[],'negative_cases':[],'app_callsite_cases':[],
        'goal_complete':False,'persistent_write_release':False,'Windows_UU_camera_operations':False,
        'real_frontend_hook_synchronization_MAIN_file_or_recovery_proven':False}
    try:
        for seed in (0xa5,0xc3):
            for site in (0x2e6f7bc,0x2e6f9b0):
                j['app_callsite_cases'].append(app_site(seed,site))
                for n in (0,48):j['positive_cases'].append(trial(seed,site,n))
            for kind in ('bad_magic','closed','busy','epoch','observed_epoch','wrong_site','short_destination',
                'overlap','gate_destination','outside_source','wrong_quality','wrong_frame','aux_overlap','aux_outside','aux_gate'):
                j['negative_cases'].append(trial(seed,0x2e6f9b0,kind=kind))
        j['bounded_phases']=sum(len(c['events']) for k in ('positive_cases','negative_cases','app_callsite_cases') for c in j[k])
        j['status']='PASS_GUEST_ONLY_SCOPED_MAIN_COPY_AND_ORIGINAL_PARAMETER_AUXILIARY_ALIAS_SCOPE'
        (out/'frontend-trial-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':j['status'],'positive_cases':len(j['positive_cases']),
            'negative_cases':len(j['negative_cases']),'app_callsite_cases':len(j['app_callsite_cases']),'bounded_phases':j['bounded_phases']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
