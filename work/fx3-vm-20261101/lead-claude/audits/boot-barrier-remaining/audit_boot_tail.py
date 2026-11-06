#!/usr/bin/env python3
"""Read-only post-barrier audit; writes only adjacent boot-tail-proof.json.

Reference evidence is frozen AP80b2. Default follow-up is AP80c; --run NAME
evaluates another existing completed run without guest/live-memory access.
Use the project's existing Capstone venv with -B to avoid bytecode writes.
"""
import argparse
import hashlib
import io
import json
import plistlib
import re
import struct
import subprocess
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from audit_boot_barrier import ROOT, OUT, RUNTIME, DATA, PINNED, read, dis, identity, gate_serial

REFERENCE = 'ap80b2digital-bd9672cf'
FOLLOWUP = 'ap80cpanel-5dd371e5'
EXPECTED_OUT = ROOT/'work/fx3-vm-20261101/lead-claude/audits/boot-barrier-remaining'
AP_BLOCKS = [(0x2b680a8,0x140),(0x2b63718,0x1a0),(0x2b5fc68,0x98),
 (0x2b634dc,0x60),(0x2b63c0c,0x20),(0x2b68330,0x64),(0x2aa1648,0x6c),
 (0x2aa222c,0x2ec),(0x285e3fc,0x4c),(0x2c20d10,0x18),
 (0x2dec0dc,0x30),(0x2de72d8,0x48),(0x2dcb9bc,0x18)]
CP_BLOCKS = [(0x607514,0x38),(0x1e54fc,0x3c),(0x607628,0x2e),
 (0x1aecb0,0x5a),(0x6073b8,0x74)]
ANCHORS = [
 ('ap',0x2b680c0,'bl #0x2b63224'),('ap',0x2b680c4,'mov w24, w0'),
 ('ap',0x2b681dc,'mov w1, w24'),('ap',0x2b681e4,'bl #0x2b63718'),
 ('ap',0x2b681e8,'b #0x2b63c0c'),('ap',0x2b63740,'mov w26, w1'),
 ('ap',0x2b63798,'bl #0x1592d30'),('ap',0x2b637a4,'ldr w0, [x0]'),
 ('ap',0x2b637a8,'str w0, [x29, #0x5c]'),('ap',0x2b637c8,'cmp w0, #2, lsl #12'),
 ('ap',0x2b637d0,'mov w0, #1'),('ap',0x2b637ec,'cmp w0, w26'),
 ('ap',0x2b6380c,'bl #0x2b634a8'),('ap',0x2b63828,'mov w0, #0'),
 ('ap',0x2b6382c,'b #0x2b637d4'),('ap',0x2b5fca4,'ldr w0, [x21, #0x304]'),
 ('ap',0x2b5fcb4,'bl #0x2dd0894'),('ap',0x2b5fcbc,'cbnz w0, #0x2b5fce8'),
 ('ap',0x2b5fcfc,'b #0x2b5fcd4'),('ap',0x2b5fce4,'ret '),
 ('ap',0x2dcb9bc,'blr x1'),('ap',0x2dcb9cc,'blr x1'),
 ('ap',0x2b6350c,'bl #0x2b634a8'),('ap',0x2b63528,'bl #0x1593f80'),
 ('ap',0x2c20d20,'str x0, [x19, #0x1b8]'),('ap',0x285e42c,'bl #0x2aa222c'),
 ('ap',0x2aa23a4,'bl #0x1592d30'),('ap',0x2aa2464,'bl #0x1592d30'),
 ('ap',0x2aa229c,'strb wzr, [x0]'),('ap',0x2b68370,'bl #0x2b638b8'),
 ('ap',0x2b68388,'ldr x0, [x19, #0x1b8]'),('ap',0x2b6838c,'bl #0x2aa1668'),
 ('ap',0x2aa168c,'strb w0, [x20]'),('ap',0x2aa16a4,'add x0, x20, #8'),
 ('ap',0x2aa16b0,'b #0x1593f80'),('cp',0x1aecb0,'cmp.w r6, #0x590000'),
]


