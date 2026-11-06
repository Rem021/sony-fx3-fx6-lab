#!/usr/bin/env python3
"""No-QEMU tests for RSP framing, actual old maps and fail-closed hit handling."""
import importlib.util
import json
import socket
import struct
import threading
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('readonly_probe',HERE/'readonly_probe.py')
rp=importlib.util.module_from_spec(spec);spec.loader.exec_module(rp)
spec2=importlib.util.spec_from_file_location('two_phase_identity',HERE/'two_phase_identity.py')
identity=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(identity)
DONOR=HERE.parent
OLD=DONOR/'hybrid-ap-candidate/runs/fx6ap-bb7588e5/serial.log'
NEW=HERE/'runs/ap-ro-f58ad0fb/serial.log'
AP=DONOR/'nflasha15-files/lib/appFw.so'
CAP=HERE.parents[5]/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-capid-v49-touch100.so'
checks=[]
def check(name,fn):
    fn();checks.append(name)
def fake(pairs,action):
    a,b=socket.socketpair();a.settimeout(.3);b.settimeout(.3);errors=[]
    def server():
        try:
            for want,replies in pairs:
                while b.recv(1)!=b'$':pass
                got=b''
                while True:
                    c=b.recv(1)
                    if c==b'#':break
                    got+=c
                checksum=b.recv(2)
                assert checksum==f'{sum(got)&255:02x}'.encode()
                assert got.decode()==want,(got,want)
                b.sendall(b'+')
                for response in replies:
                    raw=rp.rsp_packet(response)
                    for part in [raw[:2],raw[2:5],raw[5:]]:
                        if part:b.sendall(part)
                    assert b.recv(1)==b'+'
        except BaseException as e:errors.append(repr(e))
        finally:b.close()
    t=threading.Thread(target=server);t.start();r=rp.RSP(a)
    try:action(r)
    finally:r.close();t.join(2)
    assert not t.is_alive() and not errors,errors

def maps_positive():
    b=OLD.read_bytes();m=rp.choose_mapping(b,AP,CAP)
    assert m['pid']==239 and m['block_complete']
    assert m['ap']['bias']==0x7edd55b000 and m['cap']['bias']==0x7f90b0c000
    assert m['ap']['bias']+0x20ef7a0==0x7edf64a7a0
    assert m['cap']['bias']+0x1e730==0x7f90b2a730
    # start-fileoff on the second AP PT_LOAD would be 0x10000 too low.
    rw=next(x for x in m['ap']['rows'] if x['perms']=='r--p' and x['offset']==0x2901000)
    assert rw['start']-rw['offset']==m['ap']['bias']+0x10000
check('historical_maps_ptload_bias_positive',maps_positive)

def maps_negative():
    b=OLD.read_bytes();needle=b'7edfe6c000-7ee044c000 r--p 02901000'
    assert needle in b
    assert rp.choose_mapping(b.replace(needle,b'7edfe6c000-7ee044c000 r--p 02902000',1),AP,CAP) is None
    fresh=b'FX3_AP_IM_PROCESS=11\n7edd55b000-7edfe5c000 r-xp 00000000 00:02 2461 /usr/lib/appFw.so\nFX3_TASK_SNAPSHOT_1_BEGIN\nFX3_AP_IM_PROCESS=22\n7f90b0c000-7f90b12000 r--p 00000000 00:02 1636 /simulation/fx3-capid-v1.so\n'
    assert rp.choose_mapping(fresh,AP,CAP) is None
    complete=b.find(b'FX3_TASK_SNAPSHOT_',b.find(b'FX3_AP_IM_PROCESS='))
    assert complete>0
    assert rp.choose_mapping(b[:complete],AP,CAP) is None
check('wrong_offset_cross_pid_and_incomplete_maps_rejected',maps_negative)

