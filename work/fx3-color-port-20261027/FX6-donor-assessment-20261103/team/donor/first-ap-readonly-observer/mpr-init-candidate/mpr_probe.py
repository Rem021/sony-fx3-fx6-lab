#!/usr/bin/env python3
"""Host-only candidate: early IM record -> AP base -> same-call MPR Init."""
import json
import hashlib
import struct
import sys
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
sys.path.insert(0,str(PARENT))
from readonly_probe import RSP, elf_loads, map_bias, parse_maps
from two_phase_identity import read_current_identity

DONOR=PARENT.parent
MAC=PARENT.parents[5]
IM_ELF=DONOR/'nflasha15-files/bin/im.elf'
AP_ELF=DONOR/'nflasha15-files/lib/appFw.so'
MPR_ELF=MAC/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so'
MPR_SHA='9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c'
DISPATCH=0x406284; DLSYM_RETURN=0x405f10; AP_ENTRY=0xc0b044
CALL=0x212f7b8; RETURN=0x212f7bc; MPR_INIT=0xb6844; CAPID_INIT=0x13250c
GOT=0x2ef1368; CALLBACK=0x213bde0
WORDS={('im',DISPATCH):'e8feff97',('im',DLSYM_RETURN):'f40300aa',
       ('ap',CALL):'429fa797',('ap',RETURN):'f35341a9',
       ('mpr',MPR_INIT):'fd7bb2a9',('mpr',CAPID_INIT):'fd7bbca9'}

def choose_early_im(serial,im_elf=IM_ELF):
    """Pre-AP complete /init maps: independent IM ELF PT_LOAD identity."""
    for block in reversed(parse_maps(serial)):
        if block['kind']!='early' or not block['complete']:continue
        try:im=map_bias(block['rows'],b'/usr/bin/im.elf',elf_loads(im_elf))
        except ValueError:continue
        return {'pid':block['pid'],'snapshot_kind':'early_complete',
                'snapshot_byte_range':[block['byte_start'],block['byte_end']],'im':im,
                'ap':None,'mpr':None}
    return None

