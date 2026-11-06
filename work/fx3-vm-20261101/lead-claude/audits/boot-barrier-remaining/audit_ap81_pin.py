#!/usr/bin/env python3
"""Offline AP81 progress / new IMAGING pin audit; only adjacent proof writes.

Reads frozen run files and original images. No QEMU, live-memory, runtime or
device action. The nine follow-up packets are conditional software contracts,
not claims that AP81 sent or consumed them.
"""
import sys
sys.dont_write_bytecode=True
import hashlib
import importlib.util
import json
import plistlib
import re
import struct
import subprocess
from pathlib import Path

from audit_boot_barrier import ROOT,OUT,RUNTIME,DATA,PINNED,read,dis,identity
from audit_boot_tail import read_saved_run,numeric_records

RUN='ap81skd-b9850378'
FOLDER=RUNTIME/'runs'/RUN
PIN_SOURCE=ROOT/'work/fx3-vm-20261101/lead-claude/audits/pin-topology/audit_pin_topology.py'
sp=importlib.util.spec_from_file_location('readonly_original_pin_audit',PIN_SOURCE)
pin=importlib.util.module_from_spec(sp);sp.loader.exec_module(pin)
REQUEST=bytes.fromhex('c261cf81a0a0a0a001003000180000003000000000000000001000001800020000000000020000000100000000000000')
AP_BLOCKS=[(0x2d11dd4,0xb4),(0x2ebeae8,0x58),(0x2ebec6c,0x10),(0x2ebe188,0x18),(0x2ebe290,0x24),
 (0x2ebe33c,0x38),(0x2ebe454,0x20),(0x2ebe50c,0x10),(0x2ebe58c,0x64),
 (0x2e11138,0x2b8),(0x2e10d78,0x220),(0x2e10cc0,0x18)]
CP_BLOCKS=[(0x9b5114,0xdc),(0x3c6a00,0xc6),(0x3c6c1e,0x6e),(0x3c6eb0,0xb0),
 (0x3c6d7c,0x12),(0x3c7012,0x8),(0x5ba9ac,0x36),(0x5bb7ce,0x20),
 (0x1bd6aa,0x72),(0x5aa350,0xcc)]
ANCHORS=[('ap',0x2d11e4c,'bl #0x2de1f84'),('ap',0x2ebec74,'add x0, x0, #0x518'),
 ('ap',0x2ebeae8,'ldr w4, [x19, #4]'),('ap',0x2ebeb3c,'bl #0x2ebe188'),
 ('ap',0x2ebec78,'b #0x2ebeb3c'),('ap',0x2ebe33c,'ldr w0, [x29, #0x84]'),
 ('ap',0x2ebe340,'cbz w0, #0x2ebe50c'),('ap',0x2ebe598,'b.eq #0x2ebe35c'),
 ('ap',0x2ebe5e8,'bl #0x2e11138'),('ap',0x2e1117c,'bl #0x2e10d78'),
 ('ap',0x2e112a4,'bl #0x2e10d78'),('ap',0x2e11390,'bl #0x2e10f98'),
 ('cp',0x3c6a46,'movt r1, #0x9005'),('cp',0x3c6a4a,'bl #0x18f460'),
 ('cp',0x3c6c24,'strh r0, [r7, #-0x3c]'),('cp',0x3c6c76,'cmp r5, #6'),
 ('cp',0x3c6c84,'mvn r0, #0x1f'),('cp',0x3c6eb8,'bl #0x5bb7ce'),
 ('cp',0x3c6ee6,'movs r0, #0'),('cp',0x3c6f0e,'bl #0x5ba598'),
 ('cp',0x3c6f1c,'bl #0x5ba5e6'),('cp',0x3c6f2e,'bl #0x5bbaa4'),
 ('cp',0x3c6d84,'bl #0x5ba9f4'),('cp',0x3c7012,'bl #0x5badd0')]


def envelope(body,outer_id):
    assert len(body)==32
    return struct.pack('<IIHHIII',outer_id,0xa0a0a0a0,1,56,24,56,0)+body