def actual_early_maps_boundary():
    b=NEW.read_bytes();blocks=[x for x in rp.parse_maps(b) if x['kind']=='early']
    assert [x['epoch'] for x in blocks]==[1,2,3,4,5]
    assert all(x['pid']==237 and x['complete'] and x['byte_end']<b.find(b'FX3_PROVIDER_REQUEST destination=0x92840747') for x in blocks)
    biases=[rp.map_bias(x['rows'],rp.CAP_PATH,rp.elf_loads(CAP))['bias'] for x in blocks]
    assert len(set(biases))==1 and biases[0]==0x7f816d4000
    assert all(not any(r['path']==rp.AP_PATH for r in x['rows']) for x in blocks)
    assert rp.choose_mapping(b,AP,CAP) is None
    candidate=identity.choose_early_cap(b,CAP)
    assert candidate['pid']==237 and candidate['cap']['bias']==0x7f816d4000 and candidate['ap'] is None
    mixed=b.replace(b'FX3_AP_EARLY_MAPS_237_5_BEGIN',b'FX3_AP_EARLY_MAPS_999_5_BEGIN',1).replace(
        b'FX3_AP_EARLY_MAPS_237_5_END',b'FX3_AP_EARLY_MAPS_999_5_END',1)
    assert identity.choose_early_cap(mixed,CAP) is None
    truncated=b[:blocks[-1]['byte_end']-10]
    assert not [x for x in rp.parse_maps(truncated) if x['kind']=='early' and x['epoch']==5 and x['complete']]
check('current_run_early_CAP_complete_AP_absent_and_truncation_negative',actual_early_maps_boundary)

