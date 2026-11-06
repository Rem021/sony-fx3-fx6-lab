"""Optional r15 diagnostic tail. Never a performance-window or End-state sample."""
from __future__ import annotations
import hashlib, json, re, secrets, socket, struct, time
from pathlib import Path

BASE=0x41dc00000
REQ=BASE+0x3000
ACK=BASE+0x3040
SLOT_BYTES=0xc0+0x310
REQ_MAGIC=0x35514552; READY_MAGIC=0x35594452; ACK_MAGIC=0x354b4341
REQ_COMMIT=0x51524551; ACK_COMMIT=0x4b43414f; VERSION=5
UI_MAGIC=0x3145544147335846

class TailError(RuntimeError): pass

class GateWire:
    """Borrows the sole GDB stream; restore its timeout or discard an uncertain stream."""
    def __init__(self, gate, clock):
        self.gate=gate;self.clock=clock;self.unknown=False
        self.original_sock=gate.sock
        self.original_timeout=gate.sock.gettimeout() if gate.sock is not None else None
    def release(self):
        sock=self.gate.sock
        if sock is None:return
        if self.unknown:
            try:sock.close()
            finally:self.gate.sock=None
        elif sock is self.original_sock:
            sock.settimeout(self.original_timeout)
        else:
            sock.settimeout(3.0)
    def _left(self, deadline):
        left=deadline-self.clock()
        if left<=0: raise TimeoutError('tail_capture_deadline')
        return left
    def _recv(self, deadline):
        self.gate.sock.settimeout(self._left(deadline))
        b=self.gate.sock.recv(1)
        if not b: raise TailError('gdb_eof')
        return b
    def packet(self, payload, deadline):
        if self.unknown: raise TailError('prior_gdb_send_or_reply_unknown')
        data=payload.encode();self.gate.sock.settimeout(self._left(deadline))
        try: self.gate.sock.sendall(b'$'+data+b'#'+f'{sum(data)%256:02x}'.encode())
        except (OSError,TimeoutError) as exc:
            self.unknown=True;raise TailError('gdb_send_unknown') from exc
        try:
            while True:
                c=self._recv(deadline)
                if c in (b'+',b'-'): continue
                if c!=b'$': continue
                out=bytearray()
                while True:
                    c=self._recv(deadline)
                    if c==b'#': break
                    out.extend(c)
                    if len(out)>8192: raise TailError('gdb_packet_oversize')
                check=self._recv(deadline)+self._recv(deadline)
                if int(check,16)!=sum(out)%256: raise TailError('gdb_checksum')
                self.gate.sock.settimeout(self._left(deadline));self.gate.sock.sendall(b'+')
                v=out.decode()
                if v.startswith(('T','S')) or (v.startswith('O') and v!='OK'):continue
                return v
        except BaseException:
            self.unknown=True;raise
    def connect(self, deadline):
        if self.gate.sock is None:
            sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            sock.settimeout(self._left(deadline))
            try: sock.connect(self.gate.socket_path)
            except BaseException: sock.close();raise
            self.gate.sock=sock
            if self.packet('Qqemu.PhyMemMode:1',deadline)!='OK' or self.packet('qqemu.PhyMemMode',deadline)!='1':
                self.unknown=True  # a newly connected stream has no proved physical mode
                raise TailError('physical_gdb_mode_unavailable')
    def read(self, address, length, deadline):
        raw=self.packet(f'm{address:x},{length:x}',deadline)
        try: data=bytes.fromhex(raw)
        except ValueError as exc: raise TailError('invalid_gdb_hex') from exc
        if len(data)!=length: raise TailError('short_gdb_memory_read')
        return data
    def write(self,address,data,deadline):
        if self.packet(f'M{address:x},{len(data):x}:{data.hex()}',deadline)!='OK':
            raise TailError('gdb_write_not_acknowledged')

def fnv32(raw):
    h=2166136261
    for b in raw: h=((h^b)*16777619)&0xffffffff
    return h

def _qmp_ok(reply):return isinstance(reply,dict) and 'return' in reply and 'error' not in reply

