#!/usr/bin/env python3
"""Native DMM buffer table to Open caller; all region addresses are fixtures."""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage125-native-frontend-DMM-consistency'));import frontend_dmm as prev
sys.path.insert(0,str(BASE/'stage106-native-MPR-Open-fields'));import mpr_open as builder
front,pp,r,im,MPR,SP,reg=prev.front,prev.pp,prev.r,prev.im,prev.MPR,prev.SP,prev.reg
S=pp.SCRATCH;NODES=S+0x1000;EXEC=S+0x5000;PARAM=S+0xb000;MODEL=S+0xc000;AREA=42;HEAD=0x3d5770
PRIOR=BASE/'stage125-native-frontend-DMM-consistency/final-receipt.json'
PRIOR_SHA='5e14a37c9444c476c7da652d26a540dcc65c588ba960d419824a3f61d45de337'
PREVIOUS_RESULT=PRIOR.parent/'run-native-frontend-DMM-20261027/frontend-DMM-results.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def pq(m,a,v):m.uc.mem_write(a,struct.pack('<Q',v))
def saved(m):return prev.saved(m)
def restored(m,x):return prev.restored(m,x)
def table_entries(ptr):
    rows=[]
    for i in range(64):
        raw=MPR.read(ptr+i*16,16);unit,kind,area,flag,tail=struct.unpack('<IIIHH',raw)
        if flag==0xffff:return rows
        rows.append({'original_table_row':hex(ptr+i*16),'unit_type':unit,'buffer_kind':kind,
            'original_area_word8':area,'flag12':flag,'tail14':tail})
    raise AssertionError('No bounded original table terminator')
class Guest(prev.Guest):
    def __init__(self,seed):
        super().__init__(seed);self.allowed.extend(builder.ranges())
        self.allowed.extend([(0x2afb0c,0x2b035c),(0xd6700,0xd67bc),(0xd18d8,0xd1954),(0xd1b80,0xd1bc0)])
        self.boundaries.update({0xd67b8:'after_original_Enqueue_Open_fields_before_queue_access',
            0x7dfa0:'before_original_Open_scope_lock',0x7c350:'before_original_Codec_EncOpen',
            0xd1c84:'before_original_dual_stream_Open_setup'})
    def code(self,u,pc,n,user):
        bindings={0x7d9d0:('_ZN3mpr20GetCodecInfoForCodecENS_14VideoParamCombENS_10StreamTypeE',0xcd40c),
            0x81200:('_ZN3mpr15SetEncOpenParamERNS_13execEncOpen_tEP16AvbbcApi_EncOpen',0xd13f8)}
        if pc in bindings:
            name,target=bindings[pc];assert MPR.plt[pc]==name and MPR.symbols[name]['va']==target
            self.pcs.append(hex(pc));self.calls.append({'original_symbol_binding':name,'PLT':hex(pc),'target':hex(target)})
            u.reg_write(reg('pc'),target);return
        return super().code(u,pc,n,user)
def drive(m,label,entry,outputs=(),**regs):
    ev=[m.phase(label,entry,outputs=outputs,**regs)]
    for i in range(64):
        if ev[-1]['reason']!='boundary: before_original_MPR_diagnostic':return ev
        lr=m.uc.reg_read(reg('x30'));inst=list(MPR.md.disasm(MPR.read(lr-4,4),lr-4))
        assert len(inst)==1 and inst[0].mnemonic=='bl' and inst[0].op_str=='#0xc8c70'
        ev.append(m.phase(label+' independent post-log input '+str(i+1),lr,outputs=outputs))
    raise AssertionError('Unbounded diagnostic gaps')
