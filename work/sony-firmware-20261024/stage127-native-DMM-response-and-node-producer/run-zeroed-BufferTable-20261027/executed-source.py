#!/usr/bin/env python3
"""Original DMM request/copy/node slices in Unicorn; no OSAL/service adapters.

Service gaps are independent declared frames, never successful calls. Oversize
synthetic replies use padded guest destinations, not the original caller stack.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent; BASE=STAGE.parent; ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage126-native-DMM-buffer-to-Open'))
import buffer_open as prev
pp,r,im,MPR,SP,reg=prev.pp,prev.r,prev.im,prev.MPR,prev.SP,prev.reg
S=pp.SCRATCH; MSG=S+0x100; REPLY=S+0x500; OUT=S+0x1000
NODES=S+0x2000; AREA_OUT=S+0x8000; BUF=S+0x9000
OFFSET_WORD=0x3d5718; HEAD=0x3d5770; OFFSET=0x10000000
PRIOR=BASE/'stage126-native-DMM-buffer-to-Open/final-receipt.json'
PRIOR_SHA='1519ccb3d34b2961f0fe96a1af17e3fe2cf1e8b3a3fd4d5482f61f470fe67ae9'
TABLES={21:0x368988,25:0x3691a8}
def sha(b):return hashlib.sha256(b).hexdigest()
def q(m,a):return struct.unpack('<Q',bytes(m.uc.mem_read(a,8)))[0]
def putq(m,a,v):m.uc.mem_write(a,struct.pack('<Q',v))
def why(e,name):assert e['reason']=='boundary: '+name,e['reason']

class Guest(prev.Guest):
    def __init__(self,seed):
        super().__init__(seed)
        self.allowed.extend([(0x2aec74,0x2af13c),(0x2af498,0x2af638)])
        self.boundaries.update({0x7fbf0:'before_OSAL_dynamic_id',0x7e350:'before_OSAL_valloc',
            0x7c010:'before_OSAL_set_source',0x7d7d0:'before_OSAL_send',0x7dd50:'before_OSAL_receive',
            0x83370:'before_OSAL_free_message',0x819a0:'before_host_allocator',
            0x2ae900:'before_DMM_diagnostic',0x7d4f0:'before_original_assert',
            0x2af120:'before_DMM_provider',0x7d630:'before_host_free'})
        # Original runtime table/global writes are allowed only in declared slots.
        for page in (0x368000,0x369000,0x3d5000):
            self.uc.mem_protect(page,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
        putq(self,OFFSET_WORD,OFFSET)

def reply_bytes(n,key=42,status=0,kind=0x8020,zero_at=None):
    b=bytearray(max(0x28,0x18+n*16))
    struct.pack_into('<Hh',b,0,kind,status)
    struct.pack_into('<H',b,8,n)
    struct.pack_into('<I',b,0xc,key)
    for i in range(n):
        address=0 if zero_at==i else 0x70000000+i*0x01000000
        struct.pack_into('<QI',b,0x18+i*16,address,0x200000+i*0x1000)
    return bytes(b)

def diagnose(raw):
    """Conservative offline admission only; not Sony's validity oracle."""
    if len(raw)<0x18:return {'accepted':False,'reason':'short_header'}
    kind,status=struct.unpack_from('<Hh',raw);n=struct.unpack_from('<H',raw,8)[0]
    if kind!=0x8020:return {'accepted':False,'reason':'not_expected_allocation_reply'}
    if status!=0:return {'accepted':False,'reason':'nonzero_status'}
    if not 1<=n<=8:return {'accepted':False,'reason':'chunk_count_outside_independent_caller_layout'}
    if len(raw)<0x18+n*16:return {'accepted':False,'reason':'truncated_chunks'}
    chunks=[struct.unpack_from('<QI',raw,0x18+i*16) for i in range(n)]
    if not chunks[0][0]:return {'accepted':False,'reason':'empty_first_chunk'}
    return {'accepted':True,'reason':'bounded_layout_only','chunks':n,
        'ownership_origin_physical_mapping_and_hardware_validity_proven':False}