def numeric_records(lines, marker):
    rows=[]
    for i,s in enumerate(lines,1):
        if marker not in s:continue
        row={'line':i,'text':s.decode(errors='replace').rstrip('\r')}
        for k,v in re.findall(rb'(\w+)=([^\s]+)',s):
            m=re.match(rb'(?:0x[0-9a-f]+|[0-9]+)',v)
            if m:row[k.decode()]=int(m[0],0)
        rows.append(row)
    return rows


def read_saved_run(name):
    assert re.fullmatch(r'[A-Za-z0-9_-]+',name),name
    folder=RUNTIME/'runs'/name; serial=folder/'serial.log'
    receipt_path=folder/'receipt.json';receipt=json.loads(receipt_path.read_bytes())
    assert receipt['process_reaped'] and receipt['inputs_unchanged'],name
    lines=serial.read_bytes().split(b'\n');g=gate_serial(serial)
    def hits(needle):
        return [{'line':i+1,'text':s.decode(errors='replace').rstrip('\r')} for i,s in enumerate(lines) if needle in s]
    snapshots=[]
    for i,s in enumerate(lines):
        m=re.fullmatch(rb'FX3_TASK_SNAPSHOT_(289|324|327)_BEGIN\r?',s)
        if not m:continue
        end=next(j for j in range(i+1,len(lines)) if b'FX3_TASK_SNAPSHOT_'+m[1]+b'_END' in lines[j])
        rows=[{'line':j+1,'text':lines[j].decode(errors='replace').rstrip('\r')} for j in range(i+1,end)
          if lines[j].startswith((b'Name:',b'State:',b'98 ',b'29 ')) or b'osal_rcv_msg_tmo' in lines[j]]
        snapshots.append({'tid':int(m[1]),'begin_line':i+1,'rows':rows})
    links=numeric_records(lines,b'FX3_BOOT_EVENT_LINK ')
    cvwait=numeric_records(lines,b'FX3_BOOT_CV_WAIT ')
    cvreturn=numeric_records(lines,b'FX3_BOOT_CV_RETURN ')
    enum=numeric_records(lines,b'FX3_PANEL_REVERSE_ENUM ')
    assert len(enum)==1 and enum[0]['enum']==2
    seq=enum[0]['sequence'];panel_tid=enum[0]['tid']
    bound=[x for x in links if x['id']==33 and x['sequence']==seq]
    waiting=[x for x in links if x['id']==32 and x['sequence']==seq]
    assert len(bound)==len(waiting)==1
    event=bound[0]['event'];cv=bound[0]['cv']
    assert cv==event+8 and waiting[0]['event']==event and waiting[0]['cv']==cv
    assert waiting[0]['future_cv']==cv
    handler=[x for x in links if x['id']==39 and x['event']==event and x['tid']==waiting[0]['tid']]
    lifetime_end=min((x['line'] for x in handler),default=len(lines)+1)
    after_lifetime=[x for x in links if x['line']>lifetime_end and x.get('event')==event]
    active_links=[x for x in links if x['line']<=lifetime_end]
    req=hits(b'raw=0d2019011c0001800101000000000000000000000000000000000000')
    assert req
    # Stages are explicit receipt predicates; absence remains UNPROVEN.
    applied=numeric_records(lines,b'FX3_PANEL_CONSUMER_APPLIED ')
    committed=numeric_records(lines,b'FX3_PANEL_CONFIG_COMMIT ')
    consumed=numeric_records(lines,b'FX3_PANEL_CONFIG_CONSUMED ')
    verified_commits=[]
    for c in committed:
        a=[x for x in applied if x['generation']==c['generation'] and x['transaction']==c['transaction']]
        z=[x for x in consumed if x['generation']==c['generation'] and x['transaction']==c['transaction']]
        if len(a)==len(z)==1 and a[0]['panel_control']==3 and a[0]['osd_rev']==0 and z[0]['result']==0 and a[0]['source']==c['source']:
            verified_commits.append({'applied_line':a[0]['line'],'commit_line':c['line'],'consumed_line':z[0]['line'],
              'generation':c['generation'],'transaction':c['transaction']})
    es=g['events'];await_entry=[e for e in es if e['pc']==0x2b63718 and e['x0']==seq]
    await_returns=[e for e in es if e['pc']==0x2b637d4 and e['x19']==seq]
    matched=[]
    for ent in await_entry:
        handle=ent['x1']&0xffffffff
        if handle in [0x1000,0x2000]:continue
        for ret in await_returns:
            if ret['line']<=ent['line'] or ret['x0'] or ret['token_or_req']!=handle or (ret['expected'][1]&0xffffffff)!=handle:continue
            completions=[e for e in es if e['pc']==0x2b634dc and e['x0']==seq and e['x1']==handle
              and e['tid']==panel_tid and enum[0]['line']<e['line']<ret['line']]
            if len(completions)==1:
                matched.append({'handle':handle,'LE32':struct.pack('<I',handle).hex(),'await_entry_line':ent['line'],
                  'completion_line':completions[0]['line'],'await_return_line':ret['line'],'status_w0':0})
    notify=[x for x in active_links if x['id']==36 and x['event']==event and x['caller']==0x2b68390]
    cvnotify=[x for x in active_links if x['id']==37 and x['cv']==cv and x['byte_done']==1]
    resumed=[x for x in cvreturn if x['line']<=lifetime_end and x['event']==event and x['cv']==cv and x['byte_done']==1]
    stages={'0119_packet_observed':True,'software_panel_applied_reply_consumed':bool(verified_commits),
      'panel_natural_completion_single_handle_match_return0':bool(matched),
      'boot_notifies_same_event_and_cv':bool(notify and cvnotify),
      'event_wait_returns_with_done1':bool(resumed),'outer_handler_continues':bool(handler),
      'menu_verified':bool(receipt.get('menu_verified'))}
    # No scalar 'boot success' inferred from notification: early returns and
    # a genuine 0119 error can also notify. Show the separate predicates.
    faults=hits(b'Unhandled fault:');faults+=hits(b'Entering exception monitor.')
    cpio_path=folder/'cpio-audit.json';cpio=json.loads(cpio_path.read_bytes())
    installed=[m for m in cpio['members'] if m['path'] in ['simulation/fx3-capid-v1.so','simulation/fx3-ui-gate-v1.so']]
    return {**identity(serial),'receipt':{**identity(receipt_path),**{k:receipt.get(k) for k in ['created_utc','candidate_sha256','qemu_exit','duration_seconds','host_observer_error','classification','guest_exception_markers','menu_verified']}},
      'sequence':hex(seq),'event':hex(event),'cv':hex(cv),'panel_tid':panel_tid,
      'boot_links':links,'cv_wait':cvwait,'cv_return':cvreturn,'enum':enum,'0119_requests':req,
      'applied':applied,'committed':committed,'consumed':consumed,'verified_commits':verified_commits,
      'single_await_entries':await_entry,'single_await_returns':await_returns,'matched':matched,
      'snapshots':snapshots,'stages':stages,'gate_events':es,'helper_bound':hits(b'FX3_UI_GATE_BOUND '),
      'helper_CPIO_audit':identity(cpio_path),'installed_helpers':installed,
      'faults':faults,'guest_health_verdict':'FAILED_GUEST_EXCEPTION' if faults else 'NO_EXCEPTION_MARKER_OBSERVED',
      'event_lifetime_end_line':lifetime_end if handler else None,'ignored_after_event_lifetime':after_lifetime,
      'lifetime_rule':'Only first matching boot event lifecycle through285e430; later same-address/TID samples cannot be attributed to that boot future.'}


