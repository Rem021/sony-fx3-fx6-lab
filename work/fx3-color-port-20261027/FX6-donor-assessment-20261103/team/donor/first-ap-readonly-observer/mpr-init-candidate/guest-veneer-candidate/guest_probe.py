#!/usr/bin/env python3
"""Fail-closed host observer for the one patched AP Init call. Never writes guest memory."""
import hashlib
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import mpr_probe as previous
from two_phase_identity import read_current_identity

# Reuse the already tested IM record / dlsym return observer with this pinned AP.
previous.AP_ELF = HERE / 'appFw-bridge.so'
BRIDGE = HERE / 'libfx6diag.so'
MPR = previous.MPR_ELF
IM = previous.IM_ELF
AP_CALL = previous.CALL
AP_RETURN = previous.RETURN
FIRST_CONSUMER = 0x11fac8
BRIDGE_PATH = '/usr/lib/libfx6diag.so'


def dynamic_debug_va(path=IM):
    """Find DT_DEBUG in this image, never borrow a Sony/FX3 runtime address."""
    with Path(path).open('rb') as f:
        head = f.read(64)
        if head[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', head, 18)[0] != 183:
            raise ValueError('IM ELF machine')
        phoff = struct.unpack_from('<Q', head, 32)[0]
        count = struct.unpack_from('<H', head, 56)[0]
        if count > 64: raise ValueError('IM PHDR count')
        f.seek(phoff)
        phdr = f.read(count * 56)
        for i in range(count):
            p = i * 56
            kind = struct.unpack_from('<I', phdr, p)[0]
            if kind != 2: continue
            fileoff, va, _, filesz = struct.unpack_from('<QQQQ', phdr, p + 8)
            if filesz > 8192 or filesz % 16: raise ValueError('IM dynamic bounds')
            f.seek(fileoff)
            dyn = f.read(filesz)
            for j in range(0, filesz, 16):
                tag = struct.unpack_from('<Q', dyn, j)[0]
                if tag == 21: return va + j
    raise ValueError('IM DT_DEBUG absent')


def read_link_map(rsp, im_bias, limit=192):
    """Read glibc r_debug and bounded link_map in the stopped IM address space."""
    dyn = rsp.virtual_read(im_bias + dynamic_debug_va(), 16)
    tag, debug = struct.unpack('<QQ', dyn)
    if tag != 21 or debug == 0 or debug & 7: raise ValueError('runtime DT_DEBUG invalid')
    raw = rsp.virtual_read(debug, 16)
    version, first = struct.unpack_from('<I4xQ', raw)
    if version != 1 or not first: raise ValueError('r_debug layout/version')
    out = []
    visited = set()
    ptr = first
    while ptr:
        if ptr in visited or len(out) >= limit or ptr & 7: raise ValueError('link_map bounds/cycle')
        visited.add(ptr)
        addr, name, _ld, next_ptr, prev = struct.unpack('<5Q', rsp.virtual_read(ptr, 40))
        if not name: label = ''
        else:
            chunks=[];length=0
            while length<256:
                # Never ask GDB to read across a page merely to pass a NUL.
                n=min(16,256-length,4096-((name+length)&4095))
                part=rsp.virtual_read(name+length,n)
                chunks.append(part)
                if b'\0' in part:break
                length+=n
            raw_name=b''.join(chunks)
            if b'\0' not in raw_name: raise ValueError('unbounded link_map name')
            label = raw_name.split(b'\0',1)[0].decode('ascii','strict')
        if out and prev != out[-1]['link_map']: raise ValueError('link_map back pointer')
        out.append({'link_map':ptr, 'name':label, 'bias':addr})
        ptr = next_ptr
    return out


def one_module(rows, name):
    matches = [r for r in rows if r['name'] == name]
    if len(matches) != 1 or matches[0]['bias'] <= 0 or matches[0]['bias'] & 4095:
        raise ValueError('missing/ambiguous link_map ' + name)
    return matches[0]


def symbol_vas(path):
    """Bounded ELF64 dynsym parser; reads the actual bridge, not tool text output."""
    b = Path(path).read_bytes()
    if b[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', b, 18)[0] != 183:
        raise ValueError('bridge ELF')
    shoff = struct.unpack_from('<Q', b, 40)[0]
    entsize, count = struct.unpack_from('<HH', b, 58)
    if entsize != 64 or count > 128 or shoff + count*64 > len(b): raise ValueError('bridge SHDR')
    wanted = {f'fx6diag_slot_{i:02d}' for i in range(57)} | {
        'fx6diag_mpr_init','fx6diag_mpr_enterrec','fx6diag_failstop',
        'fx6diag_call_original','fx6diag_mapped_record','fx6diag_state',
        'fx6diag_fail_reason','fx6diag_original_return','fx6diag_verified_original_init'}
    found = {}
    for i in range(count):
        sh = shoff+i*64
        typ = struct.unpack_from('<I', b, sh+4)[0]
        if typ != 11: continue
        off, size = struct.unpack_from('<QQ', b, sh+24)
        link = struct.unpack_from('<I', b, sh+40)[0]
        stride = struct.unpack_from('<Q', b, sh+56)[0]
        if link >= count or stride != 24 or off+size > len(b): raise ValueError('bridge dynsym bounds')
        strsh = shoff+link*64
        so, ss = struct.unpack_from('<QQ',b,strsh+24)
        if so+ss > len(b): raise ValueError('bridge dynstr bounds')
        strings = b[so:so+ss]
        for p in range(off,off+size,24):
            ix = struct.unpack_from('<I',b,p)[0]
            if ix >= len(strings): continue
            end = strings.find(b'\0',ix)
            if end < 0: continue
            name = strings[ix:end].decode('ascii')
            if name in wanted:
                if name in found: raise ValueError('duplicate bridge symbol '+name)
                found[name] = struct.unpack_from('<Q',b,p+8)[0]
    if set(found) != wanted or len(set(found[n] for n in found if n.startswith('fx6diag_slot_'))) != 57:
        raise ValueError('bridge symbol set/uniqueness')
    return found


class Probe(previous.Probe):
    """IM -> AP call gate -> all thunk Z1 -> original call -> bounded stop."""
    def __init__(self, run, qmp, mapping):
        super().__init__(run,qmp,mapping)
        self.bridge_symbols=symbol_vas(BRIDGE)
        self.bridge_bias=None
        self.mpr_bias=None
        self.gate_installed=False
        self.thunk_hits=[]
        self.hit_budget=8
        self.call_vcpu=None;self.call_tls=None;self.call_fp=None
    def save(self):
        (self.run/'guest-veneer-observation.json').write_text(json.dumps({
            'stage':self.stage,'mapping':self.mapping,'records':self.records,
            'gate_installed':self.gate_installed,
            'breakpoints_still_installed':[hex(x) for x in sorted(self.breakpoints)],
            'resume_acks':self.resume_acks,'qmp_statuses':self.qmp_statuses,
            'policy':'only Z1/z1, addressless c, stopped-only read; no guest writes or auto continue on faults',
        },indent=2)+'\n')
    def _record(self,kind,stop,tid,regs,extra=None):
        tls=self.sysregs.read('TPIDR_EL0')
        row={'kind':kind,'stop':stop,'vCPU_observed_not_guest_tid':tid,'pc':hex(regs[32]),
             'x0_x7':[hex(x) for x in regs[:8]],'sp':hex(regs[31]),
             'fp':hex(regs[29]),'lr':hex(regs[30]),'tls':hex(tls)}
        if extra:row.update(extra)
        self.records.append(row);self.save()
        return row
    def _stop_context(self,stop):
        if self.qmp.call('query-status').get('status') != 'debug':
            raise ValueError('RSP/QMP stop mismatch')
        tid=self.rsp.select_thread(stop)
        regs=self.rsp.regs()
        return tid,regs
    def _check_bridge(self,bias,vas):
        result=read_current_identity(self.rsp,bias,BRIDGE,vas)
        for i in range(57):
            pc=bias+self.bridge_symbols[f'fx6diag_slot_{i:02d}']
            expected=0xd4200000|((0x600+i)<<5)
            if int.from_bytes(self.read(pc,4),'little')!=expected:
                raise ValueError('bridge thunk first instruction '+str(i))
        return result
    def _arm_gate(self,stop,tid,regs):
        pc=regs[32]
        if pc != self.ap_call or self.read(pc,4).hex()!=previous.WORDS[('ap',AP_CALL)]:
            raise ValueError('AP Init callsite mismatch')
        ap_identity=self.identity('ap',self.mapping['ap']['bias'])
        raw=self.read_span(regs[0],0x290)
        if regs[0] != regs[29]+0x20 or regs[0]&15:
            raise ValueError('AP source record address')
        rows=read_link_map(self.rsp,self.mapping['im']['bias'])
        bridge=one_module(rows,BRIDGE_PATH)
        mpr=one_module(rows,'/usr/lib/libmpr.so')
        self.bridge_bias=bridge['bias'];self.mpr_bias=mpr['bias']
        s=self.bridge_symbols
        bridge_identity=self._check_bridge(self.bridge_bias,
             [s['fx6diag_mpr_init'],s['fx6diag_slot_00'],s['fx6diag_slot_56'],
              s['fx6diag_mpr_enterrec'],s['fx6diag_call_original']+8])
        mpr_identity=read_current_identity(self.rsp,self.mpr_bias,MPR,
                                            [previous.MPR_INIT,FIRST_CONSUMER])
        # All possible callback entries are armed before AP's BL executes.
        # A rejected Z1 leaves the VM stopped: no original Sony Init is called.
        stops=[self.bridge_bias+s[f'fx6diag_slot_{i:02d}'] for i in range(57)]
        stops += [self.bridge_bias+s['fx6diag_mpr_enterrec'],
                  self.bridge_bias+s['fx6diag_failstop'],
                  self.bridge_bias+s['fx6diag_call_original']+8,
                  self.mpr_bias+previous.MPR_INIT,
                  self.mpr_bias+FIRST_CONSUMER,
                  self.ap_return]
        if len(stops)!=len(set(stops)):raise ValueError('gate address collision')
        for address in stops:self.add(address)
        self._record('precall_gate',stop,tid,regs,{
            'source_sha256':hashlib.sha256(raw).hexdigest(),
            'source_0x290_hex':raw.hex(),'ap_identity':ap_identity,
            'bridge_identity':bridge_identity,'mpr_identity':mpr_identity,
            'link_map':rows,'z1_count':len(stops),
            'callback_z1_count':57})
        self.call_vcpu=tid;self.call_tls=self.sysregs.read('TPIDR_EL0');self.call_fp=regs[29]
        self.gate_installed=True;self.remove(self.ap_call)
        self.stage='await_guest_bridge';self.save();self.resume()
    def process_stop(self,stop,serial):
        if self.stage=='await_type4_record':
            return super().process_stop(stop,serial)
        if self.stage=='await_ap_dlsym_return':
            tid,regs=self._stop_context(stop)
            self.qmp_statuses.append({'stage':self.stage,'status':'debug','rsp_stop':stop})
            pc=regs[32]
            tls=self.sysregs.read('TPIDR_EL0')
            record_equal=self.dispatch is not None and regs[22]==self.dispatch['record']
            tls_equal=self.dispatch is not None and hex(tls)==self.dispatch['tls']
            row=self._record('im_dlsym_return_gate',stop,tid,regs,{
                'record_x22':hex(regs[22]),
                'expected_record':None if self.dispatch is None else hex(self.dispatch['record']),
                'record_equal':record_equal,'tls_equal':tls_equal,
                'dispatch_vcpu':None if self.dispatch is None else self.dispatch['tid'],
                'vcpu_migrated':self.dispatch is not None and tid!=self.dispatch['tid']})
            if pc!=self.im_dlsym_return:
                row['reject_reasons']=['wrong_pc'];self.stage='unknown_loader_return';self.save();return True
            word=self.read(pc,4).hex();row['word_le']=word
            if word!=previous.WORDS[('im',previous.DLSYM_RETURN)]:
                row['reject_reasons']=['wrong_im_word'];self.stage='unknown_loader_return';self.save();return True
            if not record_equal or not tls_equal:
                row['reject_reasons']=[reason for okay,reason in ((record_equal,'record_x22_mismatch'),
                    (tls_equal,'TLS_mismatch')) if not okay]
                self.stage='unknown_loader_return';self.save();return True
            bias=regs[0]-previous.AP_ENTRY
            if bias<=0 or bias&4095:raise ValueError('AP entry cannot yield aligned base')
            identity=self.identity('ap',bias)
            self.mapping['ap']={'bias':bias,'source':'same IM record+x22 and TLS; current CPU AP ELF/PHDR/code'}
            self.ap_call=bias+AP_CALL;self.ap_return=bias+AP_RETURN
            row.update({'status':'accepted_same_record_TLS',
                'same_TLS_record_cross_vcpu_allowed':True,'ap_entry':hex(regs[0]),
                'ap_bias':hex(bias),'current_ap_identity':identity})
            self.add(self.ap_call);self.remove(self.im_dlsym_return)
            self.stage='await_mpr_call';self.save();self.resume();return False
        if len(self.records) >= self.hit_budget:raise ValueError('observer hit budget')
        tid,regs=self._stop_context(stop)
        pc=regs[32]
        if self.stage=='await_mpr_call':
            self._arm_gate(stop,tid,regs)
            return False
        if not self.gate_installed:raise ValueError('bridge callback gate absent')
        b=self.bridge_bias;s=self.bridge_symbols
        thunk={b+s[f'fx6diag_slot_{i:02d}']:i for i in range(57)}
        if pc in thunk:
            i=thunk[pc]
            if self.read(pc,4)!=struct.pack('<I',0xd4200000|((0x600+i)<<5)):
                raise ValueError('thunk instruction changed')
            self._check_bridge(b,[s[f'fx6diag_slot_{i:02d}']])
            self._record('unknown_callback_nonreturning',stop,tid,regs,{'slot':i})
            self.stage='unknown_callback_captured';self.save();return True
        if pc==b+s['fx6diag_mpr_enterrec']:
            self._check_bridge(b,[s['fx6diag_mpr_enterrec']])
            self._record('enterrec_blocked',stop,tid,regs)
            self.stage='enterrec_blocked';self.save();return True
        if pc==b+s['fx6diag_failstop']:
            self._check_bridge(b,[s['fx6diag_failstop']])
            reason=int.from_bytes(self.read(b+s['fx6diag_fail_reason'],4),'little')
            self._record('bridge_failstop',stop,tid,regs,{'reason':reason})
            self.stage='bridge_failstop';self.save();return True
        if pc==self.mpr_bias+FIRST_CONSUMER:
            read_current_identity(self.rsp,self.mpr_bias,MPR,[FIRST_CONSUMER])
            self._record('writer_first_threshold_consumer',stop,tid,regs)
            self.stage='writer_threshold_before_record_gate';self.save();return True
        if pc==b+s['fx6diag_call_original']+8:
            read_current_identity(self.rsp,b,BRIDGE,[s['fx6diag_call_original']+8])
            if self.sysregs.read('TPIDR_EL0')!=self.call_tls:
                raise ValueError('original call TLS mismatch')
            target=b+s['fx6diag_mapped_record']
            state=int.from_bytes(self.read(b+s['fx6diag_state'],4),'little')
            if not (state==3 and regs[0]==target and regs[1]==self.mpr_bias+previous.MPR_INIT):
                raise ValueError('bridge original Init entry contract')
            mapped=self.read_span(target,0x1f8)
            self._record('original_init_preinvoke',stop,tid,regs,{
                'mapped_sha256':hashlib.sha256(mapped).hexdigest(),'mapped_hex':mapped.hex(),
                'state':state,'original_init':hex(regs[1])})
            self.remove(pc);self.stage='await_sony_entry';self.save();self.resume();return False
        if pc==self.mpr_bias+previous.MPR_INIT:
            read_current_identity(self.rsp,self.mpr_bias,MPR,[previous.MPR_INIT])
            if self.stage!='await_sony_entry':raise ValueError('MPR Init without bridge BLR')
            if self.sysregs.read('TPIDR_EL0')!=self.call_tls:
                raise ValueError('Sony Init TLS mismatch')
            if regs[0]!=b+s['fx6diag_mapped_record'] or regs[30]!=b+s['fx6diag_call_original']+12:
                raise ValueError('Sony Init parameter/BLR return-chain mismatch')
            self._record('original_init_entry',stop,tid,regs,
                         {'caller_vcpu':self.call_vcpu,'same_TLS_different_vcpu_allowed':True})
            self.remove(pc);self.stage='await_return_or_stop';self.save();self.resume();return False
        if pc==self.ap_return:
            self.identity('ap',self.mapping['ap']['bias'])
            if self.sysregs.read('TPIDR_EL0')!=self.call_tls or regs[29]!=self.call_fp:
                raise ValueError('AP return frame/TLS mismatch')
            state=int.from_bytes(self.read(b+s['fx6diag_state'],4),'little')
            returned=int.from_bytes(self.read(b+s['fx6diag_original_return'],4),'little',signed=True)
            w0=regs[0]&0xffffffff
            if w0>=1<<31:w0-=1<<32
            self._record('ap_same_call_return',stop,tid,regs,{
                'state':state,'original_return_memory':returned,'w0_signed32':w0,
                'caller_vcpu':self.call_vcpu,'same_TLS_frame_different_vcpu_allowed':True})
            self.stage='ap_return_captured' if state==4 and returned==w0 else 'return_mismatch'
            self.save();return True
        raise ValueError('unknown stopped PC '+hex(pc))