def provider(seed,n,key=42,status=0,kind=0x8020,zero_at=None,unit=974,request=False):
    m=Guest(seed)
    try:
        # Stop before the provider wrapper so GetDmmExtList can use that boundary;
        # provider tests enter four bytes into the wrapper with x6 already declared.
        saved=prev.saved(m); ev=[m.phase('original DMM wrapper and provider prologue before dynamic ID',0x2af124,
            sp=SP,x30=pp.STOP,x0=unit,x1=OUT,x2=1,x3=AREA_OUT,x6=AREA_OUT)]
        why(ev[-1],'before_OSAL_dynamic_id');fp=m.uc.reg_read(reg('x29'));assert fp==SP-0x80
        assert [m.uc.reg_read(reg('x'+str(i))) for i in range(3)]==[0x2a,0xc7,fp+0x64]
        assert q(m,fp+0x68)==0
        # Dynamic ID data is an input to a separate post-service frame.
        m.uc.mem_write(fp+0x64,struct.pack('<I',0x123456))
        request_raw=None
        if request:
            ev.append(m.phase('independent post-dynamic frame prepares allocation arguments',0x2aed1c))
            why(ev[-1],'before_OSAL_valloc')
            assert [m.uc.reg_read(reg('x'+str(i))) for i in range(4)]==[0x61003c,fp+0x68,0x28,1]
            putq(m,fp+0x68,MSG)
            ev.append(m.phase('independent post-allocation frame builds original command20',0x2aed60,
                outputs=[(MSG,MSG+0x28)]))
            why(ev[-1],'before_OSAL_set_source')
            assert [m.uc.reg_read(reg('x0')),m.uc.reg_read(reg('w1'))]==[MSG,0x123456]
            ev.append(m.phase('independent post-set-source frame fills command fields before send',0x2aeddc,
                outputs=[(MSG,MSG+0x28)]))
            why(ev[-1],'before_OSAL_send')
            assert [m.uc.reg_read(reg('x0')),m.uc.reg_read(reg('x1'))]==[0x61003c,MSG]
            expected=bytearray(0x28);struct.pack_into('<H',expected,0,0x20)
            struct.pack_into('<I',expected,4,unit);struct.pack_into('<I',expected,0xc,0xffffffff)
            struct.pack_into('<H',expected,0x16,1)
            request_raw=bytes(m.uc.mem_read(MSG,0x28));assert request_raw==bytes(expected)
            ev.append(m.phase('independent post-send frame prepares receive and infinite timeout',0x2aeed0))
            why(ev[-1],'before_OSAL_receive')
            assert [m.uc.reg_read(reg('w0')),m.uc.reg_read(reg('x1')),m.uc.reg_read(reg('w2'))]==[0x123456,fp+0x68,0xffffffff]
        raw=reply_bytes(n,key,status,kind,zero_at);m.uc.mem_write(REPLY,raw);putq(m,fp+0x68,REPLY)
        # 0x200 padded guest allocation contains all deliberately malformed copies.
        # Nothing here is the original 0xa8 stack output or a hardware address.
        before=bytes(m.uc.mem_read(OUT,0x200))
        ev.append(m.phase('independent received bytes: original discriminator/status/copy',0x2aef0c,
            outputs=[(OUT,OUT+0x200)],x26=0x123456))
        copied=None; nominal_overwrite=[];returned=None
        if ev[-1]['reason']=='boundary: before_DMM_diagnostic':
            assert bytes(m.uc.mem_read(OUT,0x200))==before
        else:
            why(ev[-1],'before_OSAL_free_message')
            copied=bytes(m.uc.mem_read(OUT,0xa8))
            length=0x18+n*16 if n else 0x28
            expected=bytearray(0xa8);expected[:min(length,0xa8)]=raw[:min(length,0xa8)]
            struct.pack_into('<QQ',expected,0x98,struct.unpack_from('<Q',raw,0x18)[0]+OFFSET,OFFSET)
            assert copied==bytes(expected)
            tail=bytes(m.uc.mem_read(OUT+0xa8,0x200-0xa8))
            nominal_overwrite=[0xa8+i for i,(a,b) in enumerate(zip(before[0xa8:],tail)) if a!=b]
            assert not nominal_overwrite if n<=9 else nominal_overwrite
            ev.append(m.phase('independent post-message-free frame prepares dynamic ID release',0x2af0a4))
            why(ev[-1],'before_OSAL_dynamic_id')
            assert [m.uc.reg_read(reg('w0')),m.uc.reg_read(reg('w1')),m.uc.reg_read(reg('w2'))]==[0x4a,0,0x123456]
            ev.append(m.phase('independent post-ID-release frame writes unit and original return',0x2af0b4,
                outputs=[(OUT+0x10,OUT+0x14)]))
            assert ev[-1]['reason']=='returned' and prev.restored(m,saved)
            returned=q(m,OUT+0x98);assert m.uc.reg_read(reg('x0'))==OUT
            copied=bytes(m.uc.mem_read(OUT,0xa8))
            assert struct.unpack_from('<I',copied,0x10)[0]==unit
        return {'seed':seed,'n':n,'key':key,'status':status,'kind':kind,'zero_at':zero_at,'unit':unit,
            'native_request28':request_raw.hex() if request_raw else None,'declared_reply':raw.hex(),
            'offline_admission':diagnose(raw),'native_output_a8':copied.hex() if copied else None,
            'changed_offsets_beyond_original_a8_layout_in_padded_guest':[hex(x) for x in nominal_overwrite],
            'native_translated_numeric_first_address':hex(returned) if returned is not None else None,
            'events':ev,'service_result_success_claimed':False,'real_allocation_or_reachable_firmware_bug_proven':False}
    finally:m.close()

