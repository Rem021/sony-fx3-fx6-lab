#!/usr/bin/env python3
"""Original enabled diagnostic to unmapped timer boundary, then independent CRT.

No timer/MMIO result is invented. Independent formatter inputs use actual
native-produced format/va_list bytes and original file-backed CRT context.
Never substitutes host formatting or declares the real logger/device complete.
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
sys.path.insert(0,str(BASE/'stage59-native-diagnostic-gates'))
import diagnostic_gates as prev
r,im,V,n,p=prev.r,prev.im,prev.V,prev.n,prev.p
OUT=r.ARENA+0x3c0000
PRIOR_SHA='3cab80234f8292be7bb1abd5558efc94e7716b2eae0486973908aa475871f5e1'
EXTRA=[(0x27d7d0,0x27d898),(0x27d32c,0x27d3a0),
  (0x2a4588,0x2a45fc),(0x29f6c8,0x29f6dc),
  (0x126a8,0x126dc),(0x125c0,0x126a4),(0x17040,0x1a5ec),
  (0x2e340,0x2e360),(0x1d3f8,0x1d404),(0x12c0,0x1400),
  (0x17028,0x17040),(0x11e68,0x12268),(0x16eb0,0x17028)]


class Guest(prev.Guest):
    def __init__(self,*assets):
        super().__init__(*assets)
        self.ranges.extend((V+a,V+z) for a,z in EXTRA)
        self.boundaries.pop(V+0x27d7d0,None)
        self.boundaries[V+0x29f6d4]='before_original_unmapped_timer_MMIO_read'
        self.mmio_boundary=[]

    def code(self,u,pc,size,user):
        if pc==V+0x29f6d4:
            offset=u.reg_read(r.reg.UC_ARM64_REG_X8)
            base=u.reg_read(r.reg.UC_ARM64_REG_X9)
            self.mmio_boundary.append({'pc':hex(pc),'base_X9':hex(base),'offset_X8':hex(offset),
              'effective_address':hex((base+offset)&((1<<64)-1)),
              'load_instruction_executed':False,'register_or_MMIO_return_adapter':False})
        return super().code(u,pc,size,user)


def phase(m,label,start,**regs):
    e=prev.phase(m,label,start,**regs)
    global LAST_PHASE
    LAST_PHASE=e
    return e


def linked(assets):
    m=Guest(*assets);events=[n.link(m)]
    m.uc.mem_write(prev.prev.SITE,m.patch)
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    m.expected_data={prev.GUARD:1,prev.MUTE:0,prev.CAT1:1,prev.CAT2:1}
    for at,value in m.expected_data.items():
        assert m.blob[at-V]==0;m.uc.mem_write(at,bytes([value]))
    m.uc.mem_protect(prev.MUTE&~4095,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    e=phase(m,'original mute setter0 on explicit initialized/category-enabled fixture',0x27d898,x0=prev.LOG,x1=0)
    assert e['reason']=='returned';events.append(e)
    return m,events


def expected_text(log):
    # Reference comparison only; this text is NEVER written into guest output.
    words=[int(x,16) for x in log['overflow_10words']]
    strings=log['original_literal_args'];numbers=[x&0xffffffff for x in words[5:8]]
    args=[strings[str(i)] for i in (1,2,3,4)]+numbers+[strings[str(i)] for i in (8,9)]
    return (log['format']%tuple(args)).encode('ascii')


def one_case(assets,seed,limit):
    m,events=linked(assets);descriptor=p.inputs()[0][1]
    prev.prepare(m,events,descriptor,seed)
    e=phase(m,'contiguous enabled diagnostic to original timestamp MMIO boundary',0x22f34c,x0=p.CTX)
    events.append(e)
    assert e['reason']=='boundary: before_original_unmapped_timer_MMIO_read'
    assert len(m.mmio_boundary)==len(m.log_calls)==len(m.format_args)==1
    assert not m.real_returns
    timer=m.mmio_boundary[0];assert timer['effective_address']=='0xfffffffff3402108'
    assert timer['base_X9']=='0xfffffffff3400000' and timer['offset_X8']=='0x2108'
    assert not any(a<=int(timer['effective_address'],16)<=z for a,z,_ in m.uc.mem_regions())
    prefix_pcs=e['pcs'];assert hex(V+0x27d7d0) in prefix_pcs and hex(V+0x2a459c) in prefix_pcs
    native_format=m.format_args[0];log=m.log_calls[0]
    format_ptr=int(native_format['arguments_x0_x6'][4],16)
    va_ptr=int(native_format['arguments_x0_x6'][5],16)
    assert format_ptr==int(log['overflow_10words'][0],16)
    va_raw=m.read(va_ptr,32);stack,gr,vr,g_off,v_off=struct.unpack('<3Q2i',va_raw)
    assert g_off==0 and v_off==-128
    assert m.read(stack,72)==struct.pack('<9Q',*[int(x,16) for x in log['overflow_10words'][1:]])
    source=int(m.bridge_entries[0]['source'],16);arg=int(m.real_match_entries[0]['input_pointer'],16)
    source_before=m.read(source,152);arg_before=m.read(arg,152);va_before=m.read(stack,72)
    # A wholly independent original CRT call. Use another stack area so this
    # test cannot overwrite the original suspended diagnostic's va_list/slots.
    m.uc.mem_write(OUT,bytes([0x5a])*256)
    e2=phase(m,'independent original built-in bounded formatting of real native varargs',0x126a8,
      sp=r.STACK+0x3000,x0=OUT,x1=limit,x2=format_ptr,x3=va_ptr)
    events.append(e2)
    assert e2['reason']=='returned',e2['reason']
    text=expected_text(log);output=m.read(OUT,256)
    scalar=m.uc.reg_read(r.reg.UC_ARM64_REG_X0)&0xffffffff
    assert scalar==len(text),(scalar,len(text))
    if limit:
        keep=min(len(text),limit-1)
        assert output[:keep+1]==text[:keep]+b'\0'
        assert output[keep+1:]==bytes([0x5a])*(255-keep)
    else:assert output==bytes([0x5a])*256
    assert m.read(source,152)==source_before and m.read(arg,152)==arg_before
    assert m.read(va_ptr,32)==va_raw and m.read(stack,72)==va_before
    prev.assert_image(m)
    return {'seed':seed,'independent_output_limit':limit,'timer_boundary':timer,
      'native_formatter_arguments':native_format,'native_log':log,
      'native_va_list':{'pointer':hex(va_ptr),'raw32_hex':va_raw.hex(),'stack':hex(stack),
        'gr_top_unconsumed_with_gr_offs0':hex(gr),'vr_top':hex(vr),'gr_offs':g_off,'vr_offs':v_off},
      'original_context_pointer_from_literal':hex(struct.unpack_from('<Q',m.blob,0x126e0)[0]),
      'native_CRT_return_length':scalar,'reference_text_for_comparison_only':text.decode(),
      'native_output256_hex':output.hex(),'source_view_va_list_and_spill_slots_unchanged':True,
      'events':events,'hardware_timer_or_complete_logger_header_output_backend':False,
      'independent_formatter_not_continuous_resume_after_MMIO_or_clock_result_adapter':True}


def run(out):
    prior=prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for row in json.loads(prior.read_text())['files']:assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    obj=prev.prev.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o'
    code,ro,_=prev.prev.object_image(obj.read_bytes())
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    kernel=(n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    assets=(blob,module,kernel,code,ro)
    cases=[one_case(assets,seed,limit) for seed,limit in ((0xa5,236),(0xc3,236),(0xc3,32),(0xc3,0))]
    regions=[('original vsnprintf-like wrapper excluding literal',0x126a8,0x126dc),
      ('original bounded stream setup excluding UDF',0x125c0,0x126a4),
      ('native timestamp header caller',0x27d32c,0x27d3a0),
      ('native hardware timer reads',0x2a4588,0x2a45fc),
      ('native MMIO load helper',0x29f6c8,0x29f6dc)]
    proof={'status':'PASS_NATIVE_INTERNAL_FORMATTER_WITH_EXPLICIT_UNEXECUTED_TIMER',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'bounded_fragments':sum(len(c['events']) for c in cases),'cases':cases,
      'original_regions':[{'name':name,'instructions':im.dump(blob,a,z,V)} for name,a,z in regions],
      'scope':{'formatting_calls_are_internal_image_code_not_a_replaced_kernel_printf':True,
        'original_file_backed_context_used_without_new_host_locale_or_CRT_objects':True,
        'actual_MMIO_timer_read_stopped_before_load_not_simulated':True,
        'only_independent_text_formatting_not_full_diagnostic_after_MMIO':True,
        'global_pointer_lifetimes_real_loader_sync_Hal_recording_and_recovery':False,
        'UU_Windows_camera_interfaces_auth_modes_drivers_files_modules_WBI_flash':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(out/'diagnostic-format-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(module),'kernel_sha256':im.sha(kernel),
      'wrapper_object_sha256':im.sha(obj.read_bytes()),'previous_manifest_sha256':PRIOR_SHA,'volume_uuid':im.VOLUME})
    print(json.dumps({'status':proof['status'],'bounded_fragments':proof['bounded_fragments'],
      'text_lengths':[c['native_CRT_return_length'] for c in cases],'goal_complete':False}))


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