def trial(seed,modeid,profile,rows):
    m=Guest(seed)
    try:
        assert rows and len(rows)<32
        m.uc.mem_write(MODEL,bytes(0xb00));word0=1 if modeid in (21,31) else 2
        m.uc.mem_write(MODEL,struct.pack('<I',word0));m.uc.mem_write(PARAM,bytes.fromhex(profile['frontend_native_candidate448']))
        # Independent caller metadata, not produced by the sealed parameter helper.
        m.uc.mem_write(MODEL+0x40,struct.pack('<II',1,int(modeid in (31,32))))
        ev=[m.phase('independent original parameter-copy input from sealed native frontend result',0xccb04,
            outputs=[(MODEL+0x58,MODEL+0x58+445)],sp=SP,x30=pp.STOP,x19=MODEL,x1=PARAM)]
        assert ev[-1]['reason']=='boundary: after_original_parameter_copy_before_other_RecordStart_work'
        for i,row in enumerate(rows):
            node=bytearray(0x80);start=0x70000000+i*0x04000000;span=0x02000000
            struct.pack_into('<IIIIQ',node,0,row['buffer_kind'],AREA,0xa500+i,row['unit_type'],NODES+(i+1)*0x80 if i+1<len(rows) else 0)
            struct.pack_into('<H',node,0x18,1);struct.pack_into('<Q',node,0x20,start+span)
            struct.pack_into('<I',node,0x28,span);node[0x2c]=1;struct.pack_into('<QI',node,0x30,start,span)
            m.uc.mem_write(NODES+i*0x80,bytes(node))
        pq(m,HEAD,NODES);nodes=bytes(m.uc.mem_read(NODES,len(rows)*0x80));ss=saved(m)
        ev.append(m.phase('original SetMemTbl on explicitly declared linked area records',0x2afb0c,
            outputs=[(MODEL+0x278,MODEL+0x278+0x760)],abi=True,sp=SP,x30=pp.STOP,x0=AREA,x1=modeid,x2=MODEL+0x278))
        assert ev[-1]['reason']=='returned' and restored(m,ss)
        buffers=bytes(m.uc.mem_read(MODEL+0x278,0x760));assert any(buffers)
        m.uc.mem_write(EXEC,bytes(0x7b8))
        ee=drive(m,'independent post-log Enqueue Open: original buffer copy and main/proxy fields',0xd6700,
            outputs=[(EXEC,EXEC+0x7b8)],sp=SP,x29=EXEC-0x40,x30=pp.STOP,x19=MODEL,x20=EXEC,x2=0x760)
        ev.extend(ee);assert ev[-1]['reason']=='boundary: after_original_Enqueue_Open_fields_before_queue_access'
        request=bytes(m.uc.mem_read(EXEC,0x7b8));assert request[:0x760]==buffers
        assert struct.unpack_from('<III',request,0x764)==(6,6,3) and struct.unpack_from('<I',request,0x77c)[0]==15
        ev.append(m.phase('original ExecEncOpen prologue before log',0xd18d8,sp=SP,x30=pp.STOP,x0=EXEC))
        assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
        fp=m.uc.reg_read(reg('x29'));assert fp==SP-0x1c0
        ev.append(m.phase('independent post-log original reply48 clear before integration lock',0xd1930))
        assert ev[-1]['reason']=='boundary: before_original_Open_scope_lock'
        assert bytes(m.uc.mem_read(fp+0x60,48))==bytes(48)
        ee=drive(m,'independent post-DMM/unlock frame: original stream branch, clear98 and Open builder',0xd1b80)
        ev.extend(ee);proxy=request[0x760];raw=None
        if proxy:
            assert ev[-1]['reason']=='boundary: before_original_dual_stream_Open_setup'
        else:
            assert ev[-1]['reason']=='boundary: before_original_Codec_EncOpen'
            assert [m.uc.reg_read(reg('x'+str(i))) for i in range(6)]==[fp+0x90,32,15,1,0,fp+0x60]
            raw=bytes(m.uc.mem_read(fp+0x90,0x98))
            assert struct.unpack_from('<HH',raw,0x68)==(1920,1080) and raw[0x66]==15 and raw[0x82]==22 and raw[0x94:0x96]==b'\0\1'
            assert any(x.get('same_firmware_original_import')=='memset' for e in ee for x in e['original_imports_and_returns'])
        assert bytes(m.uc.mem_read(NODES,len(rows)*0x80))==nodes and bytes(m.uc.mem_read(EXEC,0x7b8))==request
        return {'seed':seed,'declared_mode':modeid,'source_profile':profile['source_label'],'original_unit_rows':rows,
            'declared_runtime_node_count':len(rows),'native_BufferTable760':buffers.hex(),'native_Enqueue_request7b8':request.hex(),
            'native_single_Open98':raw.hex() if raw is not None else None,'proxy_enabled':bool(proxy),'events':ev,
            'runtime_area_list_addresses_sizes_and_Model_source_are_explicit_fixtures':True,
            'original_single_Open_clear_executed':not bool(proxy),'dual_Open_unexecuted':bool(proxy),
            'actual_DMM_allocation_physical_buffer_ownership_encoder_or_file_proven':False,
            'all_real_locks_logs_prior_DMM_work_queue_access_and_Codec_Open_unexecuted':True}
    finally:m.close()
def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for x in json.loads(PRIOR.read_text())['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    sj=json.loads(PREVIOUS_RESULT.read_text())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(Path(__file__).read_bytes()),
        'native_frontend_source_result_sha256':sha(PREVIOUS_RESULT.read_bytes()),'cases':[],'goal_complete':False,'persistent_write_release':False,
        'camera_Windows_UU_operations':False,'actual_DMM_allocation_MAIN_recording_or_recovery_proven':False}
    try:
        for seed in (0xa5,0xc3):
            for modeid in (21,25,31,32):
                ptr=int(next(x['native_table_pointer_ELF'] for x in sj['table_free_cases'] if x['declared_mode']==modeid),16)
                label='proxy_disabled' if modeid in (21,25) else 'HEVC16'
                p=next(x for x in sj['profiles'] if x['seed']==seed and x['source_label']==label)
                j['cases'].append(trial(seed,modeid,p,table_entries(ptr)))
        j['bounded_phases']=sum(len(c['events']) for c in j['cases'])
        j['status']='PASS_NATIVE_DMM_BUFFER_FIELDS_TO_OPEN_CALLER_NOT_PHYSICAL_ALLOCATION'
        (out/'buffer-Open-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'cases':len(j['cases']),'bounded_phases':j['bounded_phases'],'status':j['status']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
