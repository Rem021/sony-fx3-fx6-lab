#!/usr/bin/env python3
"""OUR stack-view wrapper at ONE guest-only original BL instruction.

Original matcher is genuinely called. Diagnostics stay explicit boundaries;
post-diagnostic continuation is an independent copied guest, not a log/return
adapter. No physical address, Sony module, code publication or hardware claim.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import io
import json
import struct
import subprocess
import sys
import traceback
from elftools.elf.elffile import ELFFile

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage57-native-resource-alias'))
import resource_alias as prev
r,im,V,n,p=prev.r,prev.im,prev.V,prev.n,prev.prev
BRIDGE=V+0x1000000
CONST=BRIDGE+0x10000
SITE=V+0x21ed18
ORIGINAL=V+0x225eb8
PRIOR_SHA='68834930f51c015a87a8467c564d370a65a542540252d7e7046d650eb63debd5'


def branch(at,target,link):
    delta=target-at;assert delta%4==0 and -(1<<27)<=delta<(1<<27)
    return struct.pack('<I',(0x94000000 if link else 0x14000000)|((delta//4)&0x3ffffff))


def object_image(raw):
    e=ELFFile(io.BytesIO(raw));assert e['e_type']=='ET_REL' and e['e_machine']=='EM_AARCH64'
    assert e.elfclass==64 and e.little_endian and e.num_segments()==0
    text=e.get_section_by_name('.text');ro=e.get_section_by_name('.rodata')
    assert text['sh_flags']==6 and ro['sh_flags']==2 and len(ro.data())==136
    assert not any(s['sh_flags']&3==3 for s in e.iter_sections())
    code=bytearray(text.data());data=ro.data();assert 0<len(code)<0x10000
    sy=e.get_section_by_name('.symtab');undefined=[s.name for s in sy.iter_symbols() if s.name and s['st_shndx']=='SHN_UNDEF']
    assert undefined==['sony_matcher']
    functions=[s for s in sy.iter_symbols() if s['st_info']['type']=='STT_FUNC']
    assert len(functions)==1 and functions[0].name=='fx3_match_adapter' and functions[0]['st_value']==0
    assert functions[0]['st_size']==len(code)
    indices={i:s.name for i,s in enumerate(e.iter_sections())};relocs=[]
    for sec in e.iter_sections():
        if sec['sh_type']!='SHT_RELA':continue
        assert indices[sec['sh_info']]=='.text'
        symbols=e.get_section(sec['sh_link'])
        for rel in sec.iter_relocations():
            sym=symbols.get_symbol(rel['r_info_sym']);off=rel['r_offset'];kind=rel['r_info_type']
            word=struct.unpack_from('<I',code,off)[0]
            if sym['st_shndx']=='SHN_UNDEF':
                assert sym.name=='sony_matcher' and rel['r_addend']==0 and kind in (282,283)
                target=ORIGINAL;new=int.from_bytes(branch(BRIDGE+off,target,kind==283),'little')
                assert word&0xfc000000==(0x94000000 if kind==283 else 0x14000000)
            else:
                assert indices[sym['st_shndx']]=='.rodata'
                target=CONST+sym['st_value']+rel['r_addend']
                if kind==275:
                    delta=((target&~4095)-((BRIDGE+off)&~4095))>>12
                    assert -(1<<20)<=delta<(1<<20);bits=delta&0x1fffff
                    new=(word&~((3<<29)|(0x7ffff<<5)))|((bits&3)<<29)|((bits>>2)<<5)
                elif kind==277:new=(word&~(4095<<10))|((target&4095)<<10)
                else:raise AssertionError(('unsupported const relocation',kind))
            struct.pack_into('<I',code,off,new)
            relocs.append({'offset':hex(off),'type':kind,'symbol':sym.name,'target':hex(target)})
    assert any(x['symbol']=='sony_matcher' for x in relocs)
    return bytes(code),data,relocs


class Guest(p.Guest):
    def __init__(self,blob,module,kernel,code,ro):
        super().__init__(blob,module,kernel)
        assert V+len(blob)<BRIDGE
        self.code_bytes=code;self.ro_bytes=ro
        self.uc.mem_map(BRIDGE,0x10000,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
        self.uc.mem_map(CONST,4096,r.unicorn.UC_PROT_READ)
        self.uc.mem_write(BRIDGE,code);self.uc.mem_write(CONST,ro)
        assert self.read(SITE,4)==branch(SITE,ORIGINAL,True)
        self.patch=branch(SITE,BRIDGE,True)
        self.ranges.append((BRIDGE,BRIDGE+len(code)))
        self.bridge_entries=[];self.real_match_entries=[];self.real_returns=[];self.bridge_stores=[]
        self.read_events=[]
        self.uc.hook_add(r.unicorn.UC_HOOK_MEM_READ,self.observe_input_reads)

    def code(self,u,pc,size,user):
        if pc==BRIDGE:
            self.bridge_entries.append({'pc':hex(pc),'owner':hex(u.reg_read(r.reg.UC_ARM64_REG_X0)),
              'source':hex(u.reg_read(r.reg.UC_ARM64_REG_X1)),
              'SP':hex(u.reg_read(r.reg.UC_ARM64_REG_SP)),
              'LR':hex(u.reg_read(r.reg.UC_ARM64_REG_LR))})
        if pc==ORIGINAL:
            ptr=u.reg_read(r.reg.UC_ARM64_REG_X1)
            self.real_match_entries.append({'pc':hex(pc),'owner':hex(u.reg_read(r.reg.UC_ARM64_REG_X0)),
              'input_pointer':hex(ptr),'input98_hex':self.read(ptr,152).hex(),
              'SP':hex(u.reg_read(r.reg.UC_ARM64_REG_SP)),
              'LR':hex(u.reg_read(r.reg.UC_ARM64_REG_LR))})
        if pc==SITE+4:
            self.real_returns.append({'pc':hex(pc),'W0':u.reg_read(r.reg.UC_ARM64_REG_X0)&0xffffffff,
              'SP':hex(u.reg_read(r.reg.UC_ARM64_REG_SP))})
        return super().code(u,pc,size,user)

    def store(self,u,access,address,size,value,user):
        pc=u.reg_read(r.reg.UC_ARM64_REG_PC)
        if BRIDGE<=pc<BRIDGE+len(self.code_bytes):
            if not (r.STACK<=address and address+size<=r.STACK+r.STACK_SIZE):
                self.stop('wrapper store outside guest stack');return
            self.bridge_stores.append({'pc':hex(pc),'address':hex(address),'size':size})
        return super().store(u,access,address,size,value,user)

    def observe_input_reads(self,u,access,address,size,value,user):
        if not self.real_match_entries:return
        at=int(self.real_match_entries[-1]['input_pointer'],16)
        if at<=address and address+size<=at+152:
            self.read_events.append({'pc':hex(u.reg_read(r.reg.UC_ARM64_REG_PC)),
              'address':hex(address),'size':size,'offset':hex(address-at),
              'SP':hex(u.reg_read(r.reg.UC_ARM64_REG_SP))})


def phase(m,label,start,independent=True,**regs):
    e=p.phase(m,label,start,independent=independent,**regs)
    global LAST_PHASE
    LAST_PHASE=e
    return e


def linked(assets):
    m=Guest(*assets);load=n.link(m)
    # Keep the original loader's pristine-image assertions intact. Apply the
    # declared single guest-only callsite change only AFTER that loader check.
    m.uc.mem_write(SITE,m.patch)
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    return m,load


def assert_code(m,blob):
    assert m.read(V,0x1ec)==blob[:0x1ec]
    assert m.read(V+0x1ec,0x698)==m.read(n.MDATA,0x698)
    assert m.read(V+0x884,SITE-(V+0x884))==blob[0x884:SITE-V]
    assert m.read(SITE,4)==m.patch
    assert m.read(SITE+4,len(blob)-(SITE+4-V))==blob[SITE+4-V:]
    assert m.read(BRIDGE,len(m.code_bytes))==m.code_bytes
    assert m.read(CONST,len(m.ro_bytes))==m.ro_bytes


def case(assets,label,descriptor,seed,expected,alias):
    blob=assets[0];m,load=linked(assets);events=[load]
    m.uc.mem_write(p.HANDLER,bytes(0xe520))
    e=phase(m,'original common constructor '+label,0x21d9e0,x0=p.COMMON)
    assert e['reason']=='returned';events.append(e)
    m.uc.mem_write(p.CTX,bytes(0x57000));m.uc.mem_write(p.CTX+0x108,struct.pack('<I',1))
    m.uc.mem_write(p.CTX+0x118,r.p64(p.MESSAGE));m.uc.mem_write(p.FACTORY+0x55ec8,struct.pack('<I',1))
    m.uc.mem_write(p.FACTORY+0x55ed8,r.p64(p.HANDLER));m.uc.mem_write(p.FACTORY+8,struct.pack('<I',1))
    m.uc.mem_write(p.FACTORY+0x14,bytes(4));tree=p.FACTORY+0x55f10
    m.uc.mem_write(tree+0x120,struct.pack('<I',1));m.uc.mem_write(tree+0x130,r.p64(p.NODE))
    m.uc.mem_write(p.MESSAGE,bytes(0xc0));m.uc.mem_write(p.MESSAGE+8,r.p64(p.IDENTITY))
    m.uc.mem_write(p.IDENTITY,struct.pack('<I',p.UID));m.uc.mem_write(p.MESSAGE+0x20,descriptor)
    m.uc.mem_write(r.SP-0x2000,bytes([seed])*0x3000)
    e=phase(m,'queued native Open through guest-only BL and wrapper to real matcher '+label,0x22f34c,x0=p.CTX)
    assert e['reason']=='boundary: before_unexecuted_diagnostic';events.append(e)
    assert len(m.bridge_entries)==len(m.real_match_entries)==len(m.common_calls)==1
    bridge=m.bridge_entries[0];entered=m.real_match_entries[0]
    source=int(bridge['source'],16);actual=int(entered['input_pointer'],16)
    raw=m.read(source,152);view=m.read(actual,152)
    assert raw[:136]==descriptor and m.read(p.COMMON+0xe110,136)==descriptor
    assert bridge['owner']==entered['owner']==hex(p.COMMON) and bridge['LR']==hex(SITE+4)
    caller_sp=int(bridge['SP'],16);wrapper_sp=int(entered['SP'],16)
    if alias:
        assert r.STACK<=wrapper_sp<=actual and actual+152<=caller_sp<r.STACK+r.STACK_SIZE
        assert [i for i,(a,b) in enumerate(zip(raw,view)) if a!=b]==[0x38] and view[0x38]==6
        assert BRIDGE<=int(entered['LR'],16)<BRIDGE+len(m.code_bytes)
    else:
        assert actual==source and view==raw
    assert_code(m,blob)
    # Independent post-diagnostic state. Crucially X19 stays the real compiler-
    # produced argument pointer: no host-created VIEW pointer or result scalar.
    post,load2=linked(assets);events.append(load2)
    post.uc.mem_write(r.ARENA,m.read(r.ARENA,r.ARENA_SIZE))
    post.uc.mem_write(r.STACK,m.read(r.STACK,r.STACK_SIZE))
    regs=p.captured_regs(m);post.regs(**regs);post.regs(x20=3)
    post.real_match_entries=[dict(entered)];post.match_param=actual
    assert post.uc.reg_read(r.reg.UC_ARM64_REG_X19)==actual
    e=phase(post,'independent original matcher body returns through actual wrapper epilogue '+label,
      0x225fa0,independent=False);events.append(e)
    assert e['reason']=='boundary: before_unexecuted_diagnostic' and e['pcs'][-2]==hex(SITE+8)
    scalar=post.uc.reg_read(r.reg.UC_ARM64_REG_X23)&0xffffffff
    index=scalar if scalar<0x80000000 else scalar-(1<<32);assert index==expected
    assert post.real_returns==[{'pc':hex(SITE+4),'W0':expected&0xffffffff,'SP':hex(caller_sp)}]
    assert post.read(source,152)==raw and post.read(p.COMMON+0xe110,136)==descriptor
    assert post.read(actual,152)==view
    reads=post.read_events;assert reads
    if alias:assert all(int(x['SP'],16)<actual for x in reads)
    assert not post.bridge_entries
    if alias:
        assert any(BRIDGE<=int(pc,16)<BRIDGE+len(m.code_bytes) for pc in e['pcs'])
        assert any(int(w['address'],16)<=actual<int(w['address'],16)+w['size'] for w in m.bridge_stores)
    assert_code(post,blob)
    return {'label':label,'seed':seed,'scope_alias_applied':alias,'original_descriptor_hex':descriptor.hex(),
      'original_source98_hex':raw.hex(),'real_matcher_argument98_hex':view.hex(),
      'original_callsite':hex(SITE),'original_call_instruction':branch(SITE,ORIGINAL,True).hex(),
      'guest_only_replacement_BL':m.patch.hex(),'wrapper_entry':bridge,'real_matcher_entry':entered,
      'native_matcher_row':index,'actual_native_return_to_original_caller':post.real_returns,
      'compiler_owned_argument_lives_in_active_wrapper_stack_frame':alias,
      'read_events_during_original_matcher_body':reads,'wrapper_native_stores':m.bridge_stores,
      'post_body_wrapper_native_stores':post.bridge_stores,'original_events':events,
      'diagnostics_excluded_and_post_body_is_independent_copied_state':True,
      'actual_Sony_loader_module_MMU_code_publish_owner_epoch_locks_or_Hal':False,
      'global_pointer_non_escape_all_threads_and_all_consumers_proven':False}


def run(out):
    prior=prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for x in json.loads(prior.read_text())['files']:assert im.sha((ROOT/x['path']).read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    assert (STAGE/'expected_hd16m.inc').read_bytes()==(prev.STAGE/'expected_hd16m.inc').read_bytes()
    cmd=['/usr/bin/clang',*prev.old.FLAGS,'-c',str(STAGE/'match_adapter.c'),'-o',str(out/'match_adapter.a64.o')]
    built=subprocess.run(cmd,capture_output=True,text=True);assert built.returncode==0,built.stderr
    raw=(out/'match_adapter.a64.o').read_bytes();code,ro,relocs=object_image(raw)
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    kernel=(n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    assets=(blob,module,kernel,code,ro);inp=p.inputs();assert ro==inp[0][1]
    cases=[case(assets,'target FH priorA5',inp[0][1],0xa5,386,True),
      case(assets,'target FH priorC3',inp[0][1],0xc3,386,True),
      case(assets,'original FF control',inp[1][1],0xc3,386,False),
      case(assets,'proxy FH control',inp[2][1],0xc3,-1,False),
      case(assets,'stock UHD control',inp[3][1],0xc3,431,False)]
    proof={'status':'PASS_GUEST_CALLSITE_STACK_VIEW_AND_NATIVE_RETURN_WITH_EXCLUDED_DIAGNOSTICS',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'original_and_wrapper_bounded_fragments':sum(len(x['original_events']) for x in cases),
      'prototype':{'compile_command':cmd,'object_sha256':im.sha(raw),'text_bytes':len(code),
        'text_sha256':im.sha(code),'rodata_bytes':len(ro),'relocations':relocs,
        'guest_near_mapping_not_actual_camera_address':hex(BRIDGE)},'cases':cases,
      'scope':{'ONE_original_guest_BL_explicitly_redirected_not_pristine_guest_code':True,
        'original_firmware_file_and_other_guest_bytes_unchanged':True,
        'native_original_matcher_called_and_real_return_through_compiled_epilogue':True,
        'target_temp_view_stack_lifetime_observed_in_bounded_original_body':True,
        'global_pointer_non_escape_synchronization_or_real_diagnostics_proven':False,
        'Sony_loadable_module_or_actual_runtime_MMU_code_publish_cache_sync':False,
        'full_Open_Start_Hal_recording_audio_longrun_or_same_body_recovery':False,
        'UU_Windows_active_camera_protocol_files_drivers_modules_WBI_or_flash':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(out/'match-call-frame-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    (out/'compiled-source.c').write_bytes((STAGE/'match_adapter.c').read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'C_source_sha256':im.sha((STAGE/'match_adapter.c').read_bytes()),'avcam_sha256':im.sha(blob),
      'LIRO_sha256':im.sha(module),'kernel_sha256':im.sha(kernel),'previous_manifest_sha256':PRIOR_SHA,
      'volume_uuid':im.VOLUME})
    print(json.dumps({'status':proof['status'],'bounded_fragments':proof['original_and_wrapper_bounded_fragments'],
      'cases':[(x['label'],x['native_matcher_row'],x['scope_alias_applied']) for x in cases],
      'goal_complete':False}))


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