def topo_ram(rd):
    p=FOLDER/'ui-gate-counters.bin';b=p.read_bytes();out=[]
    assert hashlib.sha256(b).hexdigest()=='004271eb3a947fab3a059e5f3d29019493381133605939925e8aca25dc9c2d88'
    receipt=json.loads((FOLDER/'receipt.json').read_bytes())
    saved=next(x for x in receipt['read_only_guest_memory_snapshots'] if x['name']==p.name)
    assert saved['sha256']==hashlib.sha256(b).hexdigest()
    old=bytearray(rd(0x9ab0d70,1200))
    for i in range(50):
        row=rd(0x9ab1258+i*24,24)
        if struct.unpack_from('<I',row,8)[0]==1:old[24*i+8:24*i+24]=row[8:]
    for index,want_selected,want_flags,expected_current in [(0,0x9ab1258,1,rd(0x9ab0d70,1200)),(1,0x9ab2518,0,bytes(old))]:
        start=0x8000+index*0xa00;head=struct.unpack_from('<8Q',b,start)
        assert head[0]==0x31504f5447583346 and head[1]==index and head[4]==327 and head[5]==want_flags
        base=head[3]-0x9ab0d70;assert head[2]-base==want_selected
        raw_selected=b[start+64:start+1264];raw_current=b[start+1264:start+2464]
        def normalize(raw):
            z=bytearray(raw)
            for off in range(0,1200,24):
                for field in [0,16]:
                    pointer=struct.unpack_from('<Q',z,off+field)[0]
                    if pointer:struct.pack_into('<Q',z,off+field,pointer-base)
            return bytes(z)
        selected=normalize(raw_selected);current=normalize(raw_current)
        assert selected==rd(want_selected,1200) and current==expected_current
        differences=[i for i in range(50) if selected[24*i:24*i+24]!=current[24*i:24*i+24]]
        assert len(differences)==head[6]
        out.append({'index':index,'file_offset':hex(start),'header_u64':list(head),'module_base':hex(base),
          'selected_VA':hex(want_selected),'flags':want_flags,'differing_rows':differences,
          'selected_normalized_hex':selected.hex(),'current_normalized_hex':current.hex(),
          'normalization':'Only two pointer fields per24B subtract modulebase; all100 rows equal independently reconstructed original assignments/current updates'})
    assert out[1]['differing_rows']==[1,4,5]
    return {**identity(p),'physical':hex(saved['address']),'captures':out}


def health_and_clear():
    lines=(FOLDER/'serial.log').read_bytes().split(b'\n')
    def hits(needle):return [{'line':i+1,'text':s.decode(errors='replace').rstrip('\r')} for i,s in enumerate(lines) if needle in s]
    receipt_path=FOLDER/'receipt.json';receipt=json.loads(receipt_path.read_bytes())
    review_path=RUNTIME/'ap81-review.json';review=json.loads(review_path.read_bytes())
    assert receipt['qemu_exit']==0 and receipt['process_reaped'] and receipt['inputs_unchanged']
    assert receipt['duration_seconds']>=240 and not receipt['guest_exception_markers'] and not receipt['menu_verified']
    assert review['im_alive_last_snapshot'] and not review['fatal'] and not review['missing_markers']
    skd={tag:hits(tag.encode()) for tag in ['FX3_SKD_HW_UNAVAILABLE ','FX3_SKD_CIPHER_RESULT ',
      'FX3_SKD_DATA_ENCRYPTION_STATUS ','FX3_SKD_DATA_ENCRYPTION_RETURN ','FX3_SKD_ACCESS_AUTH_RETURN ']}
    assert len(skd['FX3_SKD_HW_UNAVAILABLE '])==1
    assert len(skd['FX3_SKD_CIPHER_RESULT '])==len(skd['FX3_SKD_DATA_ENCRYPTION_STATUS '])==2
    assert all('original_result=-1020' in x['text'] for x in skd['FX3_SKD_CIPHER_RESULT '])
    assert all('status=2 ' in x['text'] for x in skd['FX3_SKD_DATA_ENCRYPTION_STATUS '])
    assert len(skd['FX3_SKD_ACCESS_AUTH_RETURN '])==1
    gpe=hits(b'FX3_GPE_CMD ');assert len(gpe)==2
    assert 'op=FillRect ' in gpe[0]['text'] and 'result=0 ' in gpe[0]['text']
    assert 'op=Flush ' in gpe[1]['text'] and 'result=0 ' in gpe[1]['text']
    raw_path=FOLDER/'osd-first-draw.raw';raw=raw_path.read_bytes()
    draw_path=FOLDER/'osd-first-draw.json';draw=json.loads(draw_path.read_bytes())
    assert len(raw)==0x12c000 and not any(raw)
    assert hashlib.sha256(raw).hexdigest()==draw['readback_sha256']=='3630e065eb7b4540fbab11dbfd2619e8500f211b9c404380a1867fdc44b77c0c'
    assert draw['physical_readback'] and not draw['menu_acceptance']
    images=[]
    for row in draw['renders']:
        p=Path(row['path']);assert p.parent==FOLDER
        assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'] and not row['nonuniform_pixels']
        images.append({**identity(p),'assumptions':row['assumptions'],'nonuniform_pixels':False})
    return {'receipt':{**identity(receipt_path),**{k:receipt[k] for k in ['duration_seconds','qemu_exit','process_reaped','inputs_unchanged','guest_exception_markers','menu_verified']}},
      'review':{**identity(review_path),'im_alive_last_snapshot':True,'fatal':[],'missing_markers':[]},
      'SKD_events':skd,'GPE_events':gpe,'raw_first_draw':{**identity(raw_path),'all_zero':True,'physical_readback':True},
      'renders':images,'boundaries':'Logical uniform clear only. Two interpretations both black do not establish format/channels, physical scanout, menu glyphs or input response. SKD error path is not encryption/authentication success.'}


