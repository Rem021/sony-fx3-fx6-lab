#!/usr/bin/env python3
"""Original queued Open through native row selection to channel boundary.

Explicit initialized/muted logger, queue and backing-storage fixtures remain.
No camera I/O, fake diagnostic/allocator return or real hardware claim. The
private writer is an independent guest call, not an installed Sony hook.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage60-native-diagnostic-format'))
import diagnostic_format as last
prev=last.prev
r,im,V,n,p=prev.r,prev.im,prev.V,prev.n,prev.p
old=prev.prev.prev
PRIOR_SHA='66718b9145726ad88c382a339ac4629b7727823e5a7bb53e1a28641a4b564114'
EXTRA=[(0x21ed24,0x21efc4),(0x22a60c,0x22a638),
       (0x21dd54,0x21e26c),(0x27b988,0x27b9a8)]


class Guest(prev.Guest):
    def __init__(self,*assets):
        blob,module,kernel,code,ro,wcode,wro,functions=assets
        super().__init__(blob,module,kernel,code,ro)
        self.ranges.extend((V+a,V+z) for a,z in EXTRA)
        self.boundaries.pop(prev.prev.SITE+8)
        self.boundaries[V+0x21dd54]='before_original_buffer_channel_preparation'
        self.boundaries[V+0x21efc4]='before_original_no_resource_row_error'
        self.boundaries[V+0x22d394]='before_unexecuted_channel_acquisition'
        self.all_logs=[];self.rows=[];self.channel_entries=[]
        self.functions=functions;self.prototype_stores=[];self.prototype_limits=None
        self.uc.mem_map(old.CODE,0x10000,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
        self.uc.mem_map(old.RODATA,4096,r.unicorn.UC_PROT_READ)
        self.uc.mem_write(old.CODE,wcode);self.uc.mem_write(old.RODATA,wro)
        self.ranges.append((old.CODE,old.CODE+len(wcode)))
        self.writer_code=wcode;self.writer_ro=wro

    def code(self,u,pc,size,user):
        if pc==V+0x27d568:
            sp=u.reg_read(r.reg.UC_ARM64_REG_SP)
            fmt=struct.unpack('<Q',self.read(sp,8))[0]
            self.all_logs.append({'pc':hex(pc),'SP':hex(sp),
              'LR':hex(u.reg_read(r.reg.UC_ARM64_REG_LR)),
              'format':prev.bounded_cstring(self,fmt),
              'x0_x7':[hex(u.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))) for i in range(8)],
              'spill80_hex':self.read(sp,80).hex()})
            # stage59's specialized decoder describes ONLY the first matcher
            # diagnostic. Later original calls have other argument signatures.
            if len(self.all_logs)>1:
                return prev.prev.Guest.code(self,u,pc,size,user)
        if pc==V+0x21ed44:
            self.rows.append({'pc':hex(pc),'row':hex(u.reg_read(r.reg.UC_ARM64_REG_X26)),
              'preset_id':hex(u.reg_read(r.reg.UC_ARM64_REG_X22))})
        if pc==V+0x22d394:
            self.channel_entries.append({'pc':hex(pc),'LR':hex(u.reg_read(r.reg.UC_ARM64_REG_LR)),
              'SP':hex(u.reg_read(r.reg.UC_ARM64_REG_SP)),
              'x0_x4':[hex(u.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))) for i in range(5)],
              'body_executed':False,'acquisition_return_adapter':False})
        return super().code(u,pc,size,user)

    def store(self,u,access,address,size,value,user):
        pc=u.reg_read(r.reg.UC_ARM64_REG_PC)
        if old.CODE<=pc<old.CODE+len(self.writer_code):
            assert self.prototype_limits is not None
            assert any(a<=address and address+size<=a+length for a,length in self.prototype_limits)
            self.prototype_stores.append({'pc':hex(pc),'address':hex(address),'size':size})
        return super().store(u,access,address,size,value,user)


def phase(m,label,start,**regs):
    global LAST_PHASE
    e=prev.phase(m,label,start,**regs);LAST_PHASE=e
    return e


def linked(assets):
    m=Guest(*assets);events=[n.link(m)]
    m.uc.mem_write(prev.prev.SITE,m.patch)
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    m.expected_data={prev.GUARD:1,prev.MUTE:0,prev.CAT1:1,prev.CAT2:1}
    for at,value in m.expected_data.items():
        assert m.blob[at-V]==0;m.uc.mem_write(at,bytes([value]))
    m.uc.mem_protect(prev.MUTE&~4095,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    e=phase(m,'original mute setter1 on declared initialized/category-enabled logger',0x27d898,
      x0=prev.LOG,x1=1)
    assert e['reason']=='returned';events.append(e);m.expected_data[prev.MUTE]=1
    return m,events


def one_case(assets,label,descriptor,seed,expected,writer):
    m,events=linked(assets);prev.prepare(m,events,descriptor,seed)
    e=phase(m,'contiguous queued Open through real matcher diagnostics and native row preparation '+label,
      0x22f34c,x0=p.CTX)
    events.append(e)
    assert len(m.real_returns)==1 and m.real_returns[0]['W0']==expected&0xffffffff
    source=int(m.bridge_entries[0]['source'],16);raw=m.read(source,152)
    assert raw[:136]==descriptor and m.read(p.COMMON+0xe110,136)==descriptor
    if expected==-1:
        assert e['reason']=='boundary: before_original_no_resource_row_error'
        assert not m.rows and not m.channel_entries and len(m.all_logs)==1
        selected=None;channel=None;private=None
    else:
        assert e['reason']=='boundary: before_original_buffer_channel_preparation',e['reason']
        assert m.rows[0]['row']==hex(V+0x395108+expected*0x90)
        assert len(m.all_logs)==3 and not m.format_args
        selected=struct.unpack('<Q',m.read(p.COMMON+0xe000,8))[0]
        preset=struct.unpack('<I',m.read(p.COMMON+0xe470,4))[0]
        assert preset==int(m.rows[0]['preset_id'],16)
        channel={'entry_pc':hex(V+0x21dd54),
          'x0_x3':[hex(m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))) for i in range(4)],
          'preset_pointer':hex(selected),'preset_id':hex(preset)}
        before_regs=p.captured_regs(m)
        m.boundaries.pop(V+0x21dd54)
        # Resume EXACTLY the paused PC, registers, stack and memory. Only trace
        # state is reset. No independent post-diagnostic guest or supplied row.
        assert m.uc.reg_read(r.reg.UC_ARM64_REG_PC)==V+0x21dd54
        assert p.captured_regs(m)==before_regs
        e2=phase(m,'same guest untouched continuation through original channel sizing '+label,
          0x21dd54,independent=False)
        events.append(e2)
        assert e2['reason']=='boundary: before_unexecuted_channel_acquisition',e2['reason']
        assert len(m.channel_entries)==1 and len(m.all_logs)==4 and not m.format_args
        assert m.read(source,152)==raw and m.read(p.COMMON+0xe110,136)==descriptor
        channel['acquisition']=m.channel_entries[0]
        assert int(channel['acquisition']['x0_x4'][4],16)==p.COMMON+0x1060
        private=None
        if writer:
            assert expected==386 and selected==V+0x3c5798 and preset==0x19450
            # Independent writer/query calls AFTER the channel boundary. Their
            # control/session/epoch/backing storage are declared host fixtures;
            # no claim they were called from the original Sony request path.
            events.append(old.default_query(m,'original selected query on continuous row state',24498176))
            old.init_control(m)
            w=old.prototype(m,'independent compiled exact-FH private preset publication',
              'fx3_candidate',[old.CONTROL,0,0,0,old.EPOCH,old.SESSION])
            events.append(w);assert w['status']==0
            events.append(old.default_query(m,'original query on independently published private16M',16000000))
            copy=m.read(old.COPY,256);original=m.blob[0x3c5798:0x3c5898]
            assert [i for i,(a,b) in enumerate(zip(original,copy)) if a!=b]==[0xb0,0xb1,0xb2]
            assert m.read(p.COMMON+0xe000,8)==r.p64(old.COPY)
            assert m.read(p.COMMON+0xe110,136)==descriptor
            private={'status':w['status'],'query_before':24498176,'query_after':16000000,
              'actual_native_callsite_hook_installed':False,'independent_guest_call':True,
              'control':old.control(m)}
    prev.assert_image(m)
    assert m.read(old.CODE,len(m.writer_code))==m.writer_code
    assert m.read(old.RODATA,len(m.writer_ro))==m.writer_ro
    return {'label':label,'seed':seed,'native_row':expected,'source98_hex':raw.hex(),
      'source_and_common_remain_original_descriptor':True,'native_rows':m.rows,
      'actual_native_matcher_returns':m.real_returns,'original_diagnostic_calls':m.all_logs,
      'original_channel_preparation':channel,'independent_private_writer':private,
      'events':events,'same_guest_no_post_log_copy_or_return_adapter':True,
      'real_logger_state_constructor_channel_provider_Hal_recording_or_recovery':False}


def run(out):
    prior=last.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for row in json.loads(prior.read_text())['files']:
        assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    obj=prev.prev.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o'
    code,ro,_=prev.prev.object_image(obj.read_bytes())
    wobj=old.STAGE/'run-bounded-stores-20261026/resource_alias.a64.o'
    assert any(row['path']==str(wobj.relative_to(ROOT)) and row['sha256']==im.sha(wobj.read_bytes())
      for row in json.loads((old.STAGE/'final-receipt.json').read_text())['files'])
    wcode,wro,functions,_=old.object_image(wobj.read_bytes())
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    kernel=(n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    assets=blob,module,kernel,code,ro,wcode,wro,functions
    inp=p.inputs()
    cases=[one_case(assets,'target FH priorA5',inp[0][1],0xa5,386,True),
      one_case(assets,'target FH priorC3',inp[0][1],0xc3,386,True),
      one_case(assets,'artificial FF control',inp[1][1],0xc3,386,False),
      one_case(assets,'stock UHD control',inp[3][1],0xc3,431,False),
      one_case(assets,'proxy FH no-row control',inp[2][1],0xc3,-1,False)]
    proof={'status':'PASS_CONTIGUOUS_NATIVE_ROW_AND_CHANNEL_BOUNDARY',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'bounded_fragments':sum(len(c['events']) for c in cases),'cases':cases,
      'original_regions':[{'start':hex(a),'end':hex(z),'instructions':im.dump(blob,a,z,V)}
        for a,z in EXTRA],
      'scope':{'original_native_logs_return_only_under_declared_mute_state':True,
        'channel_acquisition_body_or_hardware_not_executed':True,
        'independent_private_writer_is_not_installed_hook':True,
        'UU_Windows_camera_protocol_auth_modes_drivers_files_modules_WBI_flash':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(out/'row-channel-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(module),'kernel_sha256':im.sha(kernel),
      'match_wrapper_object_sha256':im.sha(obj.read_bytes()),'writer_object_sha256':im.sha(wobj.read_bytes()),
      'previous_manifest_sha256':PRIOR_SHA,'volume_uuid':im.VOLUME})
    print(json.dumps({'status':proof['status'],'bounded_fragments':proof['bounded_fragments'],
      'native_rows':[c['native_row'] for c in cases],'goal_complete':False}))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True)
    args=ap.parse_args();im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        if 'LAST_PHASE' in globals():im.write_json(out/'last-phase-at-failure.json',LAST_PHASE)
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        raise


if __name__=='__main__':main()
