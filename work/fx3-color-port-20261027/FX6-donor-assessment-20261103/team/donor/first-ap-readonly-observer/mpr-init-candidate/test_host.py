#!/usr/bin/env python3
"""No-QEMU bounded MPR observer tests; synthetic values never runtime claims."""
import json
import struct
import subprocess
from pathlib import Path
import mpr_probe as m
from readonly_probe import elf_loads, sha

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'runs/ap-ro-8548d224/serial.log'
checks=[]
def check(name,fn):fn();checks.append(name)

def early_pre_ap_mapping():
    b=OLD.read_bytes();x=m.choose_early_im(b)
    assert x['pid']==237 and x['snapshot_kind']=='early_complete'
    assert x['snapshot_byte_range'][1]<b.find(b'FX3_AP_IM_PROCESS=')
    assert x['im']['bias']==0 and x['ap'] is None and x['mpr'] is None
    cut=b[:x['snapshot_byte_range'][1]-4]
    # An earlier completed block can still be selected; the truncated last
    # block alone is not falsely declared complete.
    assert not any(y['complete'] and y['byte_end']==x['snapshot_byte_range'][1]
                   for y in m.parse_maps(cut))
    assert m.choose_early_im(b'FX3_AP_EARLY_MAPS_237_1_BEGIN\n00400000-00409000 r-xp 00000000 00:02 3331 /usr/bin/im.elf\n') is None
check('early_complete_IM_map_before_late_AP_and_truncation',early_pre_ap_mapping)

def source_words_and_relocation():
    assert sha(m.IM_ELF)=='87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec'
    assert sha(m.AP_ELF)=='a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067'
    assert sha(m.MPR_ELF)==m.MPR_SHA
    for (name,va),word in m.WORDS.items():
        path={'im':m.IM_ELF,'ap':m.AP_ELF,'mpr':m.MPR_ELF}[name]
        segs=[x for x in elf_loads(path) if x['va']<=va and va+4<=x['va']+x['filesz']]
        assert len(segs)==1
        off=segs[0]['fileoff']+va-segs[0]['va']
        with path.open('rb') as f:f.seek(off);assert f.read(4).hex()==word
    with m.AP_ELF.open('rb') as f:
        f.seek(0x212f7b8);assert f.read(4).hex()=='429fa797'
    # Decode the original BL immediate and cross-check the real ELF RELA,
    # instead of treating a symbol-name string as a resolved binding.
    with m.AP_ELF.open('rb') as f:f.seek(m.CALL);word=int.from_bytes(f.read(4),'little')
    imm=word&0x3ffffff
    if imm&(1<<25):imm-=1<<26
    assert m.CALL+4*imm==0xb174c0
    with m.AP_ELF.open('rb') as f:
        f.seek(0xb174c0);assert f.read(8).hex()=='d01e01d011b641f9'
    rela=subprocess.check_output(['objdump','-R',str(m.AP_ELF)],text=True)
    assert '0000000002ef1368 R_AARCH64_JUMP_SLOT      _ZN3mpr4InitERKNS_11initInParamE' in rela
check('pinned_original_IM_AP_MPR_words_and_import',source_words_and_relocation)

