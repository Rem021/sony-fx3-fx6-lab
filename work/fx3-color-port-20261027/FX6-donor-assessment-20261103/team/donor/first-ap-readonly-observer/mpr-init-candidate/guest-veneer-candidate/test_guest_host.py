#!/usr/bin/env python3
"""Host-only tests of link_map parsing, exact thunk plan, and fail-closed Z1 gate."""
import hashlib
import json
import struct
import types
from pathlib import Path

import guest_probe as gp
from run_guest_once import quit_without_guest_resume

HERE=Path(__file__).resolve().parent
passes=[]

def check(name, fn):
    fn();passes.append(name)

def test_elf():
    assert gp.dynamic_debug_va()==0x418ec0
    s=gp.symbol_vas(gp.BRIDGE)
    assert len(s)==66 and len({s[f'fx6diag_slot_{i:02d}'] for i in range(57)})==57
    b=gp.BRIDGE.read_bytes()
    # ELF VA-to-file translation uses PT_LOAD rather than presumed VA=file offset.
    loads=gp.previous.elf_loads(gp.BRIDGE)
    for i in range(57):
        va=s[f'fx6diag_slot_{i:02d}']
        seg=[x for x in loads if x['va']<=va and va+4<=x['va']+x['filesz']]
        assert len(seg)==1
        off=seg[0]['fileoff']+va-seg[0]['va']
        assert b[off:off+4]==struct.pack('<I',0xd4200000|((0x600+i)<<5))
    for name,imm in [('fx6diag_mpr_enterrec',0x7f0),('fx6diag_failstop',0x7fe)]:
        va=s[name];seg=next(x for x in loads if x['va']<=va< x['va']+x['filesz'])
        off=seg['fileoff']+va-seg['va']
        assert b[off:off+4]==struct.pack('<I',0xd4200000|(imm<<5))

class Memory:
    def __init__(self):self.blobs=[]
    def put(self,addr,data):self.blobs.append((addr,data))
    def virtual_read(self,addr,size):
        for base,blob in self.blobs:
            if base<=addr and addr+size<=base+len(blob):return blob[addr-base:addr-base+size]
        raise ValueError('unmapped synthetic address')

def test_link_map():
    m=Memory();dynamic=bytearray(16);struct.pack_into('<QQ',dynamic,0,21,0x6000)
    m.put(0x418ec0,dynamic)
    m.put(0x6000,struct.pack('<I4xQ',1,0x7000))
    names=['/usr/bin/im.elf',gp.BRIDGE_PATH,'/usr/lib/libmpr.so']
    for i,name in enumerate(names):
        ptr=0x7000+i*0x100
        m.put(ptr,struct.pack('<5Q',0x100000+i*0x1000,0x8000+i*0x100,
                              0,ptr+0x100 if i<2 else 0,ptr-0x100 if i else 0))
        m.put(0x8000+i*0x100,name.encode()+b'\0'+b'\0'*16)
    rows=gp.read_link_map(m,0)
    assert len(rows)==3 and gp.one_module(rows,gp.BRIDGE_PATH)['bias']==0x101000
    bad=Memory();bad.blobs=m.blobs.copy();bad.blobs[1]=(0x6000,struct.pack('<I4xQ',2,0x7000))
    try:gp.read_link_map(bad,0)
    except ValueError:pass
    else:raise AssertionError('r_debug version accepted')
    try:gp.one_module(rows+rows[1:2],gp.BRIDGE_PATH)
    except ValueError:pass
    else:raise AssertionError('ambiguous module accepted')
    # A name ending at a page boundary must not require a read into the next page.
    edge=Memory();edge.put(0x418ec0,struct.pack('<QQ',21,0x6000))
    edge.put(0x6000,struct.pack('<I4xQ',1,0x7000))
    edge.put(0x7000,struct.pack('<5Q',0x101000,0x8ff0,0,0,0))
    edge.put(0x8ff0,b'page-edge-name\0\0')
    assert gp.read_link_map(edge,0)[0]['name']=='page-edge-name'