def reference_ram(run):
    folder=RUNTIME/'runs'/REFERENCE;p=folder/'ui-gate-counters.bin';b=p.read_bytes()
    receipt=json.loads((folder/'receipt.json').read_bytes())
    saved=next(x for x in receipt['read_only_guest_memory_snapshots'] if x['name']==p.name)
    assert hashlib.sha256(b).hexdigest()==saved['sha256']=='79bc0aa68127b9b28360d36d021b37859a097f8f2ae44181a7404d0a09af3e0b'
    h=struct.unpack_from('<16Q',b)
    assert len(b)==65536 and h[0]==0x3145544147335846 and h[1]==2 and h[5]==45 and h[6]==0
    fields='id n tid pc x0 x1 x2 x3 x4 x19 x20 x21 remaining w25 w26 w27 w28 fp token_or_req create_sequence create_function completion_sequence completion_handle sentinel'.split()
    records=[]
    for i in range(h[5]):
        r=dict(zip(fields,struct.unpack_from('<24Q',b,0x4000+192*i)))
        assert r['sentinel']==0x544f4f4245544147
        rows=[x for x in run['gate_events'] if (x['id'],x['n'],x['tid'])==(r['id'],r['n'],r['tid'])]
        assert len(rows)==1;e=rows[0]
        for k in ['pc','x0','x1','x2','x3','x4','x19','remaining','token_or_req','create_sequence','create_function','completion_sequence','completion_handle']:
            assert r[k]==e[k],(i,k)
        assert [r['w'+str(j)] for j in range(25,29)]==e['expected']
        r.update(index=i,file_offset=hex(0x4000+192*i),serial_line=e['line']);records.append(r)
    assert len(records)==len(run['gate_events'])
    assert next(x for x in records if x['id']==33)['token_or_req']==int(run['event'],16)
    assert next(x for x in records if x['id']==32)['token_or_req']==int(run['event'],16)
    seq=int(run['sequence'],16);event=int(run['event'],16)
    fit=[]
    for s in run['snapshots']:
        if s['tid'] not in [289,327]:continue
        for r in s['rows']:
            if not r['text'].startswith('98 '):continue
            args=r['text'].split();futex=int(args[1],0)
            target=event+0x30 if s['tid']==289 else seq+0x150
            assert futex==target and int(args[2],0)==0x80
            fit.append({'tid':s['tid'],'line':r['line'],'actual_futex':hex(futex),
              'fit':'event+8+0x28' if s['tid']==289 else 'sequence+0x128+0x28','expected_futex':hex(target)})
    assert len(fit)==6
    assert run['cv_wait'][0]['caller']==0x2aa23a8 and run['cv_wait'][0]['cv']==event+8
    assert not run['cv_return'] and not any(x['id'] in [35,36,37,38,39,41] for x in run['boot_links'])
    return {**identity(p),'physical':hex(saved['address']),'published':h[5],'overflow':h[6],
      'records':records,'futex_address_fits':fit,
      'grade':'RAM/serial producer cross-check and observed CV caller A; futex-address-to-single-await-PC attribution B, no new user stack or live memory read'}


