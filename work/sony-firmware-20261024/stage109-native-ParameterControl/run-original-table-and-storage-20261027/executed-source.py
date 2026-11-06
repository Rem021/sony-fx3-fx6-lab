#!/usr/bin/env python3
"""Original ParameterControl dispatch/storage under an explicit parameter map.

Mutex/allocator/free calls stop. Each later entry is an independent declared
input with retained native frames, not a supplied success return. No runtime
allocation, synchronization, object graph or live camera acceptance is claimed.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage108-original-Dataflow-copy'))
import dataflow_copy as prev
pp,r,im=prev.pp,prev.r,prev.im
AV,LIBC=prev.AV,prev.LIBC
MWF_SHA='06a80e89d1bba839bf4ea83492fb1fe0490037a8c8c46bf21d7ac46657d47a26'
MWF=prev.assets.PinnedNative(STAGE/'inputs/libMWF.so',MWF_SHA)
WBASE=0x30000000
CBASE=prev.CBASE
SP=prev.SP
SELF,PCONTROL,CMD,VBASE=prev.SELF,prev.PCONTROL,prev.CMD,prev.VBASE
STRUCT=pp.SCRATCH+0x7000
BOOL=pp.SCRATCH+0x7100
BODY=pp.SCRATCH+0x7200
TABLE=pp.SCRATCH+0x7300
TEMP=pp.SCRATCH+0x7400
OWNED=pp.SCRATCH+0x7500
DEBUG=pp.SCRATCH+0x7600
PRIOR=prev.STAGE/'final-receipt.json'
PRIOR_SHA='83772cc18dc70445d29df666da9251de354ab32e375eda66a595eb315081eb53'
VT='_ZTVN14AvbbcParamCtrl16ParameterControlE'
BOOL_CTOR='_ZN3MWF17ParamStd_TemplateIbLNS_5Param4TypeE1EEC1Eb'
NAMES=(BOOL_CTOR,'_ZN3MWF6ObjMsgC1Ev','_ZN3MWF5ParamC2Ev',
    '_ZNK3MWF6ObjMsg8GetParamEj','_ZN3MWF10ObjMsgBody8GetParamEjNS_5Param4TypeE',
    '_ZN3MWF8ParamMap3GetEj','_ZN3MWF8ParamMap11GetWritePosEjPPNS_5ParamEPi',
    '_ZN3MWF8ParamMap8GetParamEPNS_5ParamE','_ZN3MWF6StructC1Ev','_ZN3MWF6StructC1Eii',
    '_ZN3MWF6Struct8SetValueEPKvii','_ZN3MWF5Param5ClearEv',
    '_ZN3MWF6Struct13virtual_ClearEPNS_5ParamE',
    '_ZN3MWF17ParamStd_TemplateIbLNS_5Param4TypeE1EE8SetValueEb')


def sha(data):return hashlib.sha256(data).hexdigest()


def reg(name):return prev.reg(name)


def resolve(native,bias,select=lambda at:True):
    out=[]
    for sec in native.elf.iter_sections():
        if sec.name not in ('.rela.dyn','.rela.plt'):continue
        symbols=native.elf.get_section(sec['sh_link'])
        for item in sec.iter_relocations():
            kind=item['r_info_type'];at=item['r_offset'];value=None;symbol=''
            if not select(at):continue
            if kind==1027:value=bias+item['r_addend']
            elif kind in (257,1025,1026):
                s=symbols.get_symbol(item['r_info_sym']);symbol=s.name
                if s['st_shndx']!='SHN_UNDEF':value=bias+s['st_value']+item['r_addend']
            if value is not None:out.append({'place':bias+at,'kind':kind,'symbol':symbol,'value':value})
    return out


def map_image(m,native,bias):
    pages=set()
    for s in native.segments:pages.update(range((bias+s['p_vaddr'])&~4095,(bias+s['p_vaddr']+s['p_memsz']+4095)&~4095,4096))
    runs=[]
    for a in sorted(pages):
        if runs and runs[-1][1]==a:runs[-1][1]=a+4096
        else:runs.append([a,a+4096])
    for a,z in runs:m.uc.mem_map(a,z-a)
    for s in native.segments:m.uc.mem_write(bias+s['p_vaddr'],s.data())
    relocs=resolve(native,bias)
    for item in relocs:m.uc.mem_write(item['place'],struct.pack('<Q',item['value']))
    for a,z in runs:m.uc.mem_protect(a,z-a,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    return relocs


class Guest(prev.Guest):
    def __init__(self,seed):
        super().__init__(AV,seed,[(0xa3d98,0xa426c),(0xa37a0,0xa386c),(0xa32b4,0xa332c),(0xb2958,0xb29dc)])
        self.boundaries={0xa03f0:'before_unexecuted_malloc',0x9d050:'before_unexecuted_free',
            WBASE+0x21c00:'before_unexecuted_mutex_lock',WBASE+0x22300:'before_unexecuted_mutex_unlock',
            WBASE+0x215f0:'before_unexecuted_array_new',WBASE+0x23300:'before_unexecuted_array_delete',
            0x9e870:'before_unexecuted_AV_logger',0xb29dc:'after_second_original_vcall',
            WBASE+0x22210:'before_unexecuted_assert_fail'}
        self.mwf_relocations=map_image(self,MWF,WBASE)
        self.libc_relocations=map_image(self,LIBC,CBASE)
        vt=AV.symbols[VT]
        self.vt_relocations=resolve(AV,0,lambda at:vt['va']<=at<vt['va']+vt['size'])
        assert len(self.vt_relocations)==25 and all(x['kind']==257 for x in self.vt_relocations)
        for item in self.vt_relocations:self.uc.mem_write(item['place'],struct.pack('<Q',item['value']))
        self.allowed.extend((WBASE+MWF.symbols[n]['va'],WBASE+MWF.symbols[n]['va']+MWF.symbols[n]['size']) for n in NAMES)
        self.allowed.extend((CBASE+LIBC.symbols[n]['va'],CBASE+LIBC.symbols[n]['va']+LIBC.symbols[n]['size']) for n in ('memcpy','memset'))
        # A declared read-only imported debug value for the empty-table constructor.
        # No assertion is made about the real camera's debug input.
        self.uc.mem_write(0x1b2720,struct.pack('<Q',DEBUG));self.uc.mem_write(DEBUG,bytes(4))
        self.images=[(bias+s['p_vaddr'],bytes(self.uc.mem_read(bias+s['p_vaddr'],s['p_memsz'])))
            for n,bias in ((AV,0),(MWF,WBASE),(LIBC,CBASE)) for s in n.segments]
        self.table_reads=[]

    def observe(self,u,access,at,n,value,user):
        super().observe(u,access,at,n,value,user)
        if 0x1b62b0<=at and at+n<=0x1b66c4:
            self.table_reads.append({'pc':hex(u.reg_read(reg('pc'))),'table_offset':hex(at-0x1b62b0),
                'size':n,'original_bytes':bytes(u.mem_read(at,n)).hex()})

    def phase(self,*args,**kwargs):
        self.table_reads=[]
        result=super().phase(*args,**kwargs)
        result['original_PARAMETER_TABLE_reads']=self.table_reads
        return result

    def code(self,u,pc,n,user):
        if pc in self.boundaries:
            self.pcs.append(hex(pc));self.abort('boundary: '+self.boundaries[pc]);return
        symbol=AV.plt.get(pc)
        if WBASE<=pc<WBASE+0x100000:symbol=MWF.plt.get(pc-WBASE)
        if symbol:
            target=None
            if symbol in MWF.symbols:target=WBASE+MWF.symbols[symbol]['va']
            elif symbol in ('memcpy','memset'):target=CBASE+LIBC.symbols[symbol]['va']
            if target is not None and any(a<=target<z for a,z in self.allowed):
                self.pcs.append(hex(pc));self.steps+=1
                self.calls.append({'original_symbol_binding':symbol,'PLT':hex(pc),'native_target':hex(target),
                    'args_x0_x3':[hex(u.reg_read(reg('x'+str(i)))) for i in range(4)],
                    'declared_PC_binding_not_dynamic_loader_proof':True})
                u.reg_write(reg('pc'),target);return
        return super().code(u,pc,n,user)


def one(seed,command,raw,view):
    m=Guest(seed)
    try:
        events=[m.phase('original ParameterControl ctor with explicit null table and debug0',0xa3d98,
            outputs=[(PCONTROL,PCONTROL+0x80)],sp=SP,x30=pp.STOP,x0=PCONTROL,x1=0,x2=0)]
        vptr=struct.unpack('<Q',bytes(m.uc.mem_read(PCONTROL,8)))[0]
        assert vptr==AV.symbols[VT]['va']+0x10
        assert struct.unpack('<Q',bytes(m.uc.mem_read(PCONTROL+8,8)))[0]==0
        blob_slot=struct.unpack('<Q',bytes(m.uc.mem_read(vptr+0x60,8)))[0]
        bool_slot=struct.unpack('<Q',bytes(m.uc.mem_read(vptr+0x10,8)))[0]
        assert blob_slot==0xa37a0 and bool_slot==0xa32b4
        events.append(m.phase('original empty MWF Struct constructor',WBASE+MWF.symbols['_ZN3MWF6StructC1Ev']['va'],
            outputs=[(STRUCT,STRUCT+24)],sp=SP,x30=pp.STOP,x0=STRUCT))
        events.append(m.phase('original MWF bool constructor',WBASE+MWF.symbols[BOOL_CTOR]['va'],
            outputs=[(BOOL,BOOL+16)],sp=SP,x30=pp.STOP,x0=BOOL,x1=0))
        assert struct.unpack('<Q',bytes(m.uc.mem_read(STRUCT,8)))[0]==0
        # Actual population/AddParam/allocations are not executed. This graph is a
        # separate declared input, sorted as required by original binary lookup.
        m.uc.mem_write(PCONTROL+8,struct.pack('<Q',BODY));m.uc.mem_write(BODY,bytes(0x60))
        m.uc.mem_write(BODY+0x10,struct.pack('<IIQ',2,0,TABLE))
        m.uc.mem_write(TABLE,struct.pack('<IIQIIQ',0x1001,0,STRUCT,0x1057,0,BOOL))
        m.uc.mem_write(SELF+0x10,struct.pack('<Q',PCONTROL));m.uc.mem_write(CMD,command);m.uc.mem_write(VBASE,raw)
        args=dict(sp=SP,x30=pp.STOP,x0=SELF,x1=CMD)
        events.append(m.phase('original SetParameter first actual vcall through original relocated vtable',0xb2958,
            complete=False,**args))
        assert events[-1]['reason']=='boundary: before_unexecuted_mutex_lock'
        events.append(m.phase('independent post-lock original lookup for1001',WBASE+0x29ca0,complete=False))
        assert events[-1]['reason']=='boundary: before_unexecuted_mutex_unlock'
        assert m.uc.reg_read(reg('x19'))==STRUCT
        events.append(m.phase('independent post-unlock original GetParam return to blob setter',WBASE+0x29cbc,complete=False))
        assert events[-1]['reason']=='boundary: before_unexecuted_malloc' and m.uc.reg_read(reg('x0'))==0x38
        events.append(m.phase('independent declared temporary buffer; original zero/copy and Struct Clear',0xa37d4,
            outputs=[(TEMP,TEMP+0x38),(STRUCT,STRUCT+24)],complete=False,x0=TEMP))
        assert events[-1]['reason']=='boundary: before_unexecuted_array_new'
        assert m.uc.reg_read(reg('x0'))==0x38 and bytes(m.uc.mem_read(TEMP,0x38))==command
        events.append(m.phase('independent declared Struct storage; original second copy and length stores',WBASE+0x2f7b8,
            outputs=[(OWNED,OWNED+0x38),(STRUCT,STRUCT+24)],complete=False,x0=OWNED))
        assert events[-1]['reason']=='boundary: before_unexecuted_free'
        assert bytes(m.uc.mem_read(OWNED,0x38))==command
        assert struct.unpack('<Q',bytes(m.uc.mem_read(STRUCT,8)))[0]==OWNED
        assert struct.unpack('<2I',bytes(m.uc.mem_read(STRUCT+0x10,8)))==(0x38,0)
        assert m.uc.reg_read(reg('x0'))==TEMP and m.uc.reg_read(reg('x30'))==0xb299c
        events.append(m.phase('independent parent entry after unexecuted free; original bool vcall',0xb299c,
            outputs=[(SELF+0x1b8,SELF+0x1b9)],complete=False))
        assert events[-1]['reason']=='boundary: before_unexecuted_mutex_lock'
        events.append(m.phase('independent post-lock original lookup for1057',WBASE+0x29ca0,complete=False))
        assert events[-1]['reason']=='boundary: before_unexecuted_mutex_unlock' and m.uc.reg_read(reg('x19'))==BOOL
        events.append(m.phase('independent post-unlock original bool store and return to parent',WBASE+0x29cbc,
            outputs=[(BOOL,BOOL+8)],complete=False))
        assert events[-1]['reason']=='boundary: after_second_original_vcall'
        assert struct.unpack('<Q',bytes(m.uc.mem_read(BOOL,8)))[0]==1
        assert m.uc.reg_read(reg('x20'))==VBASE and m.uc.reg_read(reg('w23'))==(0x805720f9 if view==1 else 0x805700f9)
        assert bytes(m.uc.mem_read(CMD,0x38))==command and bytes(m.uc.mem_read(VBASE,0x98))==raw
        assert bytes(m.uc.mem_read(SELF+0x1b8,1))==command[0x20:0x21]
        native_bindings=[c['original_symbol_binding'] for e in events for c in e['original_calls_and_returns'] if 'original_symbol_binding' in c]
        assert native_bindings.count('memcpy')==2 and native_bindings.count('memset')==1
        return {'seed':seed,'declared_view':view,'command38_hex':command.hex(),'original_vptr':hex(vptr),
            'original_blob_setter_slot60':hex(blob_slot),'original_bool_setter_slot10':hex(bool_slot),
            'original_ABS64_vtable_relocations':m.vt_relocations,
            'declared_parameter_map':[[0x1001,hex(STRUCT)],[0x1057,hex(BOOL)]],
            'temporary38_hex':bytes(m.uc.mem_read(TEMP,0x38)).hex(),
            'Struct_storage38_hex':bytes(m.uc.mem_read(OWNED,0x38)).hex(),
            'Struct_value_pointer':hex(OWNED),'Struct_length':56,'Struct_opaque_extra':0,'native_bool1057':1,
            'nested_raw_virtual_pointer_retained':hex(struct.unpack_from('<Q',command,0x30)[0]),
            'raw98_unchanged_and_not_part_of_56_byte_Struct_copy':True,
            'native_bindings':native_bindings,'events':events,
            'post_mutex_allocator_free_entries_are_independent_inputs_not_success_returns':True,
            'actual_parameter_map_population_allocation_synchronization_or_raw_buffer_lifetime_proven':False,
            'full_SetParameter_MAIN16M_hardware_or_recovery_proven':False}
    finally:m.close()


def missing(seed,key):
    m=Guest(seed)
    try:
        events=[m.phase('original empty ParameterControl ctor for missing-key control',0xa3d98,
            outputs=[(PCONTROL,PCONTROL+0x80)],sp=SP,x30=pp.STOP,x0=PCONTROL,x1=0,x2=0)]
        m.uc.mem_write(PCONTROL+8,struct.pack('<Q',BODY));m.uc.mem_write(BODY,bytes(0x60))
        done=pp.STOP+0x100;m.boundaries[done]='after_original_missing_parameter_setter_return'
        entry=0xa37a0 if key==0x1001 else 0xa32b4
        saved={name:m.uc.reg_read(reg(name)) for name in ['x'+str(i) for i in range(19,30)]+['d'+str(i) for i in range(8,16)]}
        events.append(m.phase('original setter before missing-key lookup lock',entry,complete=False,
            sp=SP,x30=done,x0=PCONTROL,x1=key,x2=CMD if key==0x1001 else 1,x3=0x38))
        assert events[-1]['reason']=='boundary: before_unexecuted_mutex_lock'
        events.append(m.phase('independent post-lock original empty-map lookup',WBASE+0x29ca0,complete=False))
        assert events[-1]['reason']=='boundary: before_unexecuted_mutex_unlock' and m.uc.reg_read(reg('x19'))==0
        events.append(m.phase('independent post-unlock original missing-key return with debug0',WBASE+0x29cbc,complete=False))
        assert events[-1]['reason']=='boundary: after_original_missing_parameter_setter_return'
        assert m.uc.reg_read(reg('sp'))==SP and all(m.uc.reg_read(reg(name))==v for name,v in saved.items())
        assert not any('malloc' in e['reason'] or 'array_new' in e['reason'] for e in events)
        return {'seed':seed,'missing_key':hex(key),'setter_entry':hex(entry),'events':events,
            'original_GetParam_returned_null':True,'no_parameter_store_or_allocator_branch':True,
            'original_wrapper_returned_after_independent_mutex_gaps':True,
            'original_callsite_has_no_return_admission_check':True,
            'actual_camera_missing_parameter_or_mutex_effects_proven':False}
    finally:m.close()


def actual_table_prefix(seed):
    m=Guest(seed)
    try:
        event=m.phase('original ctor with original MovieEncoder PARAM_TABLE to first allocator boundary',0xa3d98,
            outputs=[(PCONTROL,PCONTROL+0x80)],complete=False,
            sp=SP,x30=pp.STOP,x0=PCONTROL,x1=0x1b62b0,x2=0x80550122)
        assert event['reason']=='boundary: before_unexecuted_array_new' and m.uc.reg_read(reg('x0'))==56
        assert event['original_PARAMETER_TABLE_reads']==[
            {'pc':'0xa3eb4','table_offset':'0x0','size':4,'original_bytes':'01100000'},
            {'pc':'0xa3ec0','table_offset':'0x4','size':4,'original_bytes':'0b000000'},
            {'pc':'0xa40f0','table_offset':'0x8','size':4,'original_bytes':'38000000'}]
        return {'seed':seed,'events':[event],'original_table_VA':'0x1b62b0',
            'original_owner_ID_argument':'0x80550122','first_original_record':[0x1001,11,56],
            'native_first_Struct_allocation_requested_bytes':56,
            'actual_new_AddParam_map_population_or_runtime_instance_proven':False}
    finally:m.close()


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        data=(ROOT/f['path']).read_bytes();assert len(data)==f['bytes'] and sha(data)==f['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    a.out.mkdir(exist_ok=False);(a.out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        source=prev.STAGE/'run-native-payload-and-header-20261027/dataflow-results.json';j=json.loads(source.read_text());rows=[]
        for i,c in enumerate(j['AV_consumers']):
            s=j['MPR_payload_copies'][i];assert s['seed']==c['seed']
            rows.append(one(c['seed'],bytes.fromhex(c['command38_hex']),bytes.fromhex(s['copied_raw98_hex']),c['declared_view']))
        negative=[missing(seed,key) for seed in (0xa5,0xc3) for key in (0x1001,0x1057)]
        table=[actual_table_prefix(seed) for seed in (0xa5,0xc3)]
        result={'status':'PASS_ORIGINAL_VTABLE_AND_PARAMETER_STORAGE_UNDER_DECLARED_MAP_NOT_RUNTIME_LIFETIME',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cases':rows,
            'negative_missing_parameter':negative,'original_table_prefix':table,
            'bounded_phases':sum(len(c['events']) for c in rows+negative+table),'source':str(source.relative_to(ROOT)),
            'source_sha256':sha(source.read_bytes()),'original_MWF_sha256':MWF_SHA,
            'actual_mutex_malloc_new_free_or_return_output_success_adapters_executed':False,
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
        (a.out/'parameter-control-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':result['status'],'cases':len(rows),'bounded_phases':result['bounded_phases']}))
    except BaseException:
        (a.out/'attempt-failure.json').write_text(json.dumps({'passing_result':False,'traceback':traceback.format_exc()},indent=2)+'\n');raise


if __name__=='__main__':main()