def node_case(seed,mode,n_pattern):
    rows=prev.table_entries(TABLES[mode]); providers=[]
    for i,row in enumerate(rows):
        n=n_pattern[i%len(n_pattern)];zero=1 if n==2 and i==1 else None
        providers.append(provider(seed,n,42+i,zero_at=zero,unit=row['unit_type']))
        assert providers[-1]['offline_admission']['accepted']
    m=Guest(seed)
    try:
        saved=prev.saved(m);putq(m,HEAD,0)
        ev=[m.phase('original GetDmmExtList counts original table and reaches provider',0x2af498,
            sp=SP,x30=pp.STOP,x0=TABLES[mode],x1=AREA_OUT,x2=AREA_OUT+0x100)]
        why(ev[-1],'before_DMM_provider');fp=m.uc.reg_read(reg('x29'));assert fp==SP-0x120
        nodes=[];at=NODES
        outputs=[];image_outputs=[(HEAD,HEAD+8)]+[(int(x['original_table_row'],16)+8,int(x['original_table_row'],16)+12) for x in rows]
        for i,(row,p) in enumerate(zip(rows,providers)):
            assert [m.uc.reg_read(reg('w0')),m.uc.reg_read(reg('x1')),m.uc.reg_read(reg('w2')),m.uc.reg_read(reg('x3'))]==[
                row['unit_type'],fp+0x78,1,AREA_OUT+0x100]
            raw=bytes.fromhex(p['native_output_a8']);m.uc.mem_write(fp+0x78,raw)
            ev.append(m.phase('independent provider-output input: original node allocation size '+str(i),0x2af510,
                x0=fp+0x78))
            why(ev[-1],'before_host_allocator')
            n=p['n'];size=0x30+n*16;assert m.uc.reg_read(reg('x0'))==size
            node=at;at+=0x100;assert at<AREA_OUT
            outputs.append((node,node+size));entry=0x2af554 if i==0 else 0x2af5f4
            ev.append(m.phase('independent malloc-address input: original node zero/init/chunk/link '+str(i),entry,
                outputs=outputs+[(AREA_OUT,AREA_OUT+4)],image_outputs=image_outputs,x0=node))
            if i+1<len(rows):why(ev[-1],'before_DMM_provider')
            else:assert ev[-1]['reason']=='returned' and prev.restored(m,saved)
            nodes.append((node,size))
        assert q(m,HEAD)==NODES and struct.unpack('<I',bytes(m.uc.mem_read(AREA_OUT,4)))[0]==42
        all_nodes=[]
        for i,((node,size),row,p) in enumerate(zip(nodes,rows,providers)):
            b=bytes(m.uc.mem_read(node,size));n=p['n'];expected=bytearray(size)
            struct.pack_into('<IIIIQ',expected,0,row['buffer_kind'],42,42+i,row['unit_type'],nodes[i+1][0] if i+1<len(nodes) else 0)
            struct.pack_into('<H',expected,0x18,n);struct.pack_into('<Q',expected,0x20,int(p['native_translated_numeric_first_address'],16));expected[0x2c]=1
            total=0;rr=bytes.fromhex(p['declared_reply']);used=0
            for k in range(n):
                addr,span=struct.unpack_from('<QI',rr,0x18+k*16)
                if not addr:break
                struct.pack_into('<QI',expected,0x30+k*16,addr,span);total+=span;used+=1
            struct.pack_into('<I',expected,0x28,total);assert b==bytes(expected)
            assert struct.unpack('<I',bytes(m.uc.mem_read(int(row['original_table_row'],16)+8,4)))[0]==42+i
            all_nodes.append({'address':hex(node),'size':size,'unit':row['unit_type'],'kind':row['buffer_kind'],
                'declared_chunks':n,'nonzero_chunks_copied':used,'native_sum':total,'native_bytes':b.hex()})
        # Match the earlier zero-initialized Model buffer prefix, while keeping
        # this initialization an explicit input rather than a Sony constructor.
        m.uc.mem_write(BUF,bytes(0x760))
        ev.append(m.phase('original SetMemTbl consumes original-produced declared nodes',0x2afb0c,
            outputs=[(BUF,BUF+0x760)],abi=True,sp=SP,x30=pp.STOP,x0=42,x1=mode,x2=BUF))
        assert ev[-1]['reason']=='returned';buffers=bytes(m.uc.mem_read(BUF,0x760));assert any(buffers)
        written=[w for w in ev[-1]['stores'] if BUF<=int(w['address'],16)<BUF+0x760]
        assert written and any(w['value'] for w in written)
        return {'seed':seed,'mode':mode,'original_rows':rows,'providers':providers,'nodes':all_nodes,
            'events':ev,'native_BufferTable760':buffers.hex(),
            'BufferTable_initial_zero_is_independent_input':True,'native_BufferTable_store_count':len(written),
            'native_node_producer_executed_with_declared_post_service_and_allocation_inputs':True,
            'physical_allocation_mapping_or_ownership_proven':False,'actual_MAIN_or_recovery_proven':False}
    finally:m.close()