def reviewed_helper_sources():
    pins={'fx3-capid-v36.c':'4637705441ed07d50262a73faaab9032df317f02cc5e9a3bd8fa9d6c5c281e0c',
      'fx3-capid-v36.so':'1c8f5d9daefbc1be0a10ad54ca142ba23d8877744a6bd039e7e0e2e2623df9f3',
      'fx3-panel-config-core-v1.c':'5963010afb80fa35f9b32f56d11ab481e76edb7416925e1ddc41df26569ea55c',
      'check-panel-config-transport.c':'7807c6cbb6c54cda37b7659a12b160e5729daac44ec152668e7757b4c93907ba',
      'fx3-ui-gate-v7.c':'bf9e195ca73f47a1ca720014f08f46ac0a3b206191d4c4527ee2c8493cb61544',
      'fx3-ui-gate-v7.so':'0882e09abea36774b384298a2173a33d4527307e3a0ba70d41af2e88a11e8880'}
    out={k:identity(RUNTIME/'helpers'/k) for k in pins}
    for k,h in pins.items():assert out[k]['sha256']==h,k
    source=(RUNTIME/'helpers/fx3-capid-v36.c').read_text()
    positions=[source.index(x,source.index('static int panel_config_dispatch')) for x in
      ['vp_enqueue(&virtual_panel','vp_consume(&virtual_panel','vp_readback(&virtual_panel','allocate(from,&reply,12,1)',
       'FX3_PANEL_CONSUMER_APPLIED','rc=send_msg(from,reply)','FX3_PANEL_CONFIG_COMMIT']]
    assert positions==sorted(positions)
    host_path=RUNTIME/'helpers/panel-config-host-check.json';host=json.loads(host_path.read_bytes())
    assert host['exit']==0 and host['source_sha256']==pins['check-panel-config-transport.c']
    build_path=RUNTIME/'helpers/fx3-capid-v36-build.json';build=json.loads(build_path.read_bytes())
    assert build['exit']==0 and build['source_sha256']==pins['fx3-capid-v36.c'] and build['output_sha256']==pins['fx3-capid-v36.so']
    cpio=json.loads((RUNTIME/'runs'/REFERENCE/'cpio-audit.json').read_bytes())
    member=next(x for x in cpio['members'] if x['path']=='simulation/fx3-ui-gate-v1.so')
    assert member['sha256']==pins['fx3-ui-gate-v7.so']
    gate=(RUNTIME/'helpers/fx3-ui-gate-v7.c').read_text()
    assert 'fx3_observed_reverse_context' not in gate and 'fx3_observed_reverse_enum' in gate
    versions={}
    for version in [7,9]:
        p=RUNTIME/'helpers'/f'fx3-ui-gate-v{version}.c';text=p.read_text()
        m=re.search(r'offsets\[(\d+)\]=\{([^}]+)',text);n=int(m[1])
        offsets=[int(x,0) for x in m[2].split(',')]
        words=[int(x,0) for x in re.search(r'words\[\d+\]=\{([^}]+)',text)[1].split(',')]
        assert len(offsets)==len(words)==n
        for va,word in zip(offsets,words):assert struct.unpack('<I',read('ap',va,4))[0]==word
        versions[str(version)]={**identity(p),'binary':identity(p.with_suffix('.so')),
          'context_export_present':'fx3_observed_reverse_context' in text,
          'pins':[{'id':i,'VA':hex(va),'word':hex(word)} for i,(va,word) in enumerate(zip(offsets,words))]}
    assert versions['9']['context_export_present'] and len(versions['9']['pins'])==48
    assert versions['9']['sha256']=='73d6bda5b7c870e5512cda693929ea39426294c65a764022423df3929ffa091e'
    assert versions['9']['binary']['sha256']=='6453fe24de31fdaa47b0f5bbc55f5c6fd324b1f88c1192c534f4d903eee617f9'
    for version in [7,9]:
        e=ELFFile(io.BytesIO((RUNTIME/'helpers'/f'fx3-ui-gate-v{version}.so').read_bytes()))
        names={s.name for s in e.get_section_by_name('.dynsym').iter_symbols() if s['st_value']}
        assert ('fx3_observed_reverse_context' in names)==(version==9)
    return {'inputs':out,'gate_versions':versions,'build_receipt':{**identity(build_path),'exit':build['exit']},
      'existing_host_fixture':{**identity(host_path),'exit':host['exit'],'stdout':host['stdout'],
        'scope':'Existing host stub result, not rerun by this audit, not native guest transport/display/TP acceptance'},
      'source_order':'exact28B+enum/tid/sequence context -> enqueue -> consume -> readback -> allocation -> APPLIED log -> send -> COMMIT; send failure restores virtual state',
      'pairing':'capidv36 requires fx3_observed_reverse_context. v7 lacks it and would reject; v9 exports it and adds single-await entry/return probes.',
      'TP':'tp_axes_reversed is software metadata only; no libObj setter called by panel consumer; native TP consumption remains separate'}


