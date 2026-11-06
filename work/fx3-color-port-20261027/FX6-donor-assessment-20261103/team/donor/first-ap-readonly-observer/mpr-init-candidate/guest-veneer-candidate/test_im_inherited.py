#!/usr/bin/env python3
"""Replay the real 03->02/TLS fields through inherited dispatch then new dlsym gate.

The old run did not serialize dlsym x22; that register is an explicit synthetic
positive/negative fixture, never claimed as a historical observation.
"""
import hashlib
import json
import struct
import tempfile
from pathlib import Path

import guest_probe as gp

HERE=Path(__file__).resolve().parent
RUN=HERE/'runs/guest-veneer-33d090b1'
OBS_SHA='79f834a71e671d7a9c9e0285c46930ae61c29a52db5f4e8339d93ebf5d354801'
old=RUN/'guest-veneer-observation.json'
assert hashlib.sha256(old.read_bytes()).hexdigest()==OBS_SHA
rows=json.loads(old.read_text())['records']
assert [r['kind'] for r in rows]==['dispatch','dlsym_return']
assert rows[0]['vCPU']=='03' and rows[1]['vCPU']=='02'
assert rows[0]['tls']==rows[1]['tls']=='0x7f837ff740'
assert rows[0]['record_words']==['0x20000004','0x1','0xffffff9f','0x83']
assert rows[0]['path']=='appFw.so' and rows[0]['symbol']=='Application_System_Init'
assert rows[1]['status']=='not_same_im_record_tls'
RECORD=int(rows[0]['record'],16);TLS=int(rows[0]['tls'],16)
AP_BASE=0x7ee1e78000  # synthetic only; current run had not reached AP-base gate.

class Image:
    def __init__(self,x22=None,tls=TLS,bad_ap=False,bad_im=False):
        self.at='dispatch';self.x22=RECORD if x22 is None else x22
        self.tls=tls;self.bad_ap=bad_ap;self.bad_im=bad_im
        self.bias={'im':0,'ap':AP_BASE}
        self.files={'im':gp.IM.read_bytes(),'ap':gp.BRIDGE.parent.joinpath('appFw-bridge.so').read_bytes()}
        self.loads={'im':gp.previous.elf_loads(gp.IM),'ap':gp.previous.elf_loads(HERE/'appFw-bridge.so')}
        self.pathptr=RECORD+0x100;self.symptr=RECORD+0x180
        self.regions={RECORD:struct.pack('<4I2Q',0x20000004,1,0xffffff9f,0x83,self.pathptr,self.symptr),
            self.pathptr:b'appFw.so\0'+bytes(63),
            self.symptr:b'Application_System_Init\0'+bytes(63)}
        self.commands=[]
    def command(self,cmd):self.commands.append(cmd);return 'OK'
    def send_continue(self):self.commands.append('c');return {'command':'c','ack':'+'}
    def select_thread(self,stop):return '03' if self.at=='dispatch' else '02'
    def regs(self):
        r=[0]*33
        if self.at=='dispatch':r[0]=RECORD;r[32]=gp.previous.DISPATCH
        else:r[0]=AP_BASE+gp.previous.AP_ENTRY;r[22]=self.x22;r[32]=gp.previous.DLSYM_RETURN
        return tuple(r)
    def virtual_read(self,addr,n):
        for start,data in self.regions.items():
            if start<=addr and addr+n<=start+len(data):return data[addr-start:addr-start+n]
        for name,bias in self.bias.items():
            va=addr-bias
            for seg in self.loads[name]:
                if seg['va']<=va and va+n<=seg['va']+seg['filesz']:
                    off=seg['fileoff']+va-seg['va'];v=self.files[name][off:off+n]
                    if self.bad_im and name=='im' and va==0x400000:v=bytes([v[0]^1])+v[1:]
                    if self.bad_ap and name=='ap' and va==0:v=bytes([v[0]^1])+v[1:]
                    return v
        raise ValueError('synthetic unmapped '+hex(addr))

class Q:
    def call(self,name):assert name=='query-status';return {'status':'debug'}

class Sys:
    def __init__(self,image):self.image=image
    def read(self,name):assert name=='TPIDR_EL0';return self.image.tls

def run_one(cls,**kwargs):
    dlsym_tls=kwargs.pop('dlsym_tls',None)
    image=Image(**kwargs)
    with tempfile.TemporaryDirectory(prefix='im-gate-test-',dir=HERE) as d:
        probe=cls(Path(d),Q(),{'im':{'bias':0}})
        probe.rsp=image;probe.sysregs=Sys(image)
        probe.stage='await_type4_record';probe.breakpoints={probe.im_dispatch}
        try:
            first=probe.process_stop('T05thread:03;',b'')
        except ValueError:
            if kwargs.get('bad_im'):return 'wrong_IM_ELF_rejected'
            raise
        assert first is False and probe.stage=='await_ap_dlsym_return'
        image.at='dlsym'
        if dlsym_tls is not None:image.tls=dlsym_tls
        try:second=probe.process_stop('T05thread:02;',b'')
        except ValueError:
            if kwargs.get('bad_ap'):return 'wrong_AP_ELF_rejected'
            raise
        return probe,second

oldprobe,stopped=run_one(gp.previous.Probe)
assert stopped and oldprobe.stage=='unknown_loader_return'
newprobe,stopped=run_one(gp.Probe)
assert not stopped and newprobe.stage=='await_mpr_call'
gate=newprobe.records[-1]
assert gate['record_equal'] and gate['tls_equal'] and gate['vcpu_migrated']
assert gate['record_x22']==hex(RECORD) and gate['expected_record']==hex(RECORD)
assert gate['current_ap_identity']['machine']=='AArch64'
for kwargs,reason in (({'x22':RECORD+8},'record_x22_mismatch'),
                      ({'dlsym_tls':TLS+8},'TLS_mismatch')):
    p,stop=run_one(gp.Probe,**kwargs)
    assert stop and p.stage=='unknown_loader_return'
    assert p.records[-1]['reject_reasons']==[reason]
assert run_one(gp.Probe,bad_im=True)=='wrong_IM_ELF_rejected'
assert run_one(gp.Probe,bad_ap=True)=='wrong_AP_ELF_rejected'
result={'status':'PASS_NO_QEMU','real_run_observation_sha256':OBS_SHA,
    'real_fields':{'dispatch_vcpu':'03','dlsym_vcpu':'02','tls':hex(TLS),
                   'dispatch_record':hex(RECORD),'dlsym_x22':'NOT_CAPTURED'},
    'synthetic_assumption':'dlsym x22 equals dispatch record only in positive fixture',
    'cases':['old_inherited_gate_rejects_vcpu_migration',
             'new_inherited_dispatch_then_dlsym_accepts_same_record_TLS_cross_vcpu',
             'new_record_mismatch_rejected','new_TLS_mismatch_rejected',
             'wrong_current_IM_ELF_rejected','wrong_current_AP_ELF_rejected']}
print(json.dumps(result,indent=2))
