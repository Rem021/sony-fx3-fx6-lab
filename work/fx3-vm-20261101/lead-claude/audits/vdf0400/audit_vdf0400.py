#!/usr/bin/env python3
"""Rebuild SYS 0400 evidence from original bytes; no guest/original-code execution.

Only this directory's vdf0400-proof.json is written. Historical name vdf0400 is
kept for the dispatch; the original path is SYS/TCUB, not a VDF command class.
"""
from pathlib import Path
import hashlib, json, struct, sys, re, subprocess, plistlib
from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile
sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if p.name == 'Mac' and (p/'README.md').is_file())
TASK = ROOT/'work/fx3-vm-20261101'
AP = TASK/'menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so'
CP = ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
LOG = TASK/'menu-repair-01/runtime/runs/ap85r4osdring-5dcb8371/serial.log'
A, B = AP.read_bytes(), CP.read_bytes()
with AP.open('rb') as f:
    elf = ELFFile(f)
    loads = [(s['p_vaddr'],s['p_offset'],s['p_filesz']) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
    plt = elf.get_section_by_name('.plt')['sh_addr']
    rela = elf.get_section_by_name('.rela.plt'); syms = elf.get_section(rela['sh_link'])
    imports = {plt+32+16*i:syms.get_symbol(r['r_info_sym']).name for i,r in enumerate(rela.iter_relocations())}
def offset(v): return next(o+v-x for x,o,n in loads if x <= v < x+n)
def raw(k,v,n):
    d,o = (A,offset(v)) if k == 'AP' else (B,v-0x108000)
    return d[o:o+n]
def dis(k,v,n):
    cs = Cs(CS_ARCH_ARM64,0) if k=='AP' else Cs(CS_ARCH_ARM,CS_MODE_THUMB)
    cs.skipdata = True
    return [{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in cs.disasm(raw(k,v,n),v)]
def cstr(k,v):
    d,o = (A,offset(v)) if k=='AP' else (B,v-0x108000)
    return d[o:d.index(b'\0',o)].decode(errors='replace')
def u32(v): return struct.unpack('<I',raw('CP',v,4))[0]
REQ = bytes.fromhex('0d2000040a0001800000')
REP = bytes.fromhex('0d2000140c00018000000000')
AP_BLOCKS = [(0x2dcadd0,0x190),(0x2dd1f14,0x40),(0x2df264c,0x124),
 (0x2de7070,0x38),(0x2de70a8,0x2a0),(0x2de4574,0x2a0),(0x2ebf3b0,0x9c),
 (0x2bd763c,0x180),(0x2bd1ecc,0x160)]
CP_BLOCKS = [(0x1a69da,0x20),(0x1a6bb2,0x16),(0x1a6c1e,4),(0x1a6cf4,0x2a),
 (0x1a6dbe,0xc),(0x5c7ff4,0x30),(0x1a8078,0x40),(0x5ce2f8,0xe),
 (0x1ac9c8,0x40),(0x1acb92,0xc),(0x1acbf0,4),(0x1ad050,0x26),
 (0x1a8e88,0x12),(0x1a8ed4,0x42),(0x1aa70c,0xc),
 (0x1a9a3c,0x12),(0x1a9fcc,0xa),(0x5cada6,0x16),
 (0x1b9090,0x1e),(0x1b90de,0x34),(0x1b944a,8),(0x5c68de,0x12),
 (0x1ad1a4,0x26),(0x1ad21c,6),(0x1ad6b6,0x26),
 (0x1aaa34,0x3a),(0x1aab1e,0x12),(0x1ab192,0xe),(0x1adf2c,0x64),
 (0x1aef1c,0xae),(0x1b95c0,0x40),(0x1b995a,0x52),(0x1ba49e,0x2a),
 (0x1ab68c,0x1a),(0x1ab878,0x1a), # VDF secondary dispatch is NOT this path
 (0x5f80e2,0x90),(0x1ad6fc,0x40),(0x1ad912,0xe),(0x1ac64c,0xc),(0x5c95b4,0x52)]
CHECKS = [
 ('AP',0x2dcae28,'ldr w0, [x21, #0x1bc]'),('AP',0x2dcae38,'bl #0x2dd1f14'),
 ('AP',0x2dcae40,'cbnz w0, #0x2dcae84'),('AP',0x2dcae80,'ret '),
 ('AP',0x2dcaf54,'bl #0x1592ec0'),('AP',0x2dcaf58,'bl #0x2ebf3b0'),
 ('AP',0x2dd1f3c,'bl #0x2df264c'),('AP',0x2df2670,'mov w1, #0x400'),
 ('AP',0x2df2674,'strh wzr, [x29, #0x48]'),('AP',0x2df268c,'cbz w0, #0x2df269c'),
 ('AP',0x2df2690,'cmp w0, #1'),('AP',0x2df2698,'strb w0, [x29, #0x48]'),
 ('AP',0x2df26a8,'mov w4, #0xc'),('AP',0x2df26ac,'mov w2, #0xa'),
 ('AP',0x2df26bc,'bl #0x2de70a8'),('AP',0x2df26c4,'bl #0x2de4574'),
 ('AP',0x2de7260,'bl #0x1592f10'),('AP',0x2de72fc,'mov w2, #-1'),
 ('AP',0x2de7300,'bl #0x1592de0'),('AP',0x2de7314,'bl #0x1591c40'),
 ('AP',0x2de7320,'bl #0x15943d0'),('AP',0x2de45c4,'cbz w0, #0x2de46cc'),
 ('AP',0x2de46cc,'mov w19, #0'),('AP',0x2bd76f8,'blr x1'),
 ('AP',0x2bd7754,'bl #0x2bd1ecc'),('AP',0x2bd7788,'b #0x2bd763c'),
 ('CP',0x1a6c1e,'movs r5, #0'),('CP',0x1a6d0e,'movs r2, #1'),
 ('CP',0x1a6d18,'movs r3, #0'),('CP',0x1a6d1a,'bl #0x1ac9c8'),
 ('CP',0x1ac9de,'bl #0x5c7ff4'),('CP',0x1a807e,'ldrb r0, [r0, #8]'),
 ('CP',0x1a808e,'str.w r0, [r4, #0x42c]'),('CP',0x1a80a0,'bl #0x5ce2f8'),
 ('CP',0x1acbf0,'movs r0, #0x3e'),('CP',0x1a9a4a,'movs r1, #0'),
 ('CP',0x1a9fd0,'bl #0x5cada6'),('CP',0x5cadb2,'bl #0x1b9090'),
 ('CP',0x1b9106,'orr r1, r1, #1'),('CP',0x1b910c,'mov.w r0, #0x400'),
 ('CP',0x1b944a,'movs r1, #0'),('CP',0x1b944c,'bl #0x5c68de'),
 ('CP',0x5c68e8,'bl #0x1ad1a4'),('CP',0x1ad21c,'movw r0, #0x23f'),
 ('CP',0x1ab198,'bl #0x1adf2c'),('CP',0x1adf5c,'mov.w r0, #0x1400'),
 ('CP',0x1adf7e,'str r6, [sp, #0x14]'),('CP',0x1adf84,'bl #0x1aef1c'),
 ('CP',0x1b9972,'ldr.w r0, [r8, #0x42c]'),('CP',0x1b997a,'str r0, [r1]'),
 ('CP',0x5f80e8,'movw r0, #0x205'),('CP',0x5c95d2,'movw r0, #0x1138')]

def software_accept(packet,state,*,destination,source,lease,profile,allocate=True,send=True):
    """Proof-only transactional configuration acceptor; no transport/device writes."""
    if (packet != REQ or destination != 0x92840747 or not source or
        profile != 'headless_sys_timecode_mode' or not isinstance(lease,dict) or
        lease.get('owner') != 'this_request' or lease.get('source') != source or
        lease.get('request') != packet.hex() or lease.get('generation') != 1 or
        state.get('completed_generation') == lease.get('generation')):
        raise ValueError('outside frozen SYS0400 software contract')
    staged = {'mode':0,'reserved':0,'software_config_accepted':True,
              'pending_counter_backend':True,'physical_timecode_verified':False,
              'recording_or_live_view_started':False}
    if not allocate or not send:
        raise ValueError('allocation/send failed: discard stage, release owned reply')
    state.update(sys_timecode_mode=staged,completed_generation=1)
    return REP

def main():
    volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID'].upper() == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    assert hashlib.sha256(A).hexdigest() == '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
    assert hashlib.sha256(B).hexdigest() == 'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
    proof={'scope':'read-only original bytes/logs; no QEMU, CP execution or installed model',
           'classification':'SYS0400 / TCUB; NOT old VDF2001 command class',
           'volume_uuid':volume['VolumeUUID'],'sources':{},'code':{},'checks':[]}
    def source(p,data=None):
        if data is None: data=p.read_bytes()
        proof['sources'][str(p.relative_to(ROOT))]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        return data
    source(AP,A);source(CP,B)
    for k,blocks in [('AP',AP_BLOCKS),('CP',CP_BLOCKS)]:
        proof['code'][k]={hex(v):{'raw':raw(k,v,n).hex(),'length':n,'disassembly':dis(k,v,n),
          'note':'Bounded blocks; literal/TBB/table bytes and .byte rows are not executable-flow evidence'} for v,n in blocks}
    for k,v,want in CHECKS:
        ins=dis(k,v,4)[0];assert ins['instruction']==want,(k,hex(v),ins,want)
        proof['checks'].append({'binary':k,**ins})
    proof['tables']=[]
    for name,base,index,want in [
      ('receive category0400',0x1a6bc8,0,0x1a6c1e),
      ('wire0400 to internal3e',0x1acb9e,0,0x1acbf0),
      ('phase0 internal3e to TCUB',0x1a8f16,0x3e,0x1a9a3c),
      ('completion0400 to internal23f',0x1ad1ca,0,0x1ad21c),
      ('internal23f to reply1400',0x1aab30,0x23f-0x200,0x1ab192),
      ('VDF secondary internal3e is default',0x1ab6a6,0x3e-0x1f,0x1ab878),
      ('old VDF1400 instead maps to1138',0x1ac4ce,0x287-0x225,0x1ac64c)]:
        slot=base+2*index;half=struct.unpack('<H',raw('CP',slot,2))[0]
        assert base+half*2==want
        proof['tables'].append({'name':name,'base':hex(base),'slot':hex(slot),'half':hex(half),'target':hex(want)})
    assert raw('CP',0x1a6d00,1)==b'\x05' # category0 TBB target1a6d0a
    parsers=[(0xb71abc+i*8,*struct.unpack('<II',raw('CP',0xb71abc+i*8,8))) for i in range(0x77)]
    entry=next(x for x in parsers if x[1]==0x400);assert entry==(0xb71d24,0x400,0x1a8079)
    proof['parser_table']={'slot':hex(entry[0]),'command':hex(entry[1]),'function_thumb':hex(entry[2]),
        'desired_mode_storage':'0x19eafb8+0x42c =0x19eb3e4','dirty_flag':'0x1438dd5'}
    proof['old_VDF_RTTI_exclusion']={'reason':'actual dispatch enters TCUB procedural path, not1ab680 VDF dispatch',
        'similar_name':cstr('CP',0xb3dc70),'name_va':'0xb3dc70','typeinfo':'0xb7ea3c','vtable':'0xb7ea24',
        'slots':{hex(i):hex(u32(0xb7ea24+i)) for i in (0xc,0x10,0x14)},
        'actual_id':'2001/0205, different36B Dataflow timecode setup; not0400'}
    assert u32(0xb7ea24+0xc)==0x5f80e3
    proof['strings']={k:{hex(v):cstr(k,v) for v in vs} for k,vs in {
        'AP':[0x3960c90,0x3960c2b,0x3960c5e,0x3968a40,0x3934d30,0x3934d59],
        'CP':[0x1a80b8,0x1adf90,0x1ba648]}.items()}
    proof['imports']={hex(v):imports[v] for v in (0x1592f10,0x1592de0,0x1591c40,0x15943d0,0x1592ec0)}
    assert imports[0x1592de0]=='osal_rcv_msg_tmo'
    proof['sequence_calls']=[x for x in dis('AP',0x2dcadd0,0x190) if x['instruction'].startswith(('bl ','blr '))]
    assert [x['instruction'] for x in proof['sequence_calls']].count('bl #0x2dd1f14')==1
    proof['request']={'hex':REQ.hex(),'header_le16':list(struct.unpack('<4H',REQ[:8])),
        'mode_u8_at8':0,'reserved_u8_at9':0,'mode_domain_AP':[0,1],
        'CP_validation':'copies byte8 verbatim; no Cmd Validate/Execute object in this path',
        'mode_labels':'not proven; do not assume free-run/rec-run labels'}
    data=LOG.read_bytes()[:5426282]
    assert len(data)==5426282 and hashlib.sha256(data).hexdigest()=='c493986a68c7dc4d8f05e24167c9eee3808e99a2087a01d92f370921b7306d8e'
    source(LOG,data);lines=data.split(b'\n')
    rows=lambda lo,hi:[{'line':i+1,'text':lines[i].decode(errors='replace')} for i in range(lo-1,hi)]
    assert b'raw='+REQ.hex().encode() in lines[21806]
    frames=[]
    for i in range(21791,21805):
        mat=re.search(rb'FX3_PROFILE_FRAME depth=(\d+).*relative=(0x[0-9a-f]+)',lines[i])
        if mat:frames.append({'line':i+1,'depth':int(mat[1]),'relative':mat[2].decode()})
    assert [f['relative'] for f in frames[:6]]==['0x2de7264','0x2df26c0','0x2dd1f40','0x2dcae3c','0x2bd76fc','0x2f71ba0']
    assert b'osal_rcv_msg_tmo' in b'\n'.join(lines[52730:52814])
    assert b'FX3_PEAKING_COMMIT ' in lines[21708]
    assert b'FX3_PEAKING_CONSUMED ' in lines[21711]
    proof['runtime']={'frozen_prefix':True,'request_line':21807,'skip_line':21809,
        'context':rows(21792,21809),'frames':frames,'last_thread346_snapshot':rows(52731,52814),
        'prior0152':rows(21709,21716),'reply1400_marker_count':data.count(b'0d200014'),
        'absence_limit':'deduplicated bounded markers, not a lossless all-message proof',
        'queue_heap_tail_captured':False}
    proof['completion']={'reply_hex':REP.hex(),'length':12,'status_at8':0,
        'status_domain':'raw SYS callback status; no OR590000 or normalization',
        'ordering':'copy desired mode+dirty flag; TCUB pending bit; callback0400,status0; reply1400; hardware counter worker later',
        'AP_consumed_in_this_run':False}
    lease={'owner':'this_request','source':0x81cf61c2,'request':REQ.hex(),'generation':1}
    kw={'destination':0x92840747,'source':0x81cf61c2,'lease':lease,'profile':'headless_sys_timecode_mode'}
    state={};assert software_accept(REQ,state,**kw)==REP
    cases=[]
    for i in range(10):
        p=bytearray(REQ);p[i]^=1;cases.append((f'byte{i}_changed',bytes(p),{}))
    cases += [('short',REQ[:-1],{}),('long',REQ+b'\0',{}),
      ('wrong_destination',REQ,{'destination':0x92840748}),('missing_source',REQ,{'source':0}),
      ('source_lease_mismatch',REQ,{'source':0x81cf61c3}),('no_lease',REQ,{'lease':None}),
      ('wrong_profile',REQ,{'profile':'physical_camera'}),('allocation_failure',REQ,{'allocate':False}),
      ('send_failure',REQ,{'send':False})]
    rejects=[]
    for name,p,over in cases:
        temp={};before=json.dumps(temp,sort_keys=True)
        try:software_accept(p,temp,**(kw|over))
        except ValueError:assert json.dumps(temp,sort_keys=True)==before;rejects.append(name)
        else:raise AssertionError(name)
    before=json.dumps(state,sort_keys=True)
    try:software_accept(REQ,state,**kw)
    except ValueError:assert json.dumps(state,sort_keys=True)==before;rejects.append('same_generation_replay')
    else:raise AssertionError('replay')
    proof['software_contract']={'installed':False,'accepted_state':state,'reply':REP.hex(),'rejections':rejects,
      'adapter_obligations':['bind current source and unique original request lease; never hard-code6189/61c2',
       'stage desired mode0 and pending-counter state before allocating reply; commit only after send accepted',
       'own allocated reply until send transfers ownership; free own reply and discard stage on failure',
       'AP retains request lifecycle and naturally frees reply at2de7320; do not double-free original request',
       'do not emit TC ticks, recording/live-view/HDMI/GPE/OSD events, clear hardware pending, or manufacture queue completion']}
    proof['following_synchronous_requests']=[
      {'scope':'remaining body of THIS run after0400','requests':[],'complete':True,
       'evidence':'2dcae3c..e80 success log then return; full run call list preserved'},
      {'scope':'failure path','requests':[],'complete':False,
       'evidence':'diagnostic/error handler2ebf3b0 may notify external error handler; no normal success reply prescribed'},
      {'scope':'later SeqQueueCommon tasks and completion observers','complete':False,'reply_hex':None,
       'evidence':'2bd7754 completion;2bd7764 destructor;2bd7788 loops; next virtual run2bd76f8 requires uncaptured queue heap',
       'required_observation':'queue object x19 +10/+20/+88, next node/task/vtable and task input; completion observer list current_task+158/+160'}]
    proof['unproven']=['CP execution and actual TC-counter/hardware effects; mode0/1 user-facing names',
      'runtime reply1400 consumption and natural completion of this sequence',
      'later dynamic queue/observer tasks and their full synchronous contracts',
      'global OSAL correlation/cancel semantics beyond the captured lease',
      'menu pixels, key response, normal standby and any physical-camera acceptance']
    for rel in ['COMMON-CONTEXT.md','PLAN.md','audits/boot-vdf-tail/README.md','audits/vdf0152-peaking/README.md']:
        source(TASK/'lead-claude'/rel)
    target=OUT/'vdf0400-proof.json'
    target.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    print(f'PASS: {len(CHECKS)} instruction checks, 7 TBH mappings, parser/RTTI exclusion, AP85r4 stack+snapshot, {len(rejects)} rejections; {target.name} rebuilt')
if __name__=='__main__':
    if len(sys.argv)>1:
        for arg in sys.argv[1:]:
            k,v,n=arg.upper().split(':');v,n=int(v,16),int(n,16)
            print(k,hex(v));print('\n'.join(x['va']+': '+x['instruction'] for x in dis(k,v,n)))
    else:main()