def fake_gate(fail_at=None):
    p=gp.Probe.__new__(gp.Probe)
    p.bridge_symbols=gp.symbol_vas(gp.BRIDGE)
    p.mapping={'ap':{'bias':0x10000000},'im':{'bias':0}}
    p.ap_call=0x10000000+gp.AP_CALL;p.ap_return=0x10000000+gp.AP_RETURN
    p.breakpoints={p.ap_call};p.records=[];p.stage='await_mpr_call'
    p.gate_installed=False;p.bridge_bias=None;p.mpr_bias=None
    p.hit_budget=8
    p.sysregs=types.SimpleNamespace(read=lambda name:0x123)
    p.rsp=object();p.resumes=0;p.adds=[]
    p.read=lambda addr,n: bytes.fromhex('429fa797') if addr==p.ap_call else b'\0'*n
    p.read_span=lambda addr,n:b'\0'*n
    p.identity=lambda origin,bias:{'origin':origin,'bias':bias}
    p._check_bridge=lambda bias,vas:{'bridge_test_identity':True}
    p._record=lambda *args,**kwargs:p.records.append({'kind':args[0]})
    p.save=lambda:None
    p.resume=lambda:setattr(p,'resumes',p.resumes+1)
    def add(addr):
        if fail_at is not None and len(p.adds)==fail_at:raise RuntimeError('synthetic Z1 reject')
        p.adds.append(addr);p.breakpoints.add(addr)
    p.add=add
    p.remove=lambda addr:p.breakpoints.remove(addr)
    regs=[0]*33;regs[0]=0x9000;regs[29]=0x8fe0;regs[32]=p.ap_call
    return p,regs

def test_z1_fail_closed():
    old_link=gp.read_link_map;old_id=gp.read_current_identity
    gp.read_link_map=lambda rsp,bias:[{'name':gp.BRIDGE_PATH,'bias':0x20000000},
                                      {'name':'/usr/lib/libmpr.so','bias':0x30000000}]
    gp.read_current_identity=lambda *args,**kwargs:{'identity_test':True}
    try:
        for at in (0,1,28,62):
            p,regs=fake_gate(at)
            try:p._arm_gate('T05thread:01;', '01',regs)
            except RuntimeError as e:assert 'Z1 reject' in str(e)
            else:raise AssertionError('Z1 failure resumed')
            assert p.resumes==0 and not p.gate_installed and p.ap_call in p.breakpoints
        p,regs=fake_gate()
        p._arm_gate('T05thread:01;','01',regs)
        assert p.gate_installed and p.resumes==1 and p.ap_call not in p.breakpoints
        assert len(p.adds)==63 and len(p.breakpoints)==63
        assert len({p.bridge_symbols[f'fx6diag_slot_{i:02d}'] for i in range(57)})==57
    finally:
        gp.read_link_map=old_link;gp.read_current_identity=old_id

def test_cross_vcpu_tls_and_frame():
    old_id=gp.read_current_identity
    gp.read_current_identity=lambda *args,**kwargs:{'identity_test':True}
    try:
        p,regs=fake_gate();p.bridge_bias=0x20000000;p.mpr_bias=0x30000000
        p.stage='await_sony_entry';p.gate_installed=True
        p.call_vcpu='01';p.call_tls=0x123;p.call_fp=0x8fe0
        regs[0]=p.bridge_bias+p.bridge_symbols['fx6diag_mapped_record']
        regs[30]=p.bridge_bias+p.bridge_symbols['fx6diag_call_original']+12
        regs[32]=p.mpr_bias+gp.previous.MPR_INIT
        p.breakpoints.add(regs[32]);p.resume=lambda:setattr(p,'resumes',p.resumes+1)
        p._stop_context=lambda stop:('02',regs) # same guest TLS, migrated vCPU
        p.process_stop('T05thread:02;',b'')
        assert p.stage=='await_return_or_stop' and p.records[-1]['kind']=='original_init_entry'
        assert p.resumes==1
        q,r=fake_gate();q.bridge_bias=p.bridge_bias;q.mpr_bias=p.mpr_bias
        q.stage='await_sony_entry';q.gate_installed=True;q.call_tls=0x123;q.call_fp=0x8fe0
        r[0]=q.bridge_bias+q.bridge_symbols['fx6diag_mapped_record']
        r[30]=q.bridge_bias+q.bridge_symbols['fx6diag_call_original']+12
        r[32]=q.mpr_bias+gp.previous.MPR_INIT
        q._stop_context=lambda stop:('02',r)
        q.sysregs=types.SimpleNamespace(read=lambda name:0x999)
        try:q.process_stop('T05thread:02;',b'')
        except ValueError as e:assert 'TLS' in str(e)
        else:raise AssertionError('wrong TLS accepted')
        q.sysregs=types.SimpleNamespace(read=lambda name:0x123)
        r[30]=0xdeadbeef
        try:q.process_stop('T05thread:02;',b'')
        except ValueError as e:assert 'return-chain' in str(e)
        else:raise AssertionError('wrong BLR return chain accepted')
        q.stage='await_return_or_stop';r[32]=q.ap_return;r[29]=0xdead
        try:q.process_stop('T05thread:02;',b'')
        except ValueError as e:assert 'frame' in str(e)
        else:raise AssertionError('wrong AP frame accepted')
    finally:gp.read_current_identity=old_id