def capture(qmp, transport, gate, serial_path, run, launch_uuid, snapshots,
            *, budget=2.0, stop_budget=5.0, clock=time.monotonic, sleep=time.sleep,
            nonce_factory=lambda:secrets.randbits(64)):
    """All guest writes are inside a proved pause; no extra key or auto retry."""
    started=clock();deadline=started+budget;run=Path(run);serial_path=Path(serial_path)
    rec={'status':'unknown','snapshot_is_end_state':False,'post_snapshot_event_counts':'unknown',
         'performance_window_closed_before_tail':True,'host_monotonic_start':started,
         'capture_budget_seconds':budget,'stop_cleanup_budget_seconds':stop_budget,
         'qmp_cont_sent':False,'tail_stop_attempted':False,'reads':[],'errors':[]}
    wire=GateWire(gate,clock);cont_attempted=False;pause_proven=False
    tag=None;nonce=None;pid=None;root=None;serial_found=False
    def left():
        remaining=deadline-clock()
        if remaining<=0:raise TimeoutError('tail_capture_deadline')
        return remaining
    def ask(cmd,args=None):
        if transport is None or transport.send_unknown:raise TailError('qmp_send_unknown')
        return qmp(cmd,args,timeout=min(3.0,left()))
    def qmp_read(name,address,length,read_deadline):
        if transport is None or transport.send_unknown:raise TailError('qmp_send_unknown_before_slot_read')
        path=run/name
        if path.exists() or path.is_symlink():raise TailError('existing_tail_evidence_path')
        remaining=read_deadline-clock()
        if remaining<=0:raise TimeoutError('tail_read_budget')
        reply=qmp('human-monitor-command',{'command-line':f'pmemsave {address:#x} {length:#x} "{path}"'},timeout=min(3.0,remaining))
        item={'name':name,'address':hex(address),'expected_bytes':length,'qmp_response':reply}
        rec['reads'].append(item)
        if clock()>=read_deadline:raise TimeoutError('tail_pmemsave_reply_after_deadline')
        if not _qmp_ok(reply):raise TailError('tail_pmemsave_failed')
        if not path.is_file() or path.is_symlink():raise TailError('tail_pmemsave_file_missing')
        raw=path.read_bytes();item['bytes']=len(raw);item['sha256']=hashlib.sha256(raw).hexdigest()
        if clock()>=read_deadline:raise TimeoutError('tail_slot_read_completed_after_deadline')
        if len(raw)!=length:raise TailError('tail_pmemsave_length_mismatch')
        return raw
    try:
        if not 0<budget<=2 or not 0<stop_budget<=10:raise ValueError('invalid_tail_budget')
        if not isinstance(launch_uuid,str) or len(launch_uuid)>80:raise TailError('launch_uuid_missing')
        ui=[s for s in snapshots if s.get('name')=='ui-gate-counters.bin' and s.get('address')==BASE and s.get('size')==0x10000]
        if len(ui)!=1:raise TailError('ui_gate_fdt_reservation_mismatch')
        status=ask('query-status');rec['pre_tail_status_response']=status
        state=status.get('return') if _qmp_ok(status) else None
        if not isinstance(state,dict) or state.get('running') is not False or state.get('status')!='paused':raise TailError('pre_tail_not_paused')
        pause_proven=True
        wire.connect(deadline)
        old=wire.read(BASE,64,deadline);header=struct.unpack('<8Q',old)
        if header[0]!=UI_MAGIC or header[1]!=2 or not header[4]:raise TailError('original_ui_observer_identity_mismatch')
        ready=wire.read(ACK,0xc0,deadline);w=struct.unpack('<48I',ready)
        pid=header[4];root=w[4]|(w[5]<<32)
        if w[0]!=READY_MAGIC or w[1]!=VERSION or w[2]!=0xc0 or w[3]!=pid or not root or w[6]!=0x310 or w[19]!=0:
            raise TailError('snapshot_v5_ready_identity_missing_or_mismatch')
        rec['guest_pid']=pid;rec['root']=hex(root)
        tag=int.from_bytes(hashlib.sha256(launch_uuid.encode()).digest()[:8],'little') or 1
        nonce=nonce_factory()
        if type(nonce) is not int or not 0<nonce<1<<64:raise TailError('invalid_nonce')
        rec['host_launch_uuid']=launch_uuid;rec['host_launch_tag']=hex(tag);rec['nonce']=hex(nonce)
        req=[REQ_MAGIC,VERSION,0x310,pid,tag&0xffffffff,tag>>32,nonce&0xffffffff,nonce>>32,
             root&0xffffffff,root>>32,0x3100,0x310,0,0,0,REQ_COMMIT]
        raw=struct.pack('<16I',*req)
        wire.write(REQ,raw[:60],deadline)
        if wire.read(REQ,60,deadline)!=raw[:60]:raise TailError('request_precommit_readback_mismatch')
        wire.write(REQ+60,raw[60:],deadline)
        if wire.read(REQ,64,deadline)!=raw:raise TailError('request_committed_readback_mismatch')
        rec['request_sha256']=hashlib.sha256(raw).hexdigest();rec['request_readback_complete']=True
        if serial_path.exists():serial_offset=serial_path.stat().st_size
        else:serial_offset=0
        left() # no cont once the two-second capture budget is consumed
        cont_attempted=True;pause_proven=False;rec['qmp_cont_attempted']=True
        reply=ask('cont');rec['cont_response']=reply
        if not _qmp_ok(reply):raise TailError('tail_cont_not_acknowledged')
        rec['qmp_cont_acknowledged']=True;rec['host_monotonic_cont']=clock()
        pattern=re.compile(rb'FX3_UI_GATE_SNAPSHOT_ACK pid='+str(pid).encode()+rb' tag='+re.escape(hex(tag).encode())+rb' nonce='+re.escape(hex(nonce).encode())+rb' probe=[0-9]+[^\r\n]*\r?\n')
        seen=bytearray()
        while clock()<deadline and not transport.send_unknown:
            if serial_path.exists():
                with serial_path.open('rb') as f:f.seek(serial_offset);chunk=f.read(65536);serial_offset=f.tell()
                if chunk:
                    seen.extend(chunk)
                    if len(seen)>131072:seen=seen[-131072:]
                    match=pattern.search(seen)
                    if match:
                        serial_found=True;rec['serial_ack_line']=match[0].decode(errors='replace');rec['host_monotonic_ack_seen']=clock();break
            sleep(min(.02,max(0,deadline-clock())))
        rec['serial_ack_matched']=serial_found
        if not serial_found:rec['errors'].append('serial_ack_timeout_or_missing')
    except BaseException as exc:
        rec['errors'].append(repr(exc))
    finally:
        rec['host_monotonic_capture_end']=clock();rec['capture_elapsed_seconds']=rec['host_monotonic_capture_end']-started
        rec['capture_deadline_expired']=clock()>=deadline
        rec['gdb_transport_unknown']=wire.unknown
        rec['qmp_transport_unknown']=bool(transport and transport.send_unknown)
        if cont_attempted and transport is not None and not transport.send_unknown:
            stop_deadline=clock()+stop_budget
            def stop_left():
                remaining=stop_deadline-clock()
                if remaining<=0:raise TimeoutError('tail_stop_or_slot_budget_expired')
                return min(3.0,remaining)
            try:
                # A lost cont reply may still mean that QEMU is running.  Query
                # the same id-matching transport before deciding whether to stop.
                reply=qmp('query-status',timeout=stop_left())
                rec['post_cont_status_response']=reply
                state=reply.get('return') if _qmp_ok(reply) else None
                if not isinstance(state,dict):raise TailError('tail_status_not_available')
                if state.get('running') is True:
                    rec['tail_stop_attempted']=True
                    reply=qmp('stop',timeout=stop_left());rec['stop_response']=reply
                    if not _qmp_ok(reply):raise TailError('tail_stop_not_acknowledged')
                elif state.get('running') is not False or state.get('status')!='paused':
                    raise TailError('tail_status_not_paused_or_running')
                reply=qmp('query-status',timeout=stop_left())
                rec['post_tail_status_response']=reply
                state=reply.get('return') if _qmp_ok(reply) else None
                if not isinstance(state,dict) or state.get('running') is not False or state.get('status')!='paused':
                    raise TailError('tail_post_stop_not_paused')
                pause_proven=True;rec['host_monotonic_stop_proven']=clock()
                # Slot reads are optional.  Restore/quit must not wait for a
                # read that begins after the diagnostic cleanup budget.
                a=qmp_read('snapshot-tail-slot-1.bin',ACK,SLOT_BYTES,stop_deadline)
                b=qmp_read('snapshot-tail-slot-2.bin',ACK,SLOT_BYTES,stop_deadline)
                if clock()>=stop_deadline:raise TimeoutError('tail_slot_validation_after_deadline')
                if a!=b:raise TailError('snapshot_slot_changed_between_paused_reads')
                h=struct.unpack_from('<48I',a);payload=a[0xc0:]
                u64=lambda at:h[at]|(h[at+1]<<32)
                if not (h[0]==ACK_MAGIC and h[1]==VERSION and h[2]==0xc0 and h[3]==pid and
                        u64(4)==tag and u64(6)==nonce and u64(8)==root and h[16]==0x310 and
                        h[17]==fnv32(payload) and h[18]==1 and h[19]==ACK_COMMIT and
                        u64(12)>0 and u64(14)>=u64(12)):
                    raise TailError('snapshot_slot_identity_commit_or_checksum_mismatch')
                rec['slot_valid']=True;rec['guest_clock1_copy_begin_ns']=u64(12);rec['guest_clock1_copy_end_ns']=u64(14)
                rec['probe_id']=h[10];rec['guest_tid']=h[11]
                rec['statistics_prefix_96Q']=list(struct.unpack_from('<96Q',payload))
                rec['object_mismatch'],rec['root_change']=struct.unpack_from('<2Q',payload,0x300)
                if serial_found and rec.get('qmp_cont_acknowledged'):
                    rec['status']='valid_nontransactional_tail_checkpoint'
                else:rec['status']='unknown_ack_or_cont_reply_missing_slot_valid'
            except BaseException as exc:
                rec['errors'].append('post_cont_stop_or_read:'+repr(exc))
        elif cont_attempted:
            rec['errors'].append('qmp_send_unknown_cannot_safely_issue_tail_stop')
        try:wire.release()
        except BaseException as exc:rec['errors'].append('gdb_release:'+repr(exc))
        rec['host_monotonic_end']=clock();rec['pause_proven_at_return']=pause_proven
        rec['qmp_cont_attempted']=cont_attempted
        rec['post_deadline_cleanup_elapsed_seconds']=max(0,rec['host_monotonic_end']-max(deadline,rec['host_monotonic_capture_end']))
        try:
            path=run/'snapshot-tail-receipt.json'
            if path.exists():raise FileExistsError(path)
            path.write_text(json.dumps(rec,indent=2)+'\n')
        except Exception as exc:
            rec['errors'].append('receipt_write:'+repr(exc))
            rec['status']='unknown_receipt_write_failed'
    return rec