class SyntheticImage:
    def __init__(self,wrong_im=False,callback_bad=False):
        self.bias={'im':0,'ap':0x7ecd5bf000,'mpr':0x7ed4719000}
        self.files={k:p.read_bytes() for k,p in [('im',m.IM_ELF),('ap',m.AP_ELF),('mpr',m.MPR_ELF)]}
        self.paths={'im':m.IM_ELF,'ap':m.AP_ELF,'mpr':m.MPR_ELF}
        self.loads={k:elf_loads(p) for k,p in self.paths.items()}
        self.record=0x7e00000000;self.pathptr=self.record+0x100;self.symptr=self.record+0x200
        self.fp=0x7e10000000;self.param=self.fp+0x20
        self.got=self.bias['mpr']+m.MPR_INIT
        self.raw=bytearray(0x290)
        cb=self.bias['ap']+m.CALLBACK+(8 if callback_bad else 0)
        struct.pack_into('<Q',self.raw,0x1d0,cb)
        struct.pack_into('<I',self.raw,0x268,2)
        struct.pack_into('<H',self.raw,0x1f2,0x1234)
        struct.pack_into('<H',self.raw,0x28a,0x30c)
        self.record_raw=struct.pack('<4I2Q',0x20000004,1,0xffffff9f,0x83,self.pathptr,self.symptr)
        self.wrong_im=wrong_im;self.commands=[];self.at='dispatch'
    def command(self,x):self.commands.append(x);return 'OK'
    def send_continue(self):self.commands.append('c');return {'command':'c','ack':'+'}
    def select_thread(self,stop):assert stop=='T05thread:01;';return '01'
    def regs(self):
        x=[0]*33
        if self.at=='dispatch':x[0]=self.record;x[29]=0x7e20000000;x[32]=m.DISPATCH
        elif self.at=='dlsym':x[0]=self.bias['ap']+m.AP_ENTRY;x[22]=self.record;x[29]=0x7e20000100;x[32]=m.DLSYM_RETURN
        elif self.at=='call':x[0]=self.param;x[29]=self.fp;x[32]=self.bias['ap']+m.CALL
        elif self.at=='mpr_entry':x[0]=self.param;x[29]=self.fp;x[32]=self.bias['mpr']+m.MPR_INIT
        elif self.at=='capid':x[29]=self.fp;x[32]=self.bias['mpr']+m.CAPID_INIT
        else:x[0]=3;x[29]=self.fp;x[32]=self.bias['ap']+m.RETURN
        return tuple(x)
    def virtual_read(self,addr,n):
        assert 0<n<=64
        regions={self.record:self.record_raw,self.pathptr:b'appFw.so\0'+bytes(50),
                 self.symptr:b'Application_System_Init\0'+bytes(50),
                 self.param:bytes(self.raw),self.bias['ap']+m.GOT:struct.pack('<Q',self.got)}
        for start,data in regions.items():
            if start<=addr and addr+n<=start+len(data):return data[addr-start:addr-start+n]
        for name,bias in self.bias.items():
            va=addr-bias
            for seg in self.loads[name]:
                if seg['va']<=va and va+n<=seg['va']+seg['filesz']:
                    off=seg['fileoff']+va-seg['va'];raw=self.files[name][off:off+n]
                    if self.wrong_im and name=='im' and va==0x400000:raw=bytes([raw[0]^1])+raw[1:]
                    return raw
        raise ValueError('synthetic unmapped '+hex(addr))

class Q:
    def call(self,name):assert name=='query-status';return {'status':'debug'}
class S:
    def read(self,name):assert name=='TPIDR_EL0';return 0x7e30000000

def state_machine_original_bytes():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        image=SyntheticImage()
        o=m.Probe(Path(d),Q(),m.choose_early_im(OLD.read_bytes()))
        o.rsp=image;o.sysregs=S();o.stage='await_type4_record';o.breakpoints={o.im_dispatch}
        for at in ('dispatch','dlsym','call','mpr_entry','capid','return'):
            image.at=at
            done=o.process_stop('T05thread:01;',b'')
            assert done==(at=='return'),at
        assert [x['kind'] for x in o.records]==['dispatch','dlsym_return','call','mpr_entry','capid','return']
        assert o.records[2]['callback_plus_1d0']==hex(image.bias['ap']+m.CALLBACK)
        assert o.records[2]['count_plus_268']==2
        assert o.records[2]['u16_fx3_reads_plus_1f2']==0x1234
        assert o.records[2]['u16_fx6_source_plus_28a']==0x30c
        assert o.records[2]['mpr_identity_before'] is not None
        assert o.records[-1]['mpr_identity_after'] is not None
        assert o.records[-1]['return_w0_signed32']==3
        assert o.records[-1]['mpr_entry_observed'] and o.records[-1]['capid_init_observed_if_armed']
        assert o.remove_all()['all_removed']
        assert all(x['command']=='c' for x in o.resume_acks)
