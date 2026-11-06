#!/usr/bin/env python3
"""Original diagnostic early-return paths and native matcher, conditional RAM.

Initialized guard/category bits are declared guest-only fixtures; mute bit is
written by the original setter. No logger constructor, OS formatter/backend,
host logging stub, fake return, camera, remote, or persistent operation.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage58-native-match-call-frame'))
import match_call_frame as prev
r,im,V,n,p=prev.r,prev.im,prev.V,prev.n,prev.p
LOG=V+0xba676c
GUARD=V+0xbceed1
MUTE=LOG+0x1908
CAT1=LOG+0x1804+2*8
CAT2=LOG+0x186c+2*8
PRIOR_SHA='4aa48521bba72709b6ed74c16ba744d4d5c038df9bd50fbfb254fff0490d0490'
EXTRA=[(0x225ee0,0x225fa0),(0x27d528,0x27d7bc),(0x27d898,0x27d8a8),
  (0x27dcf0,0x27dd88),(0x27debc,0x27df04)]


def bounded_cstring(m,at):
    assert V<=at<V+len(m.blob)
    raw=m.read(at,min(128,V+len(m.blob)-at));end=raw.find(b'\0');assert end>=0
    return raw[:end].decode('ascii')


class Guest(prev.Guest):
    def __init__(self,*assets):
        super().__init__(*assets)
        self.ranges.extend((V+a,V+z) for a,z in EXTRA)
        self.boundaries.pop(V+0x27d528,None)
        self.boundaries.update({prev.SITE+8:'after_actual_matcher_return_before_caller_diagnostic',
          V+0x27d024:'before_unexecuted_logger_constructor',
          V+0x27d7d0:'before_unexecuted_diagnostic_formatter'})
        self.log_calls=[];self.getter_returns=[];self.setter_stores=[];self.format_args=[]

    def code(self,u,pc,size,user):
        if pc==V+0x27d564:
            self.getter_returns.append({'return_pc':hex(pc),'actual_X0':hex(u.reg_read(r.reg.UC_ARM64_REG_X0))})
        if pc==V+0x27d568:
            sp=u.reg_read(r.reg.UC_ARM64_REG_SP)
            values=list(struct.unpack('<10Q',self.read(sp,80)))
            row={'entry':hex(pc),'SP':hex(sp),'arguments_x0_x7':[
              hex(u.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))) for i in range(8)],
              'overflow_10words':[hex(x) for x in values],
              'format':bounded_cstring(self,values[0]),
              'original_literal_args':{str(i):bounded_cstring(self,values[i]) for i in (1,2,3,4,8,9)},
              'scalar_raw1c_width_height':values[5:8]}
            self.log_calls.append(row)
        if pc==V+0x27d7d0:
            self.format_args.append({'entry':hex(pc),'arguments_x0_x6':[
              hex(u.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))) for i in range(7)],
              'SP':hex(u.reg_read(r.reg.UC_ARM64_REG_SP))})
        return super().code(u,pc,size,user)

    def store(self,u,access,address,size,value,user):
        if address==MUTE and size==1:
            pc=u.reg_read(r.reg.UC_ARM64_REG_PC)
            assert pc==V+0x27d8a0
            self.setter_stores.append({'pc':hex(pc),'address':hex(address),'size':size,'value':value&255})
            return
        return super().store(u,access,address,size,value,user)


def phase(m,label,start,**regs):
    e=prev.phase(m,label,start,**regs)
    global LAST_PHASE
    LAST_PHASE=e
    return e


def linked(assets,initialized,mute,enabled):
    m=Guest(*assets);load=n.link(m)
    m.uc.mem_write(prev.SITE,m.patch)
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    # Explicit initialized/header/category fixtures, NOT a global constructor
    # or observation of device logging settings. Only MUTE can be guest-written.
    for at in (GUARD,MUTE,CAT1,CAT2):assert m.blob[at-V]==0
    expected={GUARD:int(initialized),MUTE:0,CAT1:int(enabled),CAT2:int(enabled)}
    for at,value in expected.items():m.uc.mem_write(at,bytes([value]))
    page=MUTE&~4095;m.uc.mem_protect(page,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    events=[load]
    if initialized:
        e=phase(m,'original logger mute setter on declared initialized object',0x27d898,x0=LOG,x1=mute)
        assert e['reason']=='returned';events.append(e)
        assert m.setter_stores==[{'pc':hex(V+0x27d8a0),'address':hex(MUTE),'size':1,'value':mute}]
        expected[MUTE]=mute
    m.expected_data=expected
    return m,events


def assert_image(m):
    raw=bytearray(m.read(V,len(m.blob)))
    assert raw[:0x1ec]==m.blob[:0x1ec]
    assert raw[0x1ec:0x884]==m.read(n.MDATA,0x698)
    raw[0x1ec:0x884]=m.blob[0x1ec:0x884]
    assert raw[prev.SITE-V:prev.SITE-V+4]==m.patch
    raw[prev.SITE-V:prev.SITE-V+4]=m.blob[prev.SITE-V:prev.SITE-V+4]
    for at,value in m.expected_data.items():
        assert raw[at-V]==value;raw[at-V]=m.blob[at-V]
    assert raw==m.blob
    assert m.read(prev.BRIDGE,len(m.code_bytes))==m.code_bytes and m.read(prev.CONST,len(m.ro_bytes))==m.ro_bytes


def prepare(m,events,descriptor,seed):
    m.uc.mem_write(p.HANDLER,bytes(0xe520))
    e=phase(m,'complete original common constructor',0x21d9e0,x0=p.COMMON)
    assert e['reason']=='returned';events.append(e)
    m.uc.mem_write(p.CTX,bytes(0x57000));m.uc.mem_write(p.CTX+0x108,struct.pack('<I',1))
    m.uc.mem_write(p.CTX+0x118,r.p64(p.MESSAGE));m.uc.mem_write(p.FACTORY+0x55ec8,struct.pack('<I',1))
    m.uc.mem_write(p.FACTORY+0x55ed8,r.p64(p.HANDLER));m.uc.mem_write(p.FACTORY+8,struct.pack('<I',1))
    m.uc.mem_write(p.FACTORY+0x14,bytes(4));tree=p.FACTORY+0x55f10
    m.uc.mem_write(tree+0x120,struct.pack('<I',1));m.uc.mem_write(tree+0x130,r.p64(p.NODE))
    m.uc.mem_write(p.MESSAGE,bytes(0xc0));m.uc.mem_write(p.MESSAGE+8,r.p64(p.IDENTITY))
    m.uc.mem_write(p.IDENTITY,struct.pack('<I',p.UID));m.uc.mem_write(p.MESSAGE+0x20,descriptor)
    m.uc.mem_write(r.SP-0x2000,bytes([seed])*0x3000)


def case(assets,label,descriptor,seed,mute,enabled,initialized,expected):
    m,events=linked(assets,initialized,mute,enabled);prepare(m,events,descriptor,seed)
    e=phase(m,'contiguous queued Open wrapper real diagnostic and matcher '+label,0x22f34c,x0=p.CTX)
    events.append(e)
    assert len(m.bridge_entries)==len(m.real_match_entries)==1
    bridge=m.bridge_entries[0];entered=m.real_match_entries[0]
    source=int(bridge['source'],16);arg=int(entered['input_pointer'],16)
    raw=m.read(source,152);view=m.read(arg,152)
    assert raw[:136]==descriptor and m.read(p.COMMON+0xe110,136)==descriptor
    if label=='uninitialized logger guard control':
        assert e['reason']=='boundary: before_unexecuted_logger_constructor'
        assert not m.real_returns and not m.log_calls
    elif label=='enabled formatting boundary control':
        assert e['reason']=='boundary: before_unexecuted_diagnostic_formatter'
        assert not m.real_returns and len(m.log_calls)==len(m.format_args)==1
        assert hex(V+0x27d66c) in e['pcs'] and m.clear_calls
    else:
        assert e['reason']=='boundary: after_actual_matcher_return_before_caller_diagnostic'
        assert m.real_returns==[{'pc':hex(prev.SITE+4),'W0':expected&0xffffffff,'SP':bridge['SP']}]
        assert (m.uc.reg_read(r.reg.UC_ARM64_REG_X23)&0xffffffff)==expected&0xffffffff
        assert len(m.log_calls)==1 and not m.format_args
        assert hex(V+0x27d624) in e['pcs']
    if initialized:
        assert m.getter_returns==[{'return_pc':hex(V+0x27d564),'actual_X0':hex(LOG)}]
    if m.log_calls:
        log=m.log_calls[0];values=[int(x,16) for x in log['overflow_10words']]
        assert log['arguments_x0_x7'][0]==hex(LOG)
        assert values[5:8]==[struct.unpack_from('<I',view,0x1c)[0],*struct.unpack_from('<2H',view,8)]
        # These are the actual scalars/literal arguments at this call, not an
        # all-diagnostic/global pointer-escape analysis.
        assert arg not in values and source not in values
        assert hex(arg) not in log['arguments_x0_x7'] and hex(source) not in log['arguments_x0_x7']
    assert_image(m)
    return {'label':label,'state':{'initialized_guard_fixture':initialized,
      'original_setter_mute':mute if initialized else None,'category2_flags_fixture':enabled,
      'original_global_constructor_or_actual_camera_state':False},
      'source98_hex':raw.hex(),'matcher_input98_hex':view.hex(),'wrapper_entry':bridge,
      'real_matcher_entry':entered,'actual_return_to_original_caller':m.real_returns,
      'expected_row_if_returned':expected,'native_logger_getter_returns':m.getter_returns,
      'native_log_calls':m.log_calls,'native_formatter_entry_boundary':m.format_args,
      'original_mute_setter_stores':m.setter_stores,'events':events,
      'one_contiguous_original_queued_to_matcher_return':bool(m.real_returns),
      'independent_post_diagnostic_copy_or_PC_return_adapter':False,
      'observed_diagnostic_args_do_not_include_matcher_input_pointer':bool(m.log_calls),
      'all_diagnostic_global_pointer_non_escape_or_actual_logger_state_proven':False}


def run(out):
    prior=prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for row in json.loads(prior.read_text())['files']:assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    obj=prev.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o'
    code,ro,relocs=prev.object_image(obj.read_bytes())
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    kernel=(n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    assets=(blob,module,kernel,code,ro);inp=p.inputs()
    cases=[case(assets,'target muted priorA5',inp[0][1],0xa5,1,False,True,386),
      case(assets,'target muted priorC3',inp[0][1],0xc3,1,False,True,386),
      case(assets,'target category-disabled control',inp[0][1],0xc3,0,False,True,386),
      case(assets,'artificial FF muted control',inp[1][1],0xc3,1,False,True,386),
      case(assets,'proxy FH muted control',inp[2][1],0xc3,1,False,True,-1),
      case(assets,'stock UHD muted control',inp[3][1],0xc3,1,False,True,431),
      case(assets,'enabled formatting boundary control',inp[0][1],0xc3,0,True,True,None),
      case(assets,'uninitialized logger guard control',inp[0][1],0xc3,0,False,False,None)]
    regions=[('native getter incl lazy constructor and guard',0x27d528,0x27d568),
      ('native vararg wrapper',0x27d568,0x27d5c8),('native diagnostic early gates',0x27d5c8,0x27d64c),
      ('native original output preparation',0x27d64c,0x27d6ac),('native mute setter',0x27d898,0x27d8a8),
      ('original matcher diagnostic arguments',0x225ee0,0x225fa0)]
    proof={'status':'PASS_CONTIGUOUS_NATIVE_MATCHER_WITH_DECLARED_DIAGNOSTIC_GATES',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'bounded_fragments':sum(len(c['events']) for c in cases),
      'actual_contiguous_matcher_returns':sum(bool(c['actual_return_to_original_caller']) for c in cases),
      'wrapper_object_source':str(obj.relative_to(ROOT)),'wrapper_object_sha256':im.sha(obj.read_bytes()),
      'cases':cases,'original_regions':[{'name':name,'instructions':im.dump(blob,a,z,V)} for name,a,z in regions],
      'scope':{'one_guest_only_BL_and_explicit_logger_global_state_changes':True,
        'original_firmware_file_and_other_guest_bytes_unchanged':True,
        'mute_set_by_original_function_not_synthesized_log_return':True,
        'initialized_guard_and_category_flags_are_fixtures_not_camera_observation':True,
        'full_original_matcher_native_continuity_only_on_observed_early_return_states':True,
        'full_enabled_logger_constructor_formatter_output_and_global_pointer_escape':False,
        'actual_loader_MMU_shared_lock_owner_epoch_Open_Start_Hal_recording_recovery':False,
        'UU_Windows_camera_protocol_auth_modes_drivers_files_modules_WBI_flash':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(out/'diagnostic-gates-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(module),'kernel_sha256':im.sha(kernel),
      'wrapper_object_sha256':im.sha(obj.read_bytes()),'previous_manifest_sha256':PRIOR_SHA,
      'volume_uuid':im.VOLUME})
    print(json.dumps({'status':proof['status'],'bounded_fragments':proof['bounded_fragments'],
      'contiguous_returns':proof['actual_contiguous_matcher_returns'],'goal_complete':False}))


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
