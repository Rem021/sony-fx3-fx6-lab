#!/usr/bin/env python3
"""AP81 read-only audit. No firmware execution, QEMU, device or runtime writes.

Reuses the predecessor's closed assignment decoder (not its rebuild entrypoint).
Only the adjacent proof is written. Python bytecode output is disabled.
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import copy, hashlib, importlib.util, json, plistlib, re, struct, subprocess

OUT = Path(__file__).resolve().parent
ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
AUDITS = OUT.parent
RUNTIME = ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime'
RUN = RUNTIME/'runs/ap81skd-b9850378'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID'] == UUID
SPEC = importlib.util.spec_from_file_location('previous_pin_audit', AUDITS/'pin-topology/audit_pin_topology.py')
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)

def sha(b): return hashlib.sha256(b).hexdigest()
def hxkey(p): return [hex(p[0]), *p[1:]]
def getkey(row, field='source'): return P.pinwords(row[field])
def read_source(p):
    b = p.read_bytes()
    proof['sources'][str(p.relative_to(ROOT))] = {'bytes':len(b),'sha256':sha(b)}
    return b
def block(k, a, n, label):
    d = P.dis(k,a,n)
    proof['code'].append({'image':k,'va':hex(a),'bytes':n,'label':label,
                          'raw':P.read(k,a,n).hex(),'instructions':d})
    return d
def check(k, a, expected):
    got = P.dis(k,a,4)[0]
    assert got['instruction'] == expected, (k,hex(a),got,expected)
    proof['instruction_checks'].append({'image':k,**got})
def s(k,a):
    st=P.string(k,a)
    proof['strings'].append({'image':k,'va':hex(a),'value':st})
    return st
def backup_value(b, ident):
    # BK4 record0: 256B header, 6B subsystem entries, 6B property entries.
    assert b[12:16] == b'BK4\0'
    ns,np,start,size=struct.unpack_from('<4I',b,16)
    sub,unit=ident>>16,ident&65535
    assert sub<ns and 256+ns*6+np*6<=start and start+size<=len(b)
    count,index=struct.unpack_from('<HI',b,256+sub*6)
    assert unit<count and index+unit<np
    at=256+ns*6+(index+unit)*6
    attr,ptr=struct.unpack_from('<HI',b,at)
    n,off=ptr>>24,ptr&0xffffff
    assert n==4 and start<=off and off+4<=start+size
    return {'id':hex(ident),'table_offset':hex(at),'attribute':hex(attr),
            'data_offset':hex(off),'raw':b[off:off+4].hex(),
            'value':struct.unpack_from('<I',b,off)[0]}

proof={'scope':'Read-only AP81 static/captured-memory audit. No QEMU or Sony execution. Only this directory written.',
       'sources':{},'instruction_checks':[],'code':[],'strings':[],
       'evidence_limits':['The AP81 original FP/LR stack proves the executing mode branch; the setter stack was not captured.',
           'Native UUD-reset origin is source-bound and strongly corroborated by seed0/4 -> captured4/4, not a sampled setter backtrace.',
           'Only the first new GET is observed; nine packets below are a conditional software-graph projection.',
           'No CP execution, sensor image, DMA, image stream or usable menu acceptance is claimed.']}

def rebuild():
    assert sha(P.DATA['ap'])=='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
    assert sha(P.DATA['cp'])=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
    for path in P.PATHS.values(): read_source(path)
    read_source(AUDITS/'pin-topology/audit_pin_topology.py')
    read_source(AUDITS/'pin-topology/pin-topology-proof.json')
    lb=read_source(RUN/'serial.log')
    lines=lb.decode(errors='replace').split('\n')
    filters=('FX3_CHANGE_MODE_INPUT','FX3_PIN_TOPOLOGY_','FX3_PIN_GRAPH_REGISTER','FX3_PIN_COMMIT','FX3_PIN_CONSUMED',
             'FX3_BOOT_TAIL_REQUEST tid=327 destination=0x90050004','FX3_BOOT_TAIL_FRAME destination=0x90050004',
             'FX3_BOOT_EVENT_LINK id=35','FX3_BOOT_EVENT_LINK id=39','FX3_SKD_DATA_ENCRYPTION_STATUS','FX3_GPE_CMD',
             'FX3_UI_WIRE tid=231 target=0x8280084d')
    proof['serial_evidence']=[{'line':i+1,'text':x.rstrip('\r')} for i,x in enumerate(lines) if any(t in x for t in filters)]
    cap=json.loads(read_source(RUNTIME/'ap81-next-pin-capture.json'))
    assert cap['reply_added'] is False and len(cap['stack'])==14
    assert any(cap['request'] in x for x in lines)
    assert all(any(st in x for x in lines) for st in cap['stack'])
    proof['captured_request_and_stack']=cap
    raw=bytes.fromhex(cap['raw'])
    assert raw[24:]==P.request(0,(0x90050004,0,2,1)) and len(raw)==48
    req_line=next(i+1 for i,x in enumerate(lines) if cap['request'] in x)

    # Independent regeneration of all original topology assignments, twice.
    ts,tr=P.tables();rd,_,_=P.ctor();rd2,_,_=P.ctor(0x1234567800000000)
    assert rd(0x9ab0000,0x6000)==rd2(0x9ab0000,0x6000)
    boot=ts['0x9ab1258'];new=ts['0x9ab2518'];blank=ts['0x9ab0d70']
    active=[r['index'] for r in boot if r['state']==1]
    current=copy.deepcopy(blank)
    for i in active:
        current[i]['state']=1;current[i]['destination']=copy.deepcopy(boot[i]['destination'])
    diffs=[i for i in range(50) if (new[i]['state'],new[i]['destination'])!=(current[i]['state'],current[i]['destination'])]
    assert diffs==[1,4,5]
    assert all(new[i]['state']==1 and current[i]['state']==0 for i in diffs)
    assert P.select((2,6,1,0,1,0))==(0x9ab2518,0)
    ram=read_source(RUN/'ui-gate-counters.bin')
    heads=[struct.unpack_from('<8Q',ram,a) for a in (0x8000,0x8a00)]
    head=heads[1];base=head[3]-0x9ab0d70
    assert head==(0x31504f5447583346,1,base+0x9ab2518,base+0x9ab0d70,327,0,3,0)
    def normalize(b):
        b=bytearray(b)
        for i in range(50):
            for off in (0,16):
                a=i*24+off;v=struct.unpack_from('<Q',b,a)[0]
                if v:struct.pack_into('<Q',b,a,v-base)
        return bytes(b)
    oldbytes=bytearray(rd(0x9ab0d70,1200))
    for i in active:oldbytes[i*24+8:i*24+24]=rd(0x9ab1258+i*24+8,16)
    sel=ram[0x8a40:0x8ef0];cur=ram[0x8ef0:0x93a0]
    assert normalize(sel)==rd(0x9ab2518,1200)
    assert normalize(cur)==bytes(oldbytes)
    consumed=[x for x in lines if 'FX3_PIN_CONSUMED ' in x]
    assert len(consumed)==33 and all(f'pin_serial={i} ' in consumed[i-1] for i in range(1,34))
    assert 'connections=11 ' in consumed[-1] and 'buffer_refs=0' in consumed[-1]
    proof['topology']={'selected':'0x9ab2518','check_existing':False,'app_runtime_base':hex(base),
        'constructor_instructions':len(tr),'constructor_twice_equal':True,'boot_active_rows':active,
        'differences':diffs,'disconnect_rows':[],
        'current_reconstruction':'initial current shadow plus 11 successfully committed boot edges; state2 rows stay0',
        'selected_rows':new,'current_rows':current,'full_RAM_rows_matched':100,
        'snapshot_offset':'0x8a00','header':[hex(x) for x in head],
        'selected_raw':sel.hex(),'current_raw':cur.hex(),
        'selected_normalized':normalize(sel).hex(),'current_normalized':normalize(cur).hex()}

    # Exact sequence route. LR is instruction AFTER a call; inspect LR-4.
    option_targets=[0x2d2f0e0+4*x for x in struct.unpack('<16h',P.read('ap',0x3934144,32))]
    assert [i for i,v in enumerate(option_targets) if v==0x2d2f404]==[6]
    assert 'enter_face_all_deletion_mode_proc' in s('ap',0x3937400)
    s('ap',0x3937540);s('ap',0x3135972);s('ap',0x3135aa0)
    for a in (0x39d30df,0x39d321c,0x39d303e,0x39d3064):s('ap',a)
    for a,expected in [(0x2d2f408,'bl #0x2d11dd4'),(0x2d11e4c,'bl #0x2de1f84'),
        (0x2de1fac,'bl #0x2ebe9c0'),(0x2ebec74,'add x0, x0, #0x518'),
        (0x2ebec78,'b #0x2ebeb3c'),(0x2ebe5e8,'bl #0x2e11138'),
        (0x2e1117c,'bl #0x2e10d78'),(0x2e112a4,'bl #0x2e10d78'),(0x2e11390,'bl #0x2e10f98'),
        (0x238030c,'bl #0x2827348'),(0x282738c,'bl #0x2827290'),
        (0x28272b8,'cmp w1, w0'),(0x28272bc,'b.hs #0x2827340'),
        (0x28272c4,'bl #0x27fd30c'),(0x28272d4,'bl #0x2ebfdfc'),
        (0x27fd38c,'mov w1, #6'),(0x27fd394,'bl #0x27bee0c'),
        (0x27fd3bc,'mov w1, #6'),(0x27fd3c0,'bl #0x27bee0c'),
        (0x27bee0c,'b #0x27beb84'),(0x27bec4c,'mov w1, #0x144'),
        (0x27bec60,'str w0, [x25]'),(0x2c245ec,'bl #0x29301ec'),
        (0x2c245f4,'str w0, [x19, #0x6e0]')]: check('ap',a,expected)
    seed=read_source(ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin')
    saved=read_source(RUN/'backup-reserved-ram.bin')
    assert sha(seed)=='bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2'
    ids=(0x2cf1841,0x2cf1842)
    sv=[backup_value(seed,i) for i in ids];rv=[backup_value(saved,i) for i in ids]
    assert [x['value'] for x in sv]==[0,4] and [x['value'] for x in rv]==[4,4]
    proof['trigger']={'sequence':'model::sequence_mode_transition::run()',
        'branch':'enter_face_all_deletion_mode_proc','desired_option':6,'parameter_id':'0x144',
        'parameter_storage':'0x8226db8 (0x821c538+0xa880)',
        'sequence_snapshot_offset':'0xf6e0','option_dispatch_targets':[hex(x) for x in option_targets],
        'option6_is_unique_dispatch_to_captured_callsite':True,
        'native_boot_reset_chain':['0x238030c','0x282738c','0x28272c4','0x27fd394/0x27fd3c0','0x27bee0c','0x27bec60','0x2c245f4'],
        'seed_values':sv,'AP81_saved_values':rv,
        'judgment':'Native public-template UUD reset is strongly supported; no evidence of erroneous GPIO/CAPID/param243/key injection. The exact AP81 setter stack was not captured.',
        'normal_no_reset_option':0,
        'normal_modes':{'boot1':'0x9ab1258','rec_still2':'0x9ab2518','rec_movie3_proxy1_network1':'0x9ab2068'},
        'do_not_patch':'Do not pre-mark1841=4 or overwrite parameter144 merely to bypass pending original reset/deletion; saved4/4 does not prove reset side effects completed.'}

    # CP task: six canonical self descriptors and six 0x38-byte Pin instances.
    cpkeys=[]
    for i in range(6):
        t,d,n,o=struct.unpack('<4I',P.read('cp',0xf15320+16*i,16));cpkeys.append((o,t,d,n))
    objs=struct.unpack('<6I',P.read('cp',0xf15380,24))
    assert cpkeys==[(0x90050004,0,2,i) for i in range(4)]+[(0x90050004,3,2,0),(0x90050004,8,2,0)]
    assert list(objs)==[0x13ad6cc+0x38*i for i in range(6)]
    for a,expected in [(0x3c6a46,'movt r1, #0x9005'),(0x3c6a4a,'bl #0x18f460'),
        (0x3c6aba,'beq.w #0x3c6c1e'),(0x3c6c50,'bl #0x5bb7d4'),
        (0x3c6c76,'cmp r5, #6'),(0x3c6c84,'mvn r0, #0x1f'),
        (0x3c6eb8,'bl #0x5bb7ce'),(0x3c6f0e,'bl #0x5ba598'),
        (0x3c6f1c,'bl #0x5ba5e6'),(0x3c6f2e,'bl #0x5bbaa4'),
        (0x3c6d84,'bl #0x5ba9f4'),(0x3c6fc4,'bl #0x5baeb0'),
        (0x3c6ddc,'str r0, [sp, #0x258]'),(0x3c6e0e,'bl #0x44f0c0'),
        (0x9b5128,'bl #0x5ba9ac'),(0x9b5152,'bl #0x5ba9ac'),
        (0x9b5174,'bl #0x5ba9ac'),(0x9b5196,'bl #0x5ba9ac'),
        (0x9b51b8,'bl #0x5ba9ac'),(0x9b51da,'bl #0x5ba9ac')]:check('cp',a,expected)
    assert s('cp',0xdeba12)=='InfraImaging.cpp'
    cpdescs=[]
    for a in (0xefa4e4,0xefa554):
        words=struct.unpack('<4I',P.read('cp',a,16));cpdescs.append({'va':hex(a),'wire_words':list(words)})
    proof['new_owner']={'sid':'0x90050004','name':'InfraImaging pin task',
        'task_entry':'0x3c6a00','receive_manager':'0x13ad6c4','reply_sender':'0x13ad6c8',
        'pin_pointer_table':'0xf15380','self_descriptor_table':'0xf15320','constructor':'0x9b50c8..0x9b51ec',
        'all_native_endpoints':[{'key':hxkey(k),'self_descriptor':hex(0xf15320+16*i),'pin_instance':hex(objs[i])} for i,k in enumerate(cpkeys)],
        'GET_outer_reply_id':'0x90050004 (SetReplyId at3c6f0e), not zero',
        'GET_not_found_status':-32,'CP_InfraBB_new_IN_descriptors':cpdescs,
        'other_new_owner_sids':[],'native_OSAL_task_display_name':'not recovered; task entry and SID are source-bound'}

    # Preserve old indices; append only the six endpoints needed by three new edges.
    config=read_source(RUNTIME/'helpers/fx3-pin-config-v1.h').decode()
    read_source(RUNTIME/'helpers/fx3-pin-core-v1.c')
    keypart=config.split('pkeys[22][4]=',1)[1].split(';',1)[0]
    oldkeys=[tuple(int(x,16) for x in re.findall(r'0x([0-9a-f]+)U',z)) for z in re.findall(r'\{([^{}]+)\}',keypart)]
    expectedold=sorted({getkey(boot[i],f) for i in active for f in ('source','destination')})
    assert oldkeys==expectedold and len(oldkeys)==22
    edges=[(getkey(new[i]),getkey(new[i],'destination')) for i in diffs]
    extra=sorted({p for e in edges for p in e}-set(oldkeys))
    assert len(extra)==6 and {p[0] for p in extra}- {p[0] for p in oldkeys}=={0x90050004}
    model=P.SoftwarePins(oldkeys+extra)
    for i in active:
        p,q=getkey(boot[i]),getkey(boot[i],'destination')
        assert struct.unpack_from('<i',model.connect(p,q),24)[0]==0
    initial={p:copy.deepcopy(model.pins[p]) for p in oldkeys}
    packets=[]
    for row,(p,q) in zip(diffs,edges):
        for cmd,endpoint,peer,op in [(0,p,None,'GET_SOURCE'),(0,q,None,'GET_DESTINATION'),(1,p,q,'REQUEST_CONNECT')]:
            business=P.request(cmd,endpoint,peer)
            reply=model.get(endpoint) if cmd==0 else model.connect(endpoint,peer)
            status=struct.unpack_from('<i',reply,28 if cmd==0 else 24)[0]
            assert status==0
            outer=endpoint[0] if cmd==0 and endpoint[0] in (0x90050004,0x9284074a,0x9080003b) else 0
            packets.append({'order':len(packets)+1,'row':row,'operation':op,'OSAL_destination':hex(endpoint[0]),
                'self':hxkey(endpoint),'peer':hxkey(peer) if peer else None,
                'request_business_hex':business.hex(),'reply_business_hex':reply.hex(),
                'reply_envelope_hex':P.envelope(reply,outer).hex(),
                'OSAL_reply_source':hex(endpoint[0]),'outer_reply_id':hex(outer),
                'OSAL_reply_destination':'active request.outer+0; captured first example81cf61c2 only',
                'condition':'GET reads registered live state; CONNECT succeeds only after explicit owned dual-endpoint commit',
                'observed_request':len(packets)==0,'observed_reply':False})
    assert len(packets)==9 and all(model.pins[p]==initial[p] for p in oldkeys)
    assert all(model.pins[p]['peer']==q and model.pins[q]['peer']==p for p,q in edges)
    proof['conditional_requests']=packets
    proof['software_extension']={'old_endpoints':22,'new_endpoints':[hxkey(p) for p in extra],
        'total_endpoints':28,'total_owners':9,'old_edges_unchanged':11,'new_edges':3,'total_edges':14,
        'preserve_old_indices_and_peer_generation':True,'queues_initially_empty':True,'buffers_created':0,
        'stale_reply_queue_must_not_be_reused':True,'not_an_integrated_backend':True}
    # Rejection/ownership checks use actual selected keys, not synthetic success fixtures.
    p,q=edges[0];lease=model.lease(p,q)
    assert struct.unpack_from('<i',model.disconnect(p),24)[0]==-24
    assert model.pins[p]['peer']==q
    model.release(lease)
    assert struct.unpack_from('<i',model.disconnect(p),24)[0]==0
    assert struct.unpack_from('<I',model.get(p),20)[0]==1
    assert struct.unpack_from('<i',model.disconnect(p),24)[0]==-26
    missing=P.SoftwarePins(oldkeys+[p])
    assert struct.unpack_from('<i',missing.connect(p,q),24)[0]==-32 and missing.pins[p]['peer'] is None
    missing.pins[p]['state']=2
    assert struct.unpack_from('<I',missing.get(p),20)[0]==2
    assert struct.unpack_from('<i',missing.get((0x90050004,0,2,99)),28)[0]==-32
    proof['software_model_checks']=['old11peer graphs unchanged after new3 commits','all3newedges reciprocal',
        'inflight disconnect refuses-24 without graph loss','release then disconnect succeeds',
        'GET reflects disconnected1 after disconnect','duplicate disconnect returns-26',
        'unregistered destination returns-32 and does not create a peer','GET reflects transition2',
        'unknown canonical key rejected-32']

    for k,a,n,label in [
        ('ap',0x2d11dd4,0xbc,'exact captured enter_face_all_deletion procedure'),
        ('ap',0x2d2f0bc,0x28,'option dispatch'),('ap',0x2d2f404,0x10,'captured caller'),
        ('ap',0x2ebe188,0x5e0,'two-pass topology disconnect then connect'),
        ('ap',0x2e11138,0x2b8,'flags0 get/get/connect, no already-connected shortcut'),
        ('ap',0x2e10d78,0x420,'GET/CONNECT wire and consumption'),
        ('ap',0x2380300,0x30,'boot automatic UUD reset check'),
        ('ap',0x2827290,0xb8,'backup versions and conditional reset'),
        ('ap',0x27fd30c,0xc4,'face deletion option6 writer caller'),
        ('ap',0x27beb84,0xec,'write desired mode142 and option144'),
        ('ap',0x2c245b0,0x58,'sequence common property snapshot'),
        ('ap',0x293019c,0xa4,'desired/current model getters'),
        ('ap',0x2ebfde8,0xb8,'backup1841/1842 four-byte accessors'),
        ('ap',0x2d2f290,0x34,'post-pin mode classification branch'),
        ('ap',0x2d2f6f4,0x258,'post-pin remaining control path; branches require uncaptured fields'),
        ('cp',0x3c6a00,0xe0,'InfraImaging task receive and cmd dispatch'),
        ('cp',0x9b50c8,0x128,'six original constructors bind self descriptors to pin instances and reply sender'),
        ('cp',0x3c6c1e,0x6c,'GET six-object search and not-found'),
        ('cp',0x3c6eb0,0xba,'GET state/self/status and both outer SID calls'),
        ('cp',0x3c6d7c,0x50,'REQUEST_CONNECT enters general pin handshake'),
        ('cp',0x3c6fbc,0x50,'REQUEST_DISCONNECT enters general pin handshake'),
        ('cp',0x3c6dcc,0x5a,'separate0104 image metadata path, not invoked by GET/CONNECT'),
        ('cp',0x5ba9f4,0x23c,'native state transition and peer handshake'),
        ('cp',0x5badd0,0xe0,'native connect completion8001'),
        ('cp',0x5baeb0,0x170,'native disconnect guards'),
        ('cp',0x5bb1a2,0xde,'native disconnect completion8002'),
        ('cp',0x1bd2cc,0x82,'InfraBB canonical endpoint lookup'),
        ('cp',0x5aa350,0xcc,'ADF canonical endpoint lookup and reply')]: block(k,a,n,label)
    proof['reply_schema']={'business_bytes':32,'envelope_bytes':24,'total_bytes':56,
        'header':'LE16[0x1000,0x8000|request.cmd,32,2]',
        'GET_words_at8':[ 'self.type','self.direction','self.index','live CP state0connected/1disconnected/2transition','self.owner','signed status'],
        'CONNECT_DISCONNECT_words_at8':['self.type','self.direction','self.index','self.owner','signed completion status','reserved0'],
        'GET_outer_reply_id_owners_in_this_delta':['0x90050004','0x9284074a'],
        'ADF_GET_outer_reply_id':'0','generic_CONNECT_DISCONNECT_outer_reply_id':'0',
        'envelope':'LE32[reply_id,a0a0a0a0],LE16[1,56],LE32[24,56,0]; last reserved zero is software choice',
        'routing':'OSAL source=actual owner; destination=active request.reply_id; never destination=reply.outer+0'}
    draw=next(i+1 for i,x in enumerate(lines) if 'FX3_GPE_CMD op=FillRect' in x)
    flush=next(i+1 for i,x in enumerate(lines) if 'FX3_GPE_CMD op=Flush' in x)
    assert req_line<draw<flush
    proof['menu_and_stream']={'new_GET_line':req_line,'FillRect_line':draw,'Flush_line':flush,
        'serial_order':'new GET and blocked SeqQueueCommon precede UI FillRect/Flush on other threads',
        'conclusion':'Empty image stream did not prevent first logical clear/flush; this is not menu usability or full no-frame tolerance.',
        'pin_commands_contain_image_buffer_or_DMA_address':False,
        'minimal_honest_policy':'Register control endpoints, keep queues empty, no frames/0104 metadata/DMA/VSYNC fabricated; any later hardware start/buffer request requires its own supported contract or accurate failure.',
        'no_frame_tolerance_after_mode_completion':'unproven: new first GET still blocked; do not claim entire mode/menu tolerates empty stream'}
    dst=OUT/'pin-topology-2-proof.json'
    dst.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'result':'PASS','proof':str(dst),'table':'0x9ab2518','difference_rows':diffs,
        'live_RAM_rows_matched':100,'requests':len(packets),'new_endpoints':6,'new_owners':1,
        'instruction_checks':len(proof['instruction_checks']),'model_checks':len(proof['software_model_checks']),
        'UUD_seed':[x['value'] for x in sv],'UUD_saved':[x['value'] for x in rv]},ensure_ascii=False))

if __name__=='__main__':
    if len(sys.argv)>1:
        for spec in sys.argv[1:]:
            k,a,n=spec.split(':')
            for row in P.dis(k,int(a,16),int(n,16)):print(row['va'],row['instruction'])
    else:rebuild()