def main():
    assert OUT==ROOT/'work/fx3-vm-20261101/lead-claude/audits/boot-barrier-remaining'
    assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    for k in ['ap','cp']:assert hashlib.sha256(DATA[k]).hexdigest()==PINNED[k]
    for k,va,want in ANCHORS:assert dis(k,va,4)[0]['instruction']==want,(k,hex(va),dis(k,va,4)[0],want)
    rd,writes,trace=pin.ctor();rd2,_,_=pin.ctor(0x7bad)
    assert all(rd(a,1200)==rd2(a,1200) for a in [0x9ab0d70,0x9ab1258,0x9ab2518])
    ts,_=pin.tables();old,new=ts['0x9ab1258'],ts['0x9ab2518']
    changed=[b for a,b in zip(old,new) if any(a[k]!=b[k] for k in ['state','source','destination'])]
    assert [r['index'] for r in changed]==[1,4,5]
    assert sum(r['state']==1 for r in old)==11 and sum(r['state']==1 for r in new)==14
    oldkeys={pin.pinwords(r[s]) for r in old if r['state']==1 for s in ['source','destination']}
    newkeys={pin.pinwords(r[s]) for r in new if r['state']==1 for s in ['source','destination']}
    assert len(oldkeys)==22 and len(newkeys)==28 and oldkeys<=newkeys
    ram=topo_ram(rd)
    native=[]
    objects=struct.unpack('<6I',read('cp',0xf15380,24))
    calls=[0x9b5128,0x9b5152,0x9b5174,0x9b5196,0x9b51b8,0x9b51da]
    for i in range(6):
        va=0xf15320+16*i;t,d,index,owner=struct.unpack('<4I',read('cp',va,16))
        assert owner==0x90050004 and objects[i]==0x13ad6cc+i*0x38
        assert dis('cp',calls[i],4)[0]['instruction']=='bl #0x5ba9ac'
        native.append({'template_VA':hex(va),'object_VA':hex(objects[i]),'AP_key':[owner,t,d,index],'constructor_call':hex(calls[i])})
    sourcekeys=[pin.pinwords(r['source']) for r in changed]
    assert all(p in [tuple(r['AP_key']) for r in native] for p in sourcekeys)
    projected=[]
    for row in changed:
        a,b=pin.pinwords(row['source']),pin.pinwords(row['destination'])
        for cmd,key,peer,op in [(0,a,None,'GET_SOURCE'),(0,b,None,'GET_DESTINATION'),(1,a,b,'CONNECT')]:
            q=pin.request(cmd,key,peer);reply=pin.response(cmd,key,state=1,status=0)
            outer=key[0] if cmd==0 and key[0] in [0x90050004,0x9284074a,0x9080003b] else 0
            full=envelope(reply,outer);assert len(full)==56
            projected.append({'row':row['index'],'operation':op,'destination':hex(key[0]),'key':list(key),
              'peer_key':list(peer) if peer else None,'request_business':q.hex(),'request_OSAL_size':len(q)+24,
              'reply_business32B':reply.hex(),'reply_OSAL56B':full.hex(),'reply_outer_id':hex(outer),
              'metadata_source':hex(key[0]),'send_to':'this request outer+0/source; only first is captured81cf61c2',
              'condition':'GET registered disconnected object; CONNECT only after software dual-endpoint commit and ownership checks'})
    assert len(projected)==9 and REQUEST[24:]==bytes.fromhex(projected[0]['request_business'])
    assert struct.unpack_from('<I',REQUEST)[0]==0x81cf61c2
    lines=(FOLDER/'serial.log').read_bytes().split(b'\n')
    req=[{'line':i+1,'text':s.decode(errors='replace').rstrip('\r')} for i,s in enumerate(lines) if b'destination=0x90050004' in s]
    assert any(('raw='+REQUEST.hex()).encode() in s for s in lines)
    commits=[s for s in lines if b'FX3_PIN_COMMIT owner=0x90050004 ' in s]
    assert not commits
    health=health_and_clear();boot=read_saved_run(RUN)
    assert all(v for k,v in boot['stages'].items() if k!='menu_verified') and not boot['stages']['menu_verified']
    selected_probes=[e for e in boot['gate_events'] if e['pc']==0x2ebe188 and e['n']==2]
    assert len(selected_probes)==1 and selected_probes[0]['x4']==6 and selected_probes[0]['x1']==0
    option_target=0x2ebeb0c+4*struct.unpack('<b',read('ap',0x39a4708+6,1))[0]
    assert option_target==0x2ebec6c and pin.select([0,6,0,0,0,0])==(0x9ab2518,0)
    helper=RUNTIME/'helpers/fx3-pin-core-v1.c';core=helper.read_text()
    assert 'struct pin_endpoint pins[22]' in core and '0x90050004' not in core
    proof={'scope':'Offline static/previous-run audit; only adjacent JSON written; no QEMU, guest memory, runtime or original changes',
      'sources':{'AP_SHA256':PINNED['ap'],'CP_SHA256':PINNED['cp'],'reused_constructor_parser':identity(PIN_SOURCE),'current_pin_core':identity(helper)},
      'anchors':[{'image':k,'VA':hex(v),'instruction':s,'bytes':dis(k,v,4)[0]['bytes']} for k,v,s in ANCHORS],
      'original_blocks':{'ap':{hex(v):dis('ap',v,n) for v,n in AP_BLOCKS},'cp':{hex(v):dis('cp',v,n) for v,n in CP_BLOCKS}},
      'AP81_health_and_clear':health,'AP81_boot_continuation':boot,
      'static_constructor':{'VA':'0x1694028','instruction_count':len(trace),'instructions':trace,'seed_independence':True},
      'full_topology_RAM_match':ram,'selected_table':'0x9ab2518','initial_table':'0x9ab1258','new_rows':changed,
      'option6_binding':{'probe':selected_probes[0],'selector_load':'2ebeae8 loads w4=input.option',
        'jump_table_byte_VA':'0x39a470e','target':hex(option_target),
        'dataflow':'option6 path2ebec6c..78 sets x0/w1 and branches to2ebeb3c; no w4 write/call before2ebe188 entry. Captured x4=6 binds actual option6, not inferred mode2.',
        'other_fields':'Full second24B input,system_mode/proxy/remote/network/stream remain unobserved'},
      'new_endpoint_keys':[list(p) for p in sorted(newkeys-oldkeys)],'all_endpoint_keys':[list(p) for p in sorted(newkeys)],
      'new_graph_counts':{'endpoints':28,'owners':len({p[0] for p in newkeys}),'edges':14,'new_endpoints':6,'new_edges':3},
      'CP_imaging':{'receiver':'0x3c6a00,90050004 via18f460','filename':read('cp',0xdeba12,32).split(b'\0')[0].decode(),
        'canonical_six_objects':native,'GET':'3c6c1e builds8000/32B;3c6eb0 copies self+state;3c6ee6 status0;unknown3c6c84 status-32',
        'outer_reply_id':'3c6f0e ->5ba598 gets90050004; metadata source3c6f1c ->5ba5e6 also90050004',
        'connect':'3c6d84 ->5ba9f4 starts generic100/8100 handshake;3c7012 ->5badd0 completes8001 only after peer completion; no physical-frame readiness claim'},
      'actual_first_request':{'raw48B':REQUEST.hex(),'source':'0x81cf61c2','serial_rows':req,'reply_consumed_in_AP81':False},
      'conditional_nine_packet_contract':projected,
      'implementation_delta':{'not_implemented_here':True,'preserve':'Keep previous22 keys/11 edges and their live peer/generation/lease state; append6 canonical keys/3 allowed edges; no sensor frames,RAW/YC/DMA success claimed',
        'required':['Provider interception must admit90050004 under explicit profile','Replace fixed22/11 capacities and loop bounds consistently, including free/resource/buffer/snapshot decoders',
          'GET outer+0 must include90050004 in provider-ID policy; metadata source=owner and destination=actual active request source',
          'Each new endpoint starts state1,peerNone,generation1,empty queues,no registeredbuffers,pending_hardware1; commit dual-endpoint graph before8001',
          'Preserve sender/generation/reference/duplicate-free guards,allocation/send rollback and request ownership; reject unknown keys/high-bit aliases',
          'Independent bounded runtime:9 replies consumed,connections14,queries28,pin_serial42,allrefs0; then re-evaluate subsequent requests/menu']},
      'unproven':['Exact second change_mode24B input and fields other than option6; option6 branch is bound by actual x4 and original no-clobber dataflow',
        'Only first newGET captured; remaining8 packets are conditional,not existing AP81 events','Expanded graph/native replies or later resource producers not implemented/validated here',
        'Original CP current states,hardware imaging/RAW/YC/SYSND/DMA and downstream consumption','Nonuniform/menu frame,format/scanout/TP and input-to-newframe acceptance']}
    (OUT/'ap81-pin-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    print(f'PASS: {len(ANCHORS)} instruction anchors; two100-row RAM/static matches; six CP objects;28 keys/14 edges; nine conditional packets; AP81 healthy240s/nativeboot/black first clear; no guest execution')


if __name__=='__main__':main()