def test_im_record_cross_vcpu():
    def setup(tls=0x123,record=0x7000):
        p=gp.Probe.__new__(gp.Probe)
        p.stage='await_ap_dlsym_return';p.im_dlsym_return=gp.previous.DLSYM_RETURN
        p.dispatch={'record':0x7000,'tid':'03','tls':'0x123'}
        p.mapping={'im':{'bias':0}};p.records=[];p.qmp_statuses=[]
        p.breakpoints={p.im_dlsym_return};p.resumes=0
        p.sysregs=types.SimpleNamespace(read=lambda name:tls)
        p.read=lambda addr,n:bytes.fromhex(gp.previous.WORDS[('im',gp.previous.DLSYM_RETURN)])
        p.identity=lambda origin,bias:{'origin':origin,'bias':bias}
        def record(*args,**kwargs):
            row={'kind':args[0],**(args[4] if len(args)>4 else {})}
            p.records.append(row)
            return row
        p._record=record
        p.save=lambda:None;p.add=lambda addr:p.breakpoints.add(addr)
        p.remove=lambda addr:p.breakpoints.remove(addr)
        p.resume=lambda:setattr(p,'resumes',p.resumes+1)
        regs=[0]*33;regs[0]=0x50000000+gp.previous.AP_ENTRY
        regs[22]=record;regs[32]=p.im_dlsym_return
        p._stop_context=lambda stop:('02',regs)
        return p
    p=setup()
    assert p.process_stop('T05thread:02;',b'') is False
    assert p.stage=='await_mpr_call' and p.resumes==1
    assert p.records[-1]['dispatch_vcpu']=='03'
    for kw in ({'tls':0x999},{'record':0x9999}):
        p=setup(**kw)
        assert p.process_stop('T05thread:02;',b'') is True
        assert p.stage=='unknown_loader_return' and p.resumes==0
        assert p.records[-1]['record_equal']==('record' not in kw)
        assert p.records[-1]['tls_equal']==('tls' not in kw)
        assert p.records[-1]['reject_reasons']==(['TLS_mismatch'] if 'tls' in kw else ['record_x22_mismatch'])

def test_no_resume_on_fault():
    import inspect
    source=inspect.getsource(__import__('run_guest_once').main)
    assert 'frozen.cleanup_owned(' not in source
    assert 'quit_without_guest_resume(qemu,qmp,cleanup,' in source
    for stop in ('unknown_callback_captured','enterrec_blocked','bridge_failstop',
                 'writer_threshold_before_record_gate','host_exception',
                 'observation_budget_end','ap_return_captured'):
        cleanup={}
        quit_without_guest_resume(None,None,cleanup,'test_'+stop)
        assert cleanup['API16_restored'] is False
        assert cleanup['API16_restore_skipped_to_preserve_fault_stop'] is True
        assert cleanup['reason']=='test_'+stop

def test_real_input_and_guest_output():
    raw=(HERE/'genuine-input.bin').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='585d8918da368cec6ef689aa3c14dc3306311ab6661c0bffc9a02e1685430cf1'
    assert int.from_bytes(raw[0x268:0x26c],'little')==2
    assert int.from_bytes(raw[0x28a:0x28c],'little')==1440
    assert (HERE/'guest-veneer.cpio').stat().st_size==453184500
    receipt=json.loads((HERE/'static-receipt.json').read_text())
    assert receipt['status']=='STATIC_VERIFIED_NOT_RUN' and receipt['candidate_member_count']==1141

check('ELF_PT_LOAD_and_57_distinct_BRK_entries',test_elf)
check('IM_DT_DEBUG_bounded_link_map_and_negative',test_link_map)
check('all_63_Z1_preinstalled_or_no_resume',test_z1_fail_closed)
check('migrated_vcpu_same_TLS_and_wrong_TLS_frame_rejected',test_cross_vcpu_tls_and_frame)
check('IM_dlsym_cross_vcpu_same_record_TLS_and_negatives',test_im_record_cross_vcpu)
check('fault_stops_never_resume_for_API16',test_no_resume_on_fault)
check('real_snapshot_and_static_CPIO',test_real_input_and_guest_output)
print(json.dumps({'status':'PASS_NO_QEMU','tests':passes,
    'guest_probe_sha256':hashlib.sha256((HERE/'guest_probe.py').read_bytes()).hexdigest()},indent=2))