def post_boot_abort():
    """Bind recorded fault PC/map only; packed on-disk bytes are not guest code."""
    folder=RUNTIME/'runs'/FOLLOWUP;lines=(folder/'serial.log').read_bytes().split(b'\n')
    wanted=[b'Unhandled fault:',b' pc:',b'program: im.elf(SeqQueueNetwork)',
      b'7fb79b8000-7fb79b9000',b'7fb6021000-7fb628b000',b'FX3_MMAP_PASS seq=27 ']
    rows=[{'line':i+1,'text':s.decode(errors='replace').rstrip('\r')} for i,s in enumerate(lines) if any(x in s for x in wanted)]
    assert any('7fb6084fc0' in r['text'] for r in rows)
    assert any('7fb79b88eb' in r['text'] for r in rows)
    assert any('7fb79b8000-7fb79b9000' in r['text'] and 'ffffb000' in r['text'] for r in rows)
    pc,base,fault,mapbase,physical=0x7fb6084fc0,0x7fb6021000,0x7fb79b88eb,0x7fb79b8000,0xffffb000
    assert pc-base==0x63fc0 and physical+fault-mapbase==0xffffb8eb
    p=RUNTIME.parent/'original-uipc/ap-projection/regular-files/usr/lib/libInfraSKD.so';b=p.read_bytes()
    assert hashlib.sha256(b).hexdigest()=='7d1fbd9a53794def916ca3ff2fc3a00f295268bb0f4ea7c07d0e8356d2840f9b'
    e=ELFFile(io.BytesIO(b));va=0x63fc0
    seg=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va< s['p_vaddr']+s['p_filesz'])
    off=seg['p_offset']+va-seg['p_vaddr'];raw=b[off:off+24]
    decoded=[{'VA':hex(i.address),'instruction':i.mnemonic+' '+i.op_str} for i in Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(raw,va)]
    assert not decoded
    return {'run':FOLLOWUP,'serial_rows':rows,'SKD_original':identity(p),'PC':hex(pc),'module_base_from_maps':hex(base),
      'module_VA':hex(pc-base),'fault_VA':hex(fault),'dev_mem_mapped_VA':hex(mapbase),'dev_mem_physical_offset':hex(physical),
      'physical_access_inferred':hex(physical+fault-mapbase),'original_file_bytes_at_VA':raw.hex(),
      'original_direct_disassembly':decoded,
      'boundary':'No original instruction claim from undecodable on-disk bytes. Need loaded/decrypted code evidence to identify exact load instruction/device meaning. Not attributed to observer or panel reply.'}