check('synthetic_only_full_state_machine_original_image_reads_and_fields',state_machine_original_bytes)

def reject_wrong_im_or_callback():
    import tempfile
    for wrong_im,bad_cb in [(True,False),(False,True)]:
        with tempfile.TemporaryDirectory() as d:
            image=SyntheticImage(wrong_im,bad_cb)
            o=m.Probe(Path(d),Q(),m.choose_early_im(OLD.read_bytes()))
            o.rsp=image;o.sysregs=S();o.stage='await_type4_record';o.breakpoints={o.im_dispatch}
            image.at='dispatch'
            if wrong_im:
                try:o.process_stop('T05thread:01;',b'')
                except ValueError as e:assert 'current IM ELF/PHDR mismatch' in str(e)
                else:raise AssertionError('wrong current IM ELF accepted')
            else:
                assert not o.process_stop('T05thread:01;',b'')
                image.at='dlsym';assert not o.process_stop('T05thread:01;',b'')
                image.at='call';assert o.process_stop('T05thread:01;',b'')
                assert o.stage=='unknown_call' and o.records[-1]['status']=='callback_identity_mismatch'
            assert o.remove_all()['all_removed']
check('wrong_current_IM_ELF_and_callback_rejected',reject_wrong_im_or_callback)

def early_return_without_capid():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        image=SyntheticImage();o=m.Probe(Path(d),Q(),m.choose_early_im(OLD.read_bytes()))
        o.rsp=image;o.sysregs=S();o.stage='await_type4_record';o.breakpoints={o.im_dispatch}
        for at in ('dispatch','dlsym','call','mpr_entry','return'):
            image.at=at;done=o.process_stop('T05thread:01;',b'')
            assert done==(at=='return')
        row=o.records[-1]
        assert row['return_w0_signed32']==3 and row['mpr_entry_observed']
        assert row['capid_breakpoint_armed'] and not row['capid_init_observed_if_armed']
        assert o.remove_all()['all_removed']
check('synthetic_MPR_entry_then_early_return_CAPID_armed_not_hit',early_return_without_capid)

def lazy_got_then_bound_on_return():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        image=SyntheticImage();image.got=image.bias['ap']+0xb174c0
        o=m.Probe(Path(d),Q(),m.choose_early_im(OLD.read_bytes()))
        o.rsp=image;o.sysregs=S();o.stage='await_type4_record';o.breakpoints={o.im_dispatch}
        for at in ('dispatch','dlsym','call'):
            image.at=at;assert not o.process_stop('T05thread:01;',b'')
        assert o.records[-1]['mpr_identity_before'] is None
        assert o.capid_pc is None and o.stage=='await_return'
        image.got=image.bias['mpr']+m.MPR_INIT
        image.at='return';assert o.process_stop('T05thread:01;',b'')
        row=o.records[-1]
        assert row['mpr_identity_after'] is not None and not row['mpr_entry_observed']
        assert not row['capid_breakpoint_armed'] and not row['capid_init_observed_if_armed']
        assert o.remove_all()['all_removed']
check('synthetic_lazy_GOT_before_resolved_after_CAPID_coverage_unknown',lazy_got_then_bound_on_return)

(HERE/'host-tests.json').write_text(json.dumps({'status':'PASS_NO_QEMU','cases':checks,
    'historical_serial_sha256':sha(OLD),'im_sha256':sha(m.IM_ELF),
    'ap_sha256':sha(m.AP_ELF),'mpr_sha256':sha(m.MPR_ELF),
    'mpr_probe_sha256':sha(HERE/'mpr_probe.py'),
    'identity_sha256':sha(HERE.parent/'two_phase_identity.py'),
    'runner_sha256':sha(HERE/'run_mpr_once.py'),
    'test_host_sha256':sha(__file__)},indent=2)+'\n')
print(json.dumps({'status':'PASS_NO_QEMU','cases':checks},indent=2))