class Probe:
    def __init__(self,run,qmp,mapping):
        self.run=run;self.qmp=qmp;self.mapping=mapping;self.rsp=None;self.sysregs=None
        self.stage='unarmed';self.breakpoints=set();self.records=[];self.resume_acks=[]
        self.qmp_statuses=[];self.last_qmp_check=0.0;self.dispatch=None;self.call=None
        self.im_dispatch=mapping['im']['bias']+DISPATCH
        self.im_dlsym_return=mapping['im']['bias']+DLSYM_RETURN
        self.ap_call=None;self.ap_return=None;self.mpr_entry_pc=None;self.capid_pc=None
    def save(self):
        (self.run/'mpr-observation.json').write_text(json.dumps({
            'stage':self.stage,'mapping':self.mapping,'records':self.records,
            'breakpoints_still_installed':[hex(x) for x in sorted(self.breakpoints)],
            'resume_acks':self.resume_acks,'qmp_statuses':self.qmp_statuses,
            'policy':'Z1/z1 and addressless c, stopped-only g/p/m/XML; no guest writes, step, keys',
        },indent=2)+'\n')
    def resume(self):
        self.resume_acks.append({'stage':self.stage,**self.rsp.send_continue()});self.save()
    def check_qmp_without_rsp(self):
        now=time.monotonic()
        if now-self.last_qmp_check<.25:return None
        self.last_qmp_check=now
        status=self.qmp.call('query-status').get('status')
        if not self.qmp_statuses or status!=self.qmp_statuses[-1]['status']:
            self.qmp_statuses.append({'stage':self.stage,'status':status});self.save()
        if status=='running':return None
        event=self.rsp.poll_stop(.5)
        if event:return event
        self.stage='qmp_'+str(status)+'_without_rsp_stop';self.save()
        raise RuntimeError('QMP '+str(status)+' without RSP stop')
    def arm(self):
        self.qmp.call('stop')
        status=self.qmp.call('query-status').get('status')
        if status!='paused':raise RuntimeError('QMP did not pause all CPUs')
        self.qmp_statuses.append({'stage':'arm','status':status})
        self.rsp=RSP.connect(self.run)
        if self.rsp.command('Qqemu.PhyMemMode:1')!='OK' or self.rsp.command('qqemu.PhyMemMode')!='1':
            raise RuntimeError('RSP physical baseline failed')
        from gdb_sysregs104_v2 import Sysregs
        self.sysregs=Sysregs(self.rsp,self.run)
        self.add(self.im_dispatch)
        self.stage='await_type4_record';self.save()
        while True:
            initial=self.rsp.poll_stop(0)
            if initial is None:break
            if not initial.startswith(('T02','S02')):raise RuntimeError('unexpected initial stop '+initial)
        while self.rsp.stops:
            stale=self.rsp.stops.popleft()
            if not stale.startswith(('T02','S02')):raise RuntimeError('unexpected queued stop '+stale)
        self.resume()
    def add(self,addr):
        if self.rsp.command(f'Z1,{addr:x},4')!='OK':raise RuntimeError('Z1 rejected '+hex(addr))
        self.breakpoints.add(addr)
    def remove(self,addr):
        if self.rsp.command(f'z1,{addr:x},4')!='OK':raise RuntimeError('z1 rejected '+hex(addr))
        self.breakpoints.remove(addr)
    def read(self,addr,n):return self.rsp.virtual_read(addr,n)
    def read_span(self,addr,n):return b''.join(self.read(addr+i,min(64,n-i)) for i in range(0,n,64))
    def cstr(self,addr,size=40):return self.read(addr,size).split(b'\0',1)[0]
    def identity(self,origin,bias):
        if origin=='im':
            # ET_EXEC maps its file header at p_vaddr=0x400000, not VA zero.
            loads=elf_loads(IM_ELF)
            first=min(loads,key=lambda x:x['fileoff'])
            if first['fileoff']!=0:raise ValueError('IM ELF header not in first PT_LOAD')
            with IM_ELF.open('rb') as f:
                head=f.read(64);phoff=struct.unpack_from('<Q',head,32)[0]
                entsize,count=struct.unpack_from('<HH',head,54)
                if head[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',head,18)[0]!=183 or entsize!=56 or not 0<count<=64 or phoff+count*entsize>8192:
                    raise ValueError('IM ELF/PHDR invalid')
                f.seek(phoff);phdr=f.read(count*entsize)
                words=[]
                for va in [DISPATCH,DLSYM_RETURN,0x405eac,0x405f44]:
                    segs=[x for x in loads if x['va']<=va and va+4<=x['va']+x['filesz']]
                    if len(segs)!=1:raise ValueError('IM code VA not uniquely mapped')
                    off=segs[0]['fileoff']+va-segs[0]['va'];f.seek(off);word=f.read(4)
                    if self.read(bias+va,4)!=word:raise ValueError('current IM code mismatch '+hex(va))
                    words.append({'va':hex(va),'file_offset':hex(off),'word_le':word.hex()})
            header_va=bias+first['va']
            if self.read_span(header_va,64)!=head or self.read_span(header_va+phoff,len(phdr))!=phdr:
                raise ValueError('current IM ELF/PHDR mismatch')
            return {'bias':hex(bias),'header_va':hex(header_va),'machine':'AArch64',
                    'elf_header_sha256':hashlib.sha256(head).hexdigest(),
                    'program_headers_sha256':hashlib.sha256(phdr).hexdigest(),
                    'original_code_words':words}
        if origin=='ap':return read_current_identity(self.rsp,bias,AP_ELF,[AP_ENTRY,0x212f488,CALL,RETURN,0xb174c0,0xb174c4])
        return read_current_identity(self.rsp,bias,MPR_ELF,[MPR_INIT,0xb6870,0xb6874,0xb6878,CAPID_INIT])
    def _mpr_from_got(self,got):
        bias=got-MPR_INIT
        if bias<=0 or bias&0xfff:return None
        try:identity=self.identity('mpr',bias)
        except Exception:return None
        return {'bias':bias,'identity':identity,'method':'GOT target minus original MPR Init VA; current CPU ELF/PHDR/words'}
    def process_stop(self,stop,_serial):
        if len(self.records)>=6:raise RuntimeError('hit budget exceeded')
        status=self.qmp.call('query-status').get('status')
        self.qmp_statuses.append({'stage':self.stage,'status':status,'rsp_stop':stop});self.save()
        if status!='debug':raise RuntimeError('RSP/QMP stop mismatch')
        tid=self.rsp.select_thread(stop);regs=self.rsp.regs();pc=regs[32]
        expected={'await_type4_record':{self.im_dispatch:'dispatch'},
                  'await_ap_dlsym_return':{self.im_dlsym_return:'dlsym_return'},
                  'await_mpr_call':{self.ap_call:'call'},
                  'await_mpr_entry_or_return':{self.mpr_entry_pc:'mpr_entry',self.ap_return:'return'},
                  'await_capid_or_return':{self.capid_pc:'capid',self.ap_return:'return'},
                  'await_return':{self.ap_return:'return'}}
        kind=expected.get(self.stage,{}).get(pc)
        if not kind:raise ValueError('unknown breakpoint PC '+hex(pc))
        origin='mpr' if kind in ('mpr_entry','capid') else ('im' if kind in ('dispatch','dlsym_return') else 'ap')
        va={'dispatch':DISPATCH,'dlsym_return':DLSYM_RETURN,'call':CALL,
            'mpr_entry':MPR_INIT,'capid':CAPID_INIT,'return':RETURN}[kind]
        word=WORDS[(origin,va)]
        if self.read(pc,4).hex()!=word:raise ValueError('original PC word mismatch '+hex(pc))
        tls=hex(self.sysregs.read('TPIDR_EL0'))
        row={'kind':kind,'vCPU':tid,'stop':stop,'pc':hex(pc),'va':hex(va),
             'word_le':word,'x0':hex(regs[0]),'fp':hex(regs[29]),'tls':tls}
        if kind=='dispatch':
            row['current_im_identity']=self.identity('im',self.mapping['im']['bias'])
            record=regs[0];raw=self.read(record,0x20)
            words=struct.unpack_from('<4I',raw)
            pathptr,symptr=struct.unpack_from('<2Q',raw,0x10)
            row.update({'record':hex(record),'record_words':[hex(x) for x in words],
                        'path':self.cstr(pathptr).decode('ascii','replace'),
                        'symbol':self.cstr(symptr).decode('ascii','replace')})
            if words!=(0x20000004,1,0xffffff9f,0x83) or row['path']!='appFw.so' or row['symbol']!='Application_System_Init':
                row['status']='unexpected_type4_record';self.records.append(row)
                self.stage='unknown_record';self.save();return True
            self.dispatch={'record':record,'tid':tid,'tls':tls}
            self.records.append(row);self.add(self.im_dlsym_return);self.remove(self.im_dispatch)
            self.stage='await_ap_dlsym_return';self.save();self.resume();return False
        if kind=='dlsym_return':
            if self.dispatch is None or regs[22]!=self.dispatch['record'] or tid!=self.dispatch['tid'] or tls!=self.dispatch['tls']:
                row['status']='not_same_im_record_tls';self.records.append(row)
                self.stage='unknown_loader_return';self.save();return True
            bias=regs[0]-AP_ENTRY
            if bias<=0 or bias&0xfff:raise ValueError('AP entry pointer cannot yield page-aligned bias')
            row['ap_entry']=hex(regs[0]);row['ap_bias']=hex(bias)
            row['current_ap_identity']=self.identity('ap',bias)
            self.mapping['ap']={'bias':bias,'source':'same-record IM dlsym return plus current CPU ELF/PHDR/code'}
            self.ap_call=bias+CALL;self.ap_return=bias+RETURN
            self.records.append(row);self.add(self.ap_call);self.remove(self.im_dlsym_return)
            self.stage='await_mpr_call';self.save();self.resume();return False
        if kind=='call':
            row['current_ap_identity']=self.identity('ap',self.mapping['ap']['bias'])
            if regs[0]!=regs[29]+0x20 or regs[0]&15:
                row['status']='not_original_stack_record';self.records.append(row)
                self.stage='unknown_call';self.save();return True
            param=regs[0];raw=self.read_span(param,0x290)
            callback=int.from_bytes(raw[0x1d0:0x1d8],'little')
            got=int.from_bytes(self.read(self.mapping['ap']['bias']+GOT,8),'little')
            mpr=self._mpr_from_got(got)
            row.update({'parameter':hex(param),'parameter_0x290_sha256':__import__('hashlib').sha256(raw).hexdigest(),
                        'parameter_0x290_hex':raw.hex(),'callback_plus_1d0':hex(callback),
                        'callback_expected':hex(self.mapping['ap']['bias']+CALLBACK),
                        'count_plus_268':int.from_bytes(raw[0x268:0x26c],'little'),
                        'u16_fx3_reads_plus_1f2':int.from_bytes(raw[0x1f2:0x1f4],'little'),
                        'u16_fx6_source_plus_28a':int.from_bytes(raw[0x28a:0x28c],'little'),
                        'got_slot':hex(self.mapping['ap']['bias']+GOT),'got_before':hex(got),
                        'mpr_identity_before':mpr})
            if callback!=self.mapping['ap']['bias']+CALLBACK:
                row['status']='callback_identity_mismatch';self.records.append(row)
                self.stage='unknown_call';self.save();return True
            self.call={'tid':tid,'tls':tls,'fp':regs[29],'param':param,
                       'mpr_entry_observed':False,'capid_observed':False}
            self.records.append(row)
            self.add(self.ap_return)
            if mpr:
                self.mapping['mpr']=mpr
                self.mpr_entry_pc=mpr['bias']+MPR_INIT;self.add(self.mpr_entry_pc)
            self.remove(self.ap_call)
            self.stage='await_mpr_entry_or_return' if self.mpr_entry_pc else 'await_return'
            self.save();self.resume();return False
        if self.call is None or tid!=self.call['tid'] or tls!=self.call['tls']:
            row['status']='wrong_same_call_thread_tls';self.records.append(row)
            self.stage='unknown_followup';self.save();return True
        if kind=='mpr_entry':
            row['current_mpr_identity']=self.identity('mpr',self.mapping['mpr']['bias'])
            if regs[0]!=self.call['param']:
                row['status']='wrong_mpr_entry_parameter';self.records.append(row)
                self.stage='unknown_mpr_entry';self.save();return True
            row['status']='exact_MPR_Init_entry_same_tls_and_parameter'
            self.call['mpr_entry_observed']=True;self.records.append(row)
            self.remove(self.mpr_entry_pc)
            self.capid_pc=self.mapping['mpr']['bias']+CAPID_INIT;self.add(self.capid_pc)
            self.stage='await_capid_or_return';self.save();self.resume();return False
        if kind=='capid':
            row['current_mpr_identity']=self.identity('mpr',self.mapping['mpr']['bias'])
            row['status']='exact_MPR_CAPID_Init_entry_same_tls';self.call['capid_observed']=True
            self.records.append(row);self.remove(self.capid_pc)
            self.stage='await_return';self.save();self.resume();return False
        row['current_ap_identity']=self.identity('ap',self.mapping['ap']['bias'])
        if regs[29]!=self.call['fp']:
            row['status']='wrong_same_call_frame';self.records.append(row)
            self.stage='unknown_return';self.save();return True
        got=int.from_bytes(self.read(self.mapping['ap']['bias']+GOT,8),'little')
        mpr=self._mpr_from_got(got)
        row.update({'got_after':hex(got),'mpr_identity_after':mpr,
                    'return_w0_signed32':int.from_bytes(regs[0].to_bytes(8,'little')[:4],'little',signed=True),
                    'mpr_entry_observed':self.call['mpr_entry_observed'],
                    'capid_init_observed_if_armed':self.call['capid_observed'],
                    'capid_breakpoint_armed':self.capid_pc is not None,
                    'same_parameter':hex(self.call['param'])})
        row['status']='same_call_return; MPR binding proven only if current mpr_identity_after present'
        self.records.append(row);self.stage='mpr_same_call_return_captured';self.save();return True
    def remove_all(self):
        if not self.rsp:return {'attempted':False,'all_removed':True}
        results=[]
        for addr in sorted(self.breakpoints):
            try:reply=self.rsp.command(f'z1,{addr:x},4')
            except Exception as exc:reply=repr(exc)
            results.append({'address':hex(addr),'reply':reply})
            if reply=='OK':self.breakpoints.remove(addr)
        self.stage+=';cleanup';self.save()
        return {'attempted':True,'results':results,'all_removed':not self.breakpoints,
                'unremoved':[hex(x) for x in sorted(self.breakpoints)]}