def pthread_futex_evidence():
    p=RUNTIME.parent/'original-uipc/ap-projection/regular-files/lib/libpthread-2.25.so';b=p.read_bytes()
    assert hashlib.sha256(b).hexdigest()=='7394f861930c45dd5076a700da5755faf0f6bed08544b0d60eadb85a14a7d592'
    e=ELFFile(io.BytesIO(b));blocks={}
    for va,n in [(0xd50c,0x10),(0xd548,0x14),(0xd5ec,8)]:
        seg=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz'])
        off=seg['p_offset']+va-seg['p_vaddr'];raw=b[off:off+n]
        blocks[hex(va)]=[{'VA':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(raw,va)]
    assert blocks['0xd5ec'][0]['instruction']=='svc #0'
    return {**identity(p),'blocks':blocks,'scope':'Original pthread event futex group word:cv+0x28+4*g; captured first-group addresses match. Futex word is not a mutex owner TID.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',default=FOLLOWUP);args=parser.parse_args()
    assert OUT==EXPECTED_OUT
    assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    for k in ['ap','cp']:assert hashlib.sha256(DATA[k]).hexdigest()==PINNED[k]
    for k,va,want in ANCHORS:
        assert dis(k,va,4)[0]['instruction']==want,(k,hex(va),dis(k,va,4)[0],want)
    assert struct.unpack('<Q',read('ap',0x47c5b68,8))[0]==0x2b5fc68
    run_i_signature=read('ap',0x391a718,80).split(b'\0')[0].decode()
    assert run_i_signature=='void model::sequence_boot::run_i()'
    ref=read_saved_run(REFERENCE);ram=reference_ram(ref);helpers=reviewed_helper_sources()
    proof={'scope':'Only this directory writes; original images, runtime/STATE and saved runs read-only; no QEMU/guest/live-memory/device actions',
      'original_sources':{k:{'sha256':PINNED[k],'bytes':len(DATA[k])} for k in ['ap','cp']},
      'original_blocks':{'ap':{hex(v):dis('ap',v,n) for v,n in AP_BLOCKS},'cp':{hex(v):dis('cp',v,n) for v,n in CP_BLOCKS}},
      'instruction_anchors':[{'image':k,'VA':hex(va),'instruction':s,'bytes':dis(k,va,4)[0]['bytes']} for k,va,s in ANCHORS],
      'panel_task_binding':{'GOT':'0x47c5b68','entry':'0x2b5fc68','dispatch':'0x2b680c0',
        'handle_saved':'0x2b680c4 w24=w0','await_argument':'0x2b681dc w1=w24','await_call':'0x2b681e4 ->0x2b63718',
        'warning':'completion_handle at id45 is stale TLS from the previous job, not evidence of this new panel handle'},
      'single_await_contract':{'queue':'same sequence+a8 std::deque<u32>, mutex+f8, cv+128; exact record LE32(actual_handle)',
        'entry':'x0sequence,w1expected; copied to x19,w26',
        'matching':'pop4B into[FP+5c],2000 returns1; otherwise cmp w0,w26; exact match recycles to free deque+28 and returns0',
        'return_probe':'2b637d4 before restoring callee-saved: w0status,x19sequence,w26expected,[FP+5c]token; common finalret2b637e8 loses these registers',
        'important':'parent2b681e8 ignores w0 then returns; notify may follow2000 or genuine panel failure. Neither notify nor job completion alone proves successful orientation.'},
      'event_contract':{'layout':'event+0 donebyte,event+4 result,event+8 condition_variable; future={event,event+4,event+8}; sequence+1b8 stores event',
        'run_i_original_signature':{'VA':'0x391a718','value':run_i_signature},
        'return_type':'run_i is void; x0=0 at2b68374 is captured residue, not a defined business success code',
        'signal':'2b68388 loads sequence+1b8;2b6838c->2aa1668 writes done1 under globalmutex then notifies event+8',
        'wait':'AP80b2 actualcaller2aa23a8 is cooperative eventwait; later thread-scheduling cv may be waited at2aa2464, then common2aa2298 resets donebyte',
        'observations':['2b63718 expected','2b637d4 result/token','2b68374 sequence/event','2aa1668 event/caller','2aa16ac cv/done','condition wait wrapper return event/done','285e430 handler continuation']},
      'reference_run':ref,'reference_saved_RAM':ram,'reviewed_helpers':helpers,
      'unproven':['AP80b2 panel actual new dispatch handle and matching remain unknown for that historical run; AP80c separately proveshandle4',
        'Post-boot libInfraSKD exception root cause/resolution,healthy240s run,subsequent UI dequeue/draw',
        'Native libObj TP-direction consumption and raw input calibration','Final scanout/plane composition/physical panel basis/menu visuals and input']}
    proof['AP80c_post_boot_abort']=post_boot_abort()
    proof['original_pthread_futex']=pthread_futex_evidence()
    proof['additional_saved_run']=read_saved_run(args.run)
    if args.run==FOLLOWUP:
        current=proof['additional_saved_run']
        assert all(v for k,v in current['stages'].items() if k!='menu_verified') and not current['stages']['menu_verified']
        assert current['guest_health_verdict']=='FAILED_GUEST_EXCEPTION' and current['matched'][0]['handle']==4
        expected_helpers={'simulation/fx3-capid-v1.so':helpers['inputs']['fx3-capid-v36.so']['sha256'],
          'simulation/fx3-ui-gate-v1.so':helpers['gate_versions']['9']['binary']['sha256']}
        assert all(m['sha256']==expected_helpers[m['path']] for m in current['installed_helpers']) and len(current['installed_helpers'])==2
    (OUT/'boot-tail-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    print(f'PASS: {len(ANCHORS)} original anchors, panel GOT/handle flow,46+48 gate pins; AP80b2 all45 saved RAM records equal serial,actual cooperativeeventwait and6 futex fits; no guest execution')
    print(json.dumps({'stages':proof['additional_saved_run']['stages'],'guest':proof['additional_saved_run']['guest_health_verdict']},sort_keys=True))


if __name__=='__main__':main()
