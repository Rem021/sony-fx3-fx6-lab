#!/usr/bin/env python3
"""Original MAIN quality domains, nominal queries and conditional resource view.

No menu/firmware patch. Separate native app, generic MPR type helper, MPR Open,
scalar receiver and matcher experiments have explicit input boundaries. They do
not form an actual runtime transaction or prove camera/mux/encoder acceptance.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage106-native-MPR-Open-fields'));import mpr_open as mp
sys.path.insert(0,str(BASE/'stage33-imola-format-matcher'));import imola_matcher as matcher
main=mp.prev;pp,r,im,APP,MPR=mp.pp,mp.r,mp.im,main.APP,mp.MPR
SP=mp.SP;INPUT=mp.INPUT;OUTPUT=mp.OUTPUT
PRIOR=BASE/'stage114-native-callback-release-order/final-receipt.json'
PRIOR_SHA='96f158b600124e5430fb7f95c974289638f6997c80f74b2255dcdaaec4b51ca2'
def sha(b):return hashlib.sha256(b).hexdigest()
def reg(n):return getattr(r.reg,'UC_ARM64_REG_'+n.upper())

def table_inventory():
    raw=APP.read(0x398966c,26);rows=[]
    for i,v in enumerate(raw):
        at=0x2e6edb0+struct.unpack('b',bytes([v]))[0]*4
        ins=next(APP.md.disasm(APP.read(at,4),at));assert ins.mnemonic=='mov' and ins.op_str.startswith('w0, #')
        rows.append({'selector':i+1,'table_byte':v,'original_target':hex(at),
            'original_instruction':ins.bytes.hex(),'asm':ins.mnemonic+' '+ins.op_str,'MAIN_quality':int(ins.op_str.split('#')[1],0)})
    assert rows[1]['MAIN_quality']==6 and rows[3]['MAIN_quality']==8
    return {'table_address':'0x398966c','original_bytes_hex':raw.hex(),'rows':rows,
        'selectors_are_internal_input_values_not_menu_positions':True}

def app_core(seed,fmt,selector):
    m=main.Guest(seed)
    try:
        raw=bytearray(0x100);struct.pack_into('<4I',raw,0x10,15,fmt,selector,0)
        m.uc.mem_write(main.INPUT,bytes(raw))
        e=[m.phase('original app producer prologue before logging',0x2e6e5d8,stack_bytes=0xa00,
            sp=SP,x30=pp.STOP,x0=main.INPUT,x1=main.OUTPUT)]
        assert e[-1]['reason']=='boundary: before_original_app_logger'
        fp=m.uc.reg_read(reg('x29'))
        e.append(m.phase('independent app MAIN conversion with original quality selector',0x2e6ea58,stack_bytes=0xa00))
        assert e[-1]['reason']=='boundary: before_unexecuted_audio_parameter_helper'
        result=list(struct.unpack('<3I',bytes(m.uc.mem_read(fp+0x480,12))))
        assert result==[5 if fmt==6 else 1,6 if selector==2 else 8,3]
        assert bytes(m.uc.mem_read(main.INPUT,len(raw)))==bytes(raw)
        return {'seed':seed,'format_selector':fmt,'quality_selector':selector,'variant':0,'frame_selector':15,
            'native_MAIN_core':result,'events':e,'actual_menu_reachability_audio_full_parameter_or_HS_HD_producer_proven':False}
    finally:m.close()

class QGuest(mp.Guest):
    def __init__(self,seed):
        super().__init__(seed)
        for a in (0xc9e84,0x2c0ce0):
            s=next(s for s in MPR.symbols.values() if s['va']==a and s['size']);self.allowed.append((a,a+s['size']))
        self.allowed.append((0xd318c,0xd319c))
    def code(self,u,pc,n,user):
        if pc==0xd319c:
            self.pcs.append(hex(pc));self.abort('boundary: after_independent_SIDB_nominal_field_store');return
        return super().code(u,pc,n,user)
    def phase(self,label,entry,outputs=(),**regs):
        bs=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE));bc=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        for n,v in regs.items():self.uc.reg_write(reg(n),v)
        self.reason=None;self.steps=0;self.pcs=[];self.stores=[];self.calls=[];self.writes=[];self.reads=[]
        self.uc.emu_start(entry,0,count=10000,timeout=1000000)
        assert self.reason=='returned' or self.reason and self.reason.startswith('boundary: '),self.reason
        for w in self.stores:
            a,n=int(w['address'],16),w['size'];assert SP-0x200<=a and a+n<=SP or any(x<=a and a+n<=z for x,z in outputs),w
        ass=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE));assert ass[:SP-0x200-pp.STACK_BASE]==bs[:SP-0x200-pp.STACK_BASE] and ass[SP-pp.STACK_BASE:]==bs[SP-pp.STACK_BASE:]
        ac=bytes(self.uc.mem_read(pp.SCRATCH,0x10000));assert all(any(a<=pp.SCRATCH+i<z for a,z in outputs) for i,(a,b) in enumerate(zip(bc,ac)) if a!=b)
        for a,d in self.original_relocated_image:assert bytes(self.uc.mem_read(a,len(d)))==d
        assert all('stub' not in c for c in self.calls)
        return {'label':label,'entry':hex(entry),'reason':self.reason,'stop_pc':hex(self.uc.reg_read(reg('pc'))),
            'pcs':self.pcs,'stores':self.stores,'original_local_PLT_and_return_observations':self.calls,
            'whole_stack_outside_200_byte_declared_frame_unchanged':True,'whole_scratch_outside_declared_outputs_unchanged':True,
            'whole_original_relocated_ELF_image_unchanged':True,'stubs_logger_or_success_return_adapters_executed':False}

def scalar_paths(seed):
    m=QGuest(seed)
    try:
        types=[]
        for label,args,expected in [('HEVC_HD42010',(1,2,0,1,0),6),('HEVC_UHD42010',(1,3,0,1,0),5),
            ('HEVC_HD422_row8',(1,2,1,1,0),8),('invalid_HEVC_HD_depth0',(1,2,0,0,0),13),
            ('AVC_HD4208',(0,2,0,0,0),1)]:
            e,value=m.call_slices('original generic VPC '+label,0xc9e84,list(args));assert value==expected
            types.append({'label':label,'declared_typed_enums':list(args),'native_VPC':value,'events':e,
                'generic_conversion_not_actual_app_MAIN_caller_or_hardware_support':True})
        qualities=[]
        for quality in (6,8):
            e,api=m.call_slices('original DefStruct quality to codec quality',0xd0758,[quality])
            assert api==(22 if quality==6 else 24)
            n,nominal=m.call_slices('original nominal video bitrate table query',0x2c0ce0,[quality]);assert nominal==(16000 if quality==6 else 25000)
            fp=SP-0x200;m.uc.mem_write(INPUT+0x146c,struct.pack('<I',quality))
            # Independent late caller frame. W20=1000 is also present in the
            # original function, checked statically when sealing. No SIDB I/O.
            meta=m.phase('independent original SIDB nominal-query/divide/store slice',0xd318c,
                sp=fp,x29=fp,x30=pp.STOP,x19=INPUT,x20=1000)
            assert meta['reason']=='boundary: after_independent_SIDB_nominal_field_store'
            field=struct.unpack('<H',bytes(m.uc.mem_read(fp+0xb4,2)))[0];assert field==nominal//1000
            qualities.append({'MAIN_quality':quality,'native_API_quality':api,'native_nominal_query':nominal,
                'native_SIDB_slice_u16':field,'events':e+n+[meta],
                'actual_SIDB_commit_mux_header_or_measured_bitrate_proven':False})
        return {'seed':seed,'generic_VPC_cases':types,'quality_cases':qualities,
            'log_gaps_are_independent_inputs':m.log_gaps}
    finally:m.close()

def pinned_result(stage,relative):
    manifest=json.loads((BASE/stage/'final-receipt.json').read_text());p=BASE/stage/relative
    member=next(x for x in manifest['files'] if x['path']==str(p.relative_to(ROOT)))
    data=p.read_bytes();assert len(data)==member['bytes'] and sha(data)==member['sha256']
    return json.loads(data),{'path':str(p.relative_to(ROOT)),'sha256':sha(data)}

def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for x in json.loads(PRIOR.read_text())['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source':str(Path(__file__).relative_to(ROOT)),'source_sha256':sha(Path(__file__).read_bytes()),
        'app_quality_table':table_inventory(),'app_cases':[],'scalar_cases':[],'FF_produced':[],
        'FF_classified':[],'resource_cases':[],'goal_complete':False,'persistent_write_release':False,
        'Windows_UU_camera_operations':False,'actual_MAIN_source_runtime_hardware_or_recovery_proven':False}
    try:
        blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
        assert sha(blob)==matcher.r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
        old,receipt=pinned_result('stage106-native-MPR-Open-fields','run-negative-boundaries-20261027/mpr-open-results.json')
        j['reused_FH_original_outputs']=[p for p in old['produced'] if p['label']=='target_HEVC_HD420']
        assert len(j['reused_FH_original_outputs'])==2
        j['reused_FH_receipt']=receipt
        desc,receipt=pinned_result('stage32-resource-open-descriptor','run-enum-bound-20261025/resource-descriptor-results.json')
        j['reused_descriptor_receipt']=receipt;target=bytes.fromhex(desc['cases'][0]['descriptor_hex'])
        rows=matcher.inventory(blob)
        for seed in (0xa5,0xc3):
            for fmt in (6,8):
                for sel in (2,4):j['app_cases'].append(app_core(seed,fmt,sel))
            scalar=scalar_paths(seed);j['scalar_cases'].append(scalar)
            vpc=next(x['native_VPC'] for x in scalar['generic_VPC_cases'] if x['label']=='HEVC_HD42010')
            core_quality=next(x['native_MAIN_core'][1] for x in j['app_cases'] if x['seed']==seed and x['format_selector']==6 and x['quality_selector']==4)
            p=mp.produce(seed,('native_generic_HD_with_native_app_FF_quality',vpc,core_quality,3));j['FF_produced'].append(p)
            assert p['core_fields']['quality82']==24
            c=mp.classify(blob,p);j['FF_classified'].append(c)
            assert c['decoded']['quality']['original_name']=='FF' and c['decoded']['quality']['native_enum']==6
            # Isolate this quality-domain handoff in the previously produced
            # original HD descriptor. Other descriptor fields/tail are retained
            # declared inputs, not a new full resource-builder transaction.
            d=bytearray(target);struct.pack_into('<I',d,0x38,c['decoded']['quality']['native_enum'])
            assert [i for i,(a,b) in enumerate(zip(target,d)) if a!=b]==[0x38]
            for label,value,index in [('retained_target_FH_control',target,-1),('native_FF_quality_field_handoff',bytes(d),386)]:
                match=matcher.match(blob,label,value,2,10,rows)
                assert match['independent_matcher']['matched_row']==index
                j['resource_cases'].append({'seed':seed,'quality_field_only_handoff_not_complete_MPR_receiver_or_real_image_tail':True,'match':match})
        phases=sum(len(x['events']) for x in j['app_cases'])
        phases+=sum(len(x['events']) for c in j['scalar_cases'] for x in c['generic_VPC_cases']+c['quality_cases'])
        phases+=sum(len(p['original_builder_events'])+sum(len(q['events']) for q in p['category_queries']) for p in j['FF_produced'])
        phases+=sum(len(c['events']) for c in j['FF_classified'])+len(j['resource_cases'])*2
        j['new_bounded_phases']=phases;j['reused_old_FH_phases_counted_as_new']=False
        j['status']='PASS_ORIGINAL_MAIN_QUALITY_DOMAINS_DISTINGUISH_FH16K_FROM_FF25K'
        (out/'quality-domain-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':j['status'],'app_cases':len(j['app_cases']),'FF_Open_cases':len(j['FF_produced']),
            'resource_cases':len(j['resource_cases']),'new_bounded_phases':phases}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