def real_profile_and_rejects():
    import re
    spec=importlib.util.spec_from_file_location('run_once',HERE/'run_once.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    raw=NEW.read_bytes();native=mod._lineage(raw)
    proof=identity.target_profile(raw,native,AP)
    assert proof['bias']==0x7ed2a91000 and proof['frame_count']>=2
    bad=dict(native);bad['tid']+=1
    try:identity.target_profile(raw,bad,AP)
    except ValueError:pass
    else:raise AssertionError('mixed TID profile accepted')
    bad=dict(native);bad['source']^=1
    try:identity.target_profile(raw,bad,AP)
    except ValueError:pass
    else:raise AssertionError('wrong source profile accepted')
    start,end=proof['profile_byte_range']
    altered=raw[:start]+raw[start:end].replace(b' relative=0x20f160c',b' relative=0x20f1608',1)+raw[end:]
    try:identity.target_profile(altered,native,AP)
    except ValueError:pass
    else:raise AssertionError('mixed dladdr base accepted')
    try:identity.target_profile(raw[:proof['profile_byte_range'][0]],native,AP)
    except ValueError:pass
    else:raise AssertionError('missing profile/request accepted')
check('real_pre_call_profile_base_and_missing_mixed_rejection',real_profile_and_rejects)

def current_elf_identity_negative():
    # All reads are from fixed original ELF bytes, then one controlled corrupt
    # byte per case. No guest binary is executed or modified.
    base=0x7ed2a91000
    segments=rp.elf_loads(AP)
    class Image:
        def __init__(self,corrupt):self.corrupt=corrupt
        def virtual_read(self,addr,n):
            va=addr-base
            seg=next(x for x in segments if x['va']<=va and va+n<=x['va']+x['filesz'])
            with AP.open('rb') as f:f.seek(seg['fileoff']+va-seg['va']);b=bytearray(f.read(n))
            if addr<=self.corrupt<addr+n:b[self.corrupt-addr]^=1
            return bytes(b)
    samples=[base,base+0x40,base+0x20ef7a0]
    for addr in samples:
        try:identity.read_current_identity(Image(addr),base,AP,[0x20ef79c,0x20ef7a0])
        except ValueError:pass
        else:raise AssertionError(('accepted_corrupt_ELF_or_word',hex(addr)))
    good=identity.read_current_identity(Image(-1),base,AP,[0x20ef79c,0x20ef7a0])
    assert good['bias']==hex(base) and good['program_header_bytes']==336
check('current_cpu_ELF_header_PHDR_original_word_positive_and_negatives',current_elf_identity_negative)

def rsp_split_and_async():
    def act(r):
        assert r.command('Qqemu.PhyMemMode:1')=='OK'
        assert r.command('Hg2')=='OK'
        assert r.stops.pop()=='T05thread:2;'
        assert r.command('m10,4')=='fd7bbaa9'
        assert r.command('z1,100,4')=='OK'
        for forbidden in ['M100,4:ffff','G'+('0'*8),'P0=0','Z0,100,4','vCont;s:2']:
            try:r.command(forbidden)
            except ValueError:pass
            else:raise AssertionError(forbidden)
    fake([('Qqemu.PhyMemMode:1',['OK']),('Hg2',['T05thread:2;','OK']),
          ('m10,4',['fd7bbaa9']),('z1,100,4',['OK'])],act)
check('rsp_fragment_ack_async_and_command_allowlist',rsp_split_and_async)

def rsp_checksum_bad():
    a,b=socket.socketpair();a.settimeout(.3);b.settimeout(.3)
    def server():
        assert b.recv(1)==b'$'
        while b.recv(1)!=b'#':pass
        b.recv(2);b.sendall(b'+$OK#00');assert b.recv(1)==b'-';b.close()
    t=threading.Thread(target=server);t.start();r=rp.RSP(a)
    try:
        try:r.command('Qqemu.PhyMemMode:1')
        except ValueError as e:assert 'checksum' in str(e)
        else:raise AssertionError('bad checksum accepted')
    finally:r.close();t.join(2)
check('rsp_bad_checksum_nack_and_abort',rsp_checksum_bad)

def rsp_timeout():
    a,b=socket.socketpair();a.settimeout(.05);b.settimeout(.05)
    def server():
        assert b.recv(1)==b'$'
        while b.recv(1)!=b'#':pass
        b.recv(2);time.sleep(.25);b.close()
    t=threading.Thread(target=server);t.start();r=rp.RSP(a)
    try:
        try:r.command('Qqemu.PhyMemMode:1',timeout=.1)
        except TimeoutError:pass
        else:raise AssertionError('silent RSP accepted')
    finally:r.close();t.join(2)
check('rsp_bounded_timeout',rsp_timeout)

def rsp_unsolicited_stop():
    a,b=socket.socketpair();a.settimeout(.3);b.settimeout(.3)
    def server():
        raw=rp.rsp_packet('T05thread:2;')
        b.sendall(raw[:4]);b.sendall(raw[4:]);assert b.recv(1)==b'+';b.close()
    t=threading.Thread(target=server);t.start();r=rp.RSP(a)
    try:assert r.poll_stop(.1)=='T05thread:2;'
    finally:r.close();t.join(2)
check('rsp_unsolicited_stop_fragmented',rsp_unsolicited_stop)

def unknown_hit():
    class Stub:
        def select_thread(self,stop):return '2'
        def regs(self):return tuple([0]*32+[0x1234])
    mapping={'cap':{'bias':0x7f90b0c000},'ap':{'bias':0x7edd55b000}}
    try:rp.confirm_hit(Stub(),'T05thread:2;',mapping,0x7f90b2a730,'cap')
    except ValueError as e:assert 'unknown breakpoint PC' in str(e)
    else:raise AssertionError('unknown hit accepted')
    try:rp.confirm_hit(Stub(),'T05core:02;',mapping,0x1234,'cap')
    except ValueError:pass
    else:raise AssertionError('CPU-unattributed hit accepted')
check('wrong_pc_and_unattributed_cpu_rejected',unknown_hit)

def remove_all_cleanup():
    spec=importlib.util.spec_from_file_location('run_once',HERE/'run_once.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    class Stub:
        def __init__(self,answer):self.answer=answer;self.cmd=[]
        def command(self,x):self.cmd.append(x);return self.answer
    m=rp.choose_mapping(OLD.read_bytes(),AP,CAP)
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        o=mod.Probe(Path(d),None,m);o.rsp=Stub('OK');o.breakpoints={0x100,0x200}
        assert o.remove_all()['all_removed'] and o.rsp.cmd==['z1,100,4','z1,200,4']
        o=mod.Probe(Path(d),None,m);o.rsp=Stub('E22');o.breakpoints={0x100}
        result=o.remove_all()
        assert not result['all_removed'] and result['unremoved']==['0x100']
        saved=json.loads((Path(d)/'readonly-observation.json').read_text())
        assert saved['breakpoints_still_installed']==['0x100']
check('z1_cleanup_success_and_failure_visible',remove_all_cleanup)

def failed_breakpoint_no_resume():
    spec=importlib.util.spec_from_file_location('run_once',HERE/'run_once.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    class FakeQMP:
        def __init__(self):self.calls=[];self.closed=False
        def call(self,name):self.calls.append(name)
        def close(self):self.closed=True
    class FakeQemu:
        def __init__(self):self.exited=False
        def poll(self):return 0 if self.exited else None
        def wait(self,timeout):self.exited=True
    q=FakeQMP();p=FakeQemu();cleanup={'API16_restored':False}
    mod.quit_without_guest_resume(p,q,cleanup)
    assert q.calls==['stop','quit'] and q.closed and p.exited
    assert cleanup['reason']=='unremoved_debug_breakpoint; no_API16_resume'
check('failed_z1_no_guest_resume_or_restore_write',failed_breakpoint_no_resume)

def same_call_capture():
    spec=importlib.util.spec_from_file_location('run_once',HERE/'run_once.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    m=identity.choose_early_cap(OLD.read_bytes(),CAP)
    full=rp.choose_mapping(OLD.read_bytes(),AP,CAP);ap=full['ap']['bias'];cap=m['cap']['bias']
    ptr=0x7ed155ff00;fp=0x7ed1559100;cap_fp=fp-0x80;native=OLD.read_bytes()
    class FakeRSP:
        def __init__(self):self.stage=0;self.cmd=[]
        def select_thread(self,stop):return '2'
        def regs(self):
            r=[0]*33;r[29]=cap_fp if self.stage==0 else fp;r[0]=ptr if self.stage==0 else 0xfffffc03
            r[32]=cap+0x1e730 if self.stage==0 else ap+0x20ef7a0
            return tuple(r)
        def virtual_read(self,addr,n):
            vals={cap+0x1e730:bytes.fromhex('ff8301d1'),ap+0x20ef79c:bytes.fromhex('61aaa897'),
                ap+0x20ef7a0:bytes.fromhex('e0000034'),ptr:bytes.fromhex('0d202d030a0001800000'),
                cap+0x45bc0:bytes(4),cap+0x45b08:bytes(8),fp+0x58:struct.pack('<Q',ptr),
                cap_fp:struct.pack('<QQ',fp,ap+0x20ef7a0)}
            if addr in vals:
                assert len(vals[addr])==n,(hex(addr),n)
                return vals[addr]
            for base,path in [(ap,AP),(cap,CAP)]:
                for seg in rp.elf_loads(path):
                    va=addr-base
                    if seg['va']<=va and va+n<=seg['va']+seg['filesz']:
                        with path.open('rb') as f:
                            f.seek(seg['fileoff']+va-seg['va']);data=f.read(n)
                        assert len(data)==n
                        return data
            raise AssertionError((hex(addr),n))
        def command(self,p):self.cmd.append(p);return 'OK'
        def send_continue(self):self.cmd.append('c');return {'command':'c','ack':'+'}
    class FakeSys:
        def read(self,p):assert p=='TPIDR_EL0';return 0x7ed155a740
    class FakeQMP:
        def __init__(self):self.calls=[]
        def call(self,p):self.calls.append(p);return {'status':'debug'} if p=='query-status' else {}
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        q=FakeQMP();o=mod.Probe(Path(d),q,m);o.rsp=FakeRSP();o.sysregs=FakeSys();o.stage='await_audio_entry';o.breakpoints={o.cap_entry}
        assert o.process_stop('T05thread:2;',native) is False
        assert o.records[0]['model_initialized']==0 and o.stage=='await_same_call_return'
        assert o.records[0]['ap_frame_anchor']==hex(fp)
        assert o.records[0]['current_ap_identity']['bias']==hex(ap)
        o.rsp.stage=1
        assert o.process_stop('T05thread:2;',native) is True
        assert o.records[1]['send_w0_signed32']==-1021 and o.records[1]['assert_branch_will_fire']
        assert o.stage=='same_call_return_captured' and q.calls.count('cont')==0
        assert o.resume_acks==[{'stage':'await_same_call_return','command':'c','ack':'+'}]
    with tempfile.TemporaryDirectory() as d:
        class BadTLS:
            def read(self,p):return 0x123456
        o=mod.Probe(Path(d),FakeQMP(),m);o.rsp=FakeRSP();o.sysregs=BadTLS();o.stage='await_audio_entry';o.breakpoints={o.cap_entry}
        assert o.process_stop('T05thread:2;',native) is True
        assert o.stage=='unknown_hit_stop' and 'model_initialized' not in o.records[0]
    with tempfile.TemporaryDirectory() as d:
        class NoFrame(FakeRSP):
            def virtual_read(self,addr,n):
                if addr==cap_fp:raise ValueError('unavailable current frame')
                return super().virtual_read(addr,n)
        o=mod.Probe(Path(d),FakeQMP(),m);o.rsp=NoFrame();o.sysregs=FakeSys();o.stage='await_audio_entry';o.breakpoints={o.cap_entry}
        assert o.process_stop('T05thread:2;',native) is True
        assert o.stage=='unknown_hit_stop' and 'model_initialized' not in o.records[0]
check('same_request_tls_return_and_model_capture',same_call_capture)

def resume_wire_early():
    for coalesced in (False,True):
        a,b=socket.socketpair();a.settimeout(.4);b.settimeout(.4);errors=[]
        def server():
            try:
                assert b.recv(1)==b'$' and b.recv(1)==b'c'
                assert b.recv(1)==b'#' and b.recv(2)==b'63'
                pkt=rp.rsp_packet('T05thread:2;')
                if coalesced:b.sendall(b'+'+pkt)
                else:
                    b.sendall(b'+')
                    # No packet, keepalive, mode query or preemptive ACK while running.
                    import select
                    assert not select.select([b],[],[],.03)[0]
                    for part in (pkt[:1],pkt[1:5],pkt[5:8],pkt[8:]):
                        b.sendall(part);time.sleep(.003)
                assert b.recv(1)==b'+'
            except BaseException as e:errors.append(repr(e))
            finally:b.close()
        t=threading.Thread(target=server);t.start();r=rp.RSP(a)
        try:
            assert r.send_continue()=={'command':'c','ack':'+'}
            assert r.poll_stop(.2)=='T05thread:2;'
        finally:r.close();t.join(2)
        assert not t.is_alive() and not errors,(coalesced,errors)
check('resume_ACK_then_fragmented_early_T05_and_outbound_silence',resume_wire_early)

def resume_wire_late():
    a,b=socket.socketpair();a.settimeout(3);b.settimeout(3);errors=[]
    def server():
        try:
            assert b.recv(1)==b'$' and b.recv(1)==b'c'
            assert b.recv(1)==b'#' and b.recv(2)==b'63'
            b.sendall(b'+');time.sleep(2.1)
            b.sendall(rp.rsp_packet('T05thread:p1.2;'))
            assert b.recv(1)==b'+'
        except BaseException as e:errors.append(repr(e))
        finally:b.close()
    t=threading.Thread(target=server);t.start();r=rp.RSP(a)
    try:
        assert r.send_continue()['ack']=='+'
        assert r.poll_stop(.02) is None
        assert r.poll_stop(2.5)=='T05thread:p1.2;'
    finally:r.close();t.join(2)
    assert not t.is_alive() and not errors,errors
check('resume_late_T05_not_a_2s_command_reply',resume_wire_late)

def resume_wire_failures():
    for mode in ('timeout','disconnect','nack','stop_before_ack'):
        a,b=socket.socketpair();a.settimeout(.3);b.settimeout(.3);seen=[]
        def server():
            try:
                assert b.recv(1)==b'$' and b.recv(1)==b'c'
                assert b.recv(1)==b'#' and b.recv(2)==b'63'
                if mode=='disconnect':
                    b.close();return
                if mode=='timeout':
                    time.sleep(.14)
                elif mode=='nack':b.sendall(b'-')
                elif mode=='stop_before_ack':b.sendall(rp.rsp_packet('T05thread:2;'))
                # A failed continue must never be automatically retransmitted.
                b.settimeout(.04)
                try:seen.append(b.recv(100))
                except socket.timeout:seen.append(b'')
            finally:b.close()
        t=threading.Thread(target=server);t.start();r=rp.RSP(a)
        try:
            expected={'timeout':TimeoutError,'disconnect':ConnectionError,
                      'nack':ValueError,'stop_before_ack':ValueError}[mode]
            try:r.send_continue(timeout=.08)
            except expected:pass
            else:raise AssertionError('failed continue accepted '+mode)
        finally:r.close();t.join(2)
        assert not t.is_alive() and seen==([] if mode=='disconnect' else [b'']),(mode,seen)
check('resume_ACK_timeout_disconnect_NACK_wrong_order_no_retry',resume_wire_failures)

def qmp_without_rsp_fails_closed():
    spec=importlib.util.spec_from_file_location('run_once',HERE/'run_once.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    class Q:
        def call(self,name):assert name=='query-status';return {'status':'debug'}
    class R:
        def __init__(self,event):self.event=event;self.calls=[]
        def poll_stop(self,timeout):self.calls.append(timeout);return self.event
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        o=mod.Probe(Path(d),Q(),{'cap':{'bias':0}});o.rsp=R(None)
        try:o.check_qmp_without_rsp()
        except RuntimeError as e:assert 'without RSP stop packet' in str(e)
        else:raise AssertionError('silent QMP debug accepted')
        saved=json.loads((Path(d)/'readonly-observation.json').read_text())
        assert saved['stage']=='qmp_debug_without_rsp_stop'
        assert saved['qmp_statuses']==[{'stage':'unarmed','status':'debug'}]
        o=mod.Probe(Path(d),Q(),{'cap':{'bias':0}});o.rsp=R('T05thread:2;')
        assert o.check_qmp_without_rsp()=='T05thread:2;'
check('QMP_debug_crosscheck_without_RSP_fails_closed_or_preserves_T05',qmp_without_rsp_fails_closed)

def real_rsp_thread_field_parser():
    # Exercise the real parser and real framed Hg/Hc writes over socketpair.
    for stop,tid in [('T05thread:02;','02'),
                     ('T05core:01;thread:02;','02'),
                     ('T05thread:p1.02;core:01;','p1.02')]:
        def accept(rsp):assert rsp.select_thread(stop)==tid
        fake([('Hg'+tid,['OK']),('Hc'+tid,['OK'])],accept)
    bad=['T05','T05core:01;','T05thread:;','T05thread:zz;',
         'T05thread:02;thread:03;','T05thread:02','T05;thread:02;',
         'S05thread:02;','T02thread:02;','T05thread:p1.;']
    for stop in bad:
        a,b=socket.socketpair();b.settimeout(.01);rsp=rp.RSP(a)
        try:
            try:rsp.select_thread(stop)
            except ValueError:pass
            else:raise AssertionError('invalid stop accepted '+stop)
            try:wire=b.recv(100)
            except socket.timeout:wire=b''
            assert wire==b'',(stop,wire)
        finally:rsp.close();b.close()
    def reject_hg(rsp):
        try:rsp.select_thread('T05thread:02;')
        except ValueError as e:assert 'CPU selection failed' in str(e)
        else:raise AssertionError('Hg failure accepted')
    fake([('Hg02',['E22'])],reject_hg)
check('real_RSP_select_thread_first_later_multiprocess_and_rejections',real_rsp_thread_field_parser)

(HERE/'host-tests.json').write_text(json.dumps({'status':'PASS_NO_QEMU','cases':checks,
    'historical_serial_sha256':rp.sha(OLD),'observer_sha256':rp.sha(HERE/'readonly_probe.py'),
    'identity_sha256':rp.sha(HERE/'two_phase_identity.py'),
    'runner_sha256':rp.sha(HERE/'run_once.py')},indent=2)+'\n')
print(json.dumps({'status':'PASS_NO_QEMU','cases':checks},indent=2))