def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and sha(p.read_bytes())==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256':sha(Path(__file__).read_bytes()),'response_cases':[],'node_cases':[],
        'camera_Windows_UU_or_host_services_executed':False,'goal_complete':False,'persistent_write_release':False}
    try:
        for n in (0,1,2,8,9,10):j['response_cases'].append(provider(0xa5,n,request=n==1))
        for status,kind in ((1,0x8020),(-1,0x8020),(0,0x8023)):
            j['response_cases'].append(provider(0xc3,1,status=status,kind=kind))
        assert diagnose(reply_bytes(2)[:-1])['reason']=='truncated_chunks'
        assert diagnose(b'')['reason']=='short_header'
        assert diagnose(reply_bytes(1,zero_at=0))['reason']=='empty_first_chunk'
        j['node_cases'].append(node_case(0xa5,21,[1]))
        j['node_cases'].append(node_case(0xc3,25,[8,2,1]))
        all_events=[e for c in j['response_cases'] for e in c['events']]+[
            e for c in j['node_cases'] for e in c['events']]+[
            e for c in j['node_cases'] for p in c['providers'] for e in p['events']]
        j['bounded_phases']=len(all_events)
        j['status']='PASS_NATIVE_DMM_LAYOUT_AND_NODE_CONSTRUCTION_NOT_ALLOCATION_OR_RECORDING'
        (out/'DMM-response-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':j['status'],'responses':len(j['response_cases']),
            'node_cases':len(j['node_cases']),'nodes':sum(len(c['nodes']) for c in j['node_cases']),'phases':len(all_events)}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
