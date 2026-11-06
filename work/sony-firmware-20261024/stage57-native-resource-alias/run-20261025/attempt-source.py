#!/usr/bin/env python3
"""Compile OUR scoped matcher-view/writer, execute only in bounded Unicorn.

Explicit post-log inputs and owner/session/epoch assumptions remain fixtures.
Sony image/code/tables and original descriptor are immutable. No host payload,
camera, driver, mode, module, firmware, USB or remote operations exist here.
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
sys.path.insert(0,str(BASE/'stage54-native-open-matcher-input'))
import open_matcher_input as prev
sys.path.insert(0,str(BASE/'stage37-compiled-scoped-writer'))
import compiled_writer as old
r,im,V,n=prev.r,prev.im,prev.V,prev.n
CODE,RODATA=0x13000000,0x13010000
CONTROL=r.ARENA+0x3a0000
VIEW=r.ARENA+0x3b0000
RESULT=r.ARENA+0x3b1000
PACKET=r.ARENA+0x3b2000
INPUT=r.ARENA+0x3b3000
NEG_SRC=r.ARENA+0x3b4000
B=r.ARENA+0x180000
COMMON=prev.COMMON
COPY=COMMON+0xe010
MAGIC,SESSION,EPOCH=0x4658334735373031,0x1122334455667788,7
PRIOR_SHA='de9b0acdb0ecadba06eb2b83c3f2636f5316ef5604c91a44415df924855954f5'


def object_image(raw):
    elf=ELFFile(io.BytesIO(raw));assert elf['e_type']=='ET_REL' and elf['e_machine']=='EM_AARCH64'
    assert elf.elfclass==64 and elf.little_endian and elf.num_segments()==0
    text=elf.get_section_by_name('.text');ro=elf.get_section_by_name('.rodata')
    assert text['sh_flags']==6 and ro['sh_flags']==2
    assert not any(sec['sh_flags']&3==3 for sec in elf.iter_sections())
    code=bytearray(text.data());data=ro.data();assert 0<len(code)<=0x10000 and 392<=len(data)<4096
    symbols=elf.get_section_by_name('.symtab')
    assert not any(s.name and s['st_shndx']=='SHN_UNDEF' for s in symbols.iter_symbols())
    functions={s.name:CODE+s['st_value'] for s in symbols.iter_symbols() if s['st_info']['type']=='STT_FUNC'}
    assert set(functions)=={'fx3_candidate','fx3_match_view'}
    indices={i:s.name for i,s in enumerate(elf.iter_sections())}
    bases={i:CODE if name=='.text' else RODATA for i,name in indices.items() if name in ('.text','.rodata')}
    relocs=[]
    for sec in elf.iter_sections():
        if sec['sh_type']!='SHT_RELA':continue
        assert indices[sec['sh_info']]=='.text'
        table=elf.get_section(sec['sh_link'])
        for rel in sec.iter_relocations():
            sym=table.get_symbol(rel['r_info_sym']);assert sym['st_shndx'] in bases
            target=bases[sym['st_shndx']]+sym['st_value']+rel['r_addend']
            at=rel['r_offset'];kind=rel['r_info_type'];word=struct.unpack_from('<I',code,at)[0]
            if kind==275:
                delta=((target&~4095)-((CODE+at)&~4095))>>12
                assert -(1<<20)<=delta<(1<<20);bits=delta&0x1fffff
                patched=(word&~((3<<29)|(0x7ffff<<5)))|((bits&3)<<29)|((bits>>2)<<5)
            elif kind==277:patched=(word&~(4095<<10))|((target&4095)<<10)
            else:raise AssertionError(('unapproved OUR-object relocation',kind))
            struct.pack_into('<I',code,at,patched)
            relocs.append({'offset':hex(at),'type':kind,'target':hex(target)})
    return bytes(code),data,functions,relocs


class Guest(prev.Guest):
    def __init__(self,blob,module,kernel,code,ro,functions):
        super().__init__(blob,module,kernel);self.functions=functions;self.code_bytes=code;self.ro_bytes=ro
        self.uc.mem_map(CODE,0x10000,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
        self.uc.mem_map(RODATA,4096,r.unicorn.UC_PROT_READ)
        self.uc.mem_write(CODE,code);self.uc.mem_write(RODATA,ro)
        self.ranges.append((CODE,CODE+len(code)))
        self.ranges.extend((V+a,V+z) for a,z in [*old.w.RANGES,(0x21ed28,0x21ed80)])
        self.boundaries[V+0x27d568]='before_original_row_diagnostic'
        self.boundaries[V+0x22211c]='after_original_rate_fields_before_other_inputs'


def original_phase(m,label,start,independent=True,**regs):
    e=prev.phase(m,label,start,independent=independent,**regs)
    global LAST_PHASE
    LAST_PHASE=e
    return e


def prototype(m,label,function,args):
    m.store_count=0;m.store_digest=hashlib.sha256()
    regs={f'x{i}':value for i,value in enumerate(args)}
    # Separate declared guest stack, never claim an inserted Sony call frame.
    e=prev.c.phase(m,label,m.functions[function],sp=r.STACK+0x2000,**regs)
    e['function']=function;e['status']=m.uc.reg_read(r.reg.UC_ARM64_REG_X0)
    assert e['reason']=='returned'
    assert all(int(pc,16)==r.STOP or CODE<=int(pc,16)<CODE+len(m.code_bytes) for pc in e['pcs'])
    permitted=[(CONTROL,296),(r.STACK,r.STACK_SIZE)]
    if function=='fx3_match_view':permitted.append((VIEW,152))
    else:permitted.extend(((COPY,256),(COMMON+0xe000,8)))
    assert all(any(a<=int(w['address'],16) and int(w['address'],16)+w['size']<=a+n
      for a,n in permitted) for w in e['writes'])
    global LAST_PHASE
    LAST_PHASE=e
    return e


def control(m):return old.control(m)


def init_control(m):
    values=[MAGIC,SESSION,EPOCH,EPOCH,COMMON,1,0,0,1,0,0,0,0]
    m.uc.mem_write(CONTROL,struct.pack('<13Q',*values)+bytes(192))


def assert_immutable(m,blob):
    prev.c.assert_image(m,blob)
    assert m.read(CODE,len(m.code_bytes))==m.code_bytes and m.read(RODATA,len(m.ro_bytes))==m.ro_bytes


def linked(assets):
    blob,module,kernel,code,ro,functions=assets
    m=Guest(*assets);ev=n.link(m)
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    return m,ev


def native_prefix(assets,seed):
    m,load=linked(assets);events=[load]
    m.uc.mem_write(prev.HANDLER,bytes(0xe520))
    e=original_phase(m,'original common-handler constructor',0x21d9e0,x0=COMMON)
    assert e['reason']=='returned';events.append(e)
    # Exactly stage54 declared queues/ID/node fixtures; no full factory boot.
    m.uc.mem_write(prev.CTX,bytes(0x57000))
    m.uc.mem_write(prev.CTX+0x108,struct.pack('<I',1));m.uc.mem_write(prev.CTX+0x118,r.p64(prev.MESSAGE))
    m.uc.mem_write(prev.FACTORY+0x55ec8,struct.pack('<I',1))
    m.uc.mem_write(prev.FACTORY+0x55ed8,r.p64(prev.HANDLER))
    m.uc.mem_write(prev.FACTORY+8,struct.pack('<I',1));m.uc.mem_write(prev.FACTORY+0x14,bytes(4))
    tree=prev.FACTORY+0x55f10
    m.uc.mem_write(tree+0x120,struct.pack('<I',1));m.uc.mem_write(tree+0x130,r.p64(prev.NODE))
    descriptor=prev.inputs()[0][1]
    m.uc.mem_write(prev.MESSAGE,bytes(0xc0));m.uc.mem_write(prev.MESSAGE+8,r.p64(prev.IDENTITY))
    m.uc.mem_write(prev.IDENTITY,struct.pack('<I',prev.UID));m.uc.mem_write(prev.MESSAGE+0x20,descriptor)
    m.uc.mem_write(r.SP-0x2000,bytes([seed])*0x3000)
    e=original_phase(m,'native queued FH Open produces MAIN matcher input',0x22f34c,x0=prev.CTX)
    assert e['reason']=='boundary: before_unexecuted_diagnostic';events.append(e)
    assert len(m.matcher_calls)==1
    source=int(m.matcher_calls[0]['input_pointer'],16);raw=m.read(source,152)
    assert raw[:136]==descriptor and struct.unpack_from('<4I',raw,0x88)==(1,10,25,seed*0x01010101)
    assert m.read(COMMON+0xe110,136)==descriptor
    init_control(m)
    return m,events,source,raw,prev.captured_regs(m)


def default_query(m,label,expected):
    e=original_phase(m,label,0x225b7c,x0=COMMON,x8=RESULT)
    assert e['reason']=='returned'
    values=struct.unpack('<3Q',m.read(RESULT,24));assert values==(25999360,expected,26000000)
    e['decoded_trace_target_cpb']=list(values)
    return e


def rate_pack(m,label,expected):
    m.uc.mem_write(PACKET,bytes([0xa5])*0x40)
    e=original_phase(m,label,0x221fd0,x21=COMMON,x22=PACKET,x20=INPUT)
    assert e['reason']=='boundary: after_original_rate_fields_before_other_inputs'
    block=m.read(PACKET,0x38);words=struct.unpack_from('<3I',block,0x2c)
    target=((words[0]>>8)+1)<<(6+(words[0]&255))
    trace=((words[1]>>8)+1)<<(6+(words[1]&255))
    cpb=((words[2]>>8)+1)<<(4+(words[2]&255))
    assert (trace,target,cpb)==(25999360,expected,26000000)
    e['partial_block_hex']=block.hex();e['decoded_trace_target_cpb']=[trace,target,cpb]
    return e


def positive(assets,seed):
    blob=assets[0];m,events,source,raw,regs=native_prefix(assets,seed)
    p=[];m.uc.mem_write(VIEW,bytes([0x5a])*152)
    original_descriptor=m.read(COMMON+0xe110,136)
    e=prototype(m,'compiled separate FH-to-FF matcher view','fx3_match_view',
      [CONTROL,source,VIEW,EPOCH,SESSION]);p.append(e);assert e['status']==0
    view=m.read(VIEW,152)
    assert [i for i,(a,b) in enumerate(zip(raw,view)) if a!=b]==[0x38]
    assert struct.unpack_from('<I',view,0x38)[0]==6
    assert m.read(source,152)==raw and m.read(COMMON+0xe110,136)==original_descriptor
    # A distinct guest after the excluded diagnostics. Input X19 points to the
    # compiled temporary view; original frames/arena are explicit fixtures.
    post,load=linked(assets);events.append(load)
    post.uc.mem_write(r.ARENA,m.read(r.ARENA,r.ARENA_SIZE))
    post.uc.mem_write(r.STACK,m.read(r.STACK,r.STACK_SIZE))
    post.regs(**regs);post.regs(x19=VIEW,x20=3);post.match_param=VIEW
    e=original_phase(post,'independent original matcher consumes compiled view',0x225fa0,independent=False)
    events.append(e);assert e['reason']=='boundary: before_unexecuted_diagnostic'
    index=post.uc.reg_read(r.reg.UC_ARM64_REG_X23)&0xffffffff;assert index==386
    assert post.read(VIEW,152)==view and post.read(source,152)==raw
    e=original_phase(post,'independent native row address and preset ID from returned index',0x21ed28,independent=False)
    events.append(e);assert e['reason']=='boundary: before_original_row_diagnostic'
    row=post.uc.reg_read(r.reg.UC_ARM64_REG_X26);ident=post.uc.reg_read(r.reg.UC_ARM64_REG_X22)
    assert row==V+0x395108+386*0x90 and ident==0x19450
    # Later unexecuted diagnostic/UID-name helper excluded explicitly. UID is
    # original prefix-produced common value, not a supplied matcher return.
    uid=struct.unpack('<I',post.read(COMMON+0x10ac,4))[0];assert uid==prev.UID
    e=original_phase(post,'independent native row marshalling and preset selector on original FH descriptor',
      0x21edc8,independent=False,x23=uid)
    events.append(e);assert e['reason']=='boundary: before_actual_buffer_and_channel_preparation'
    assert post.read(COMMON+0xe000,8)==r.p64(V+0x3c5798)
    assert post.read(COMMON+0xe470,4)==struct.pack('<I',0x19450)
    assert post.read(COMMON+0xe110,136)==original_descriptor
    events.append(default_query(post,'original FF default before private16M publication',24498176))
    post.uc.mem_write(B,bytes([0x5a])*0xf000);saved_b=post.read(B,0xf000)
    e=prototype(post,'compiled exact FH writer publishes private16M preset','fx3_candidate',
      [CONTROL,0,0,0,EPOCH,SESSION]);p.append(e);assert e['status']==0
    assert control(post)['out_id']==1
    original=blob[0x3c5798:0x3c5898];copy=post.read(COPY,256)
    assert [i for i,(a,b) in enumerate(zip(original,copy)) if a!=b]==[0xb0,0xb1,0xb2]
    assert post.read(COMMON+0xe000,8)==r.p64(COPY)
    events.append(default_query(post,'original selected-record query on compiled private16M',16000000))
    packed=rate_pack(post,'original rate pack on compiled private16M',16000000);events.append(packed)
    old_packet=post.read(PACKET,0x38)
    # Data-only lifecycle: dependency completion remains simulated. No code is
    # reclaimed and the FH descriptor does not become a valid stock config.
    for label,args,status in (
      ('close candidate entry',[CONTROL,4,0,0,EPOCH,SESSION],0),
      ('held while producer remains',[CONTROL,5,0,0,EPOCH,SESSION],10),
      ('register independently prepared parameter packet',[CONTROL,1,1,PACKET,EPOCH,SESSION],0),
      ('simulated producer exit',[CONTROL,2,1,0,EPOCH,SESSION],0),
      ('held while packet remains',[CONTROL,5,0,0,EPOCH,SESSION],10),
      ('simulated packet consumer completion',[CONTROL,3,2,PACKET,EPOCH,SESSION],0),
      ('data pointer restore after declared dependency exit',[CONTROL,5,0,0,EPOCH,SESSION],0)):
        q=prototype(post,label,'fx3_candidate',args);p.append(q);assert q['status']==status
    events.append(default_query(post,'original default after data-only pointer restore',24498176))
    assert post.read(COMMON+0xe110,136)==original_descriptor
    assert post.read(source,152)==raw and post.read(VIEW,152)==view
    assert post.read(B,0xf000)==saved_b and post.read(PACKET,0x38)==old_packet
    assert post.read(V+0x3c5798,256)==original and post.read(COPY,256)==copy
    assert_immutable(m,blob);assert_immutable(post,blob)
    return {'seed':seed,'original_input98_hex':raw.hex(),'compiled_match_view98_hex':view.hex(),
      'original_FH_descriptor88_hex':original_descriptor.hex(),'only_match_view_changed_byte':0x38,
      'native_MAIN_tail':list(struct.unpack_from('<4I',raw,0x88)),
      'native_matcher_row':index,'native_row_address':hex(row),'native_preset_id':hex(ident),
      'native_selected_default':24498176,'compiled_private_target':16000000,
      'native_metadata_identity_remains_FH_and_source_unchanged':True,
      'entire_other_owner_and_old_packet_unchanged':True,'control_after':control(post),
      'original_events':events,'prototype_events':p,
      'actual_hook_placement_current_owner_epoch_shared_lock_full_Open_Start_Hal':False,
      'pointer_restore_is_not_valid_stock_mode_restore_or_hardware_recovery':True}


def negatives(assets):
    m,events,source,raw,regs=native_prefix(assets,0xc3)
    rows=[];descriptor=raw[:136]
    controls=['FF source','geometry','proxy role','tail8c','tail90','source padding',
      'owner descriptor','epoch','session','observed epoch','gate','phase','held lock','foreign owner','overlap']
    for label in controls:
        init_control(m);m.uc.mem_write(NEG_SRC,raw);m.uc.mem_write(COMMON+0xe110,descriptor)
        m.uc.mem_write(VIEW,bytes([0x5a])*152)
        args=[CONTROL,NEG_SRC,VIEW,EPOCH,SESSION];status=5
        field=lambda name,value:old.set_field(m,name,value)
        if label=='FF source':m.uc.mem_write(NEG_SRC+0x38,struct.pack('<I',6))
        elif label=='geometry':m.uc.mem_write(NEG_SRC+8,struct.pack('<H',1921))
        elif label=='proxy role':m.uc.mem_write(NEG_SRC+0x88,struct.pack('<I',2))
        elif label=='tail8c':m.uc.mem_write(NEG_SRC+0x8c,struct.pack('<I',1))
        elif label=='tail90':m.uc.mem_write(NEG_SRC+0x90,struct.pack('<I',24))
        elif label=='source padding':m.uc.mem_write(NEG_SRC+0x84,b'\x01')
        elif label=='owner descriptor':m.uc.mem_write(COMMON+0xe110+0x38,struct.pack('<I',6))
        elif label=='epoch':args[3]+=1;status=1
        elif label=='session':args[4]+=1;status=1
        elif label=='observed epoch':field('observed_epoch',EPOCH+1);status=4
        elif label=='gate':field('gate',0);status=3
        elif label=='phase':field('phase',1);status=3
        elif label=='held lock':field('lock',1);status=2
        elif label=='foreign owner':field('owner',B)
        elif label=='overlap':args[1]=VIEW
        before=m.read(VIEW,152);common_before=m.read(COMMON,0xe520)
        e=prototype(m,'rejected view: '+label,'fx3_match_view',args)
        assert e['status']==status,(label,e['status'],status)
        assert m.read(VIEW,152)==before and m.read(COMMON,0xe520)==common_before
        if label=='held lock':assert control(m)['lock']==1
        rows.append({'label':label,'expected_status':status,'event':e,
          'destination_and_common_unchanged':True,'control_after':control(m)})
    assert_immutable(m,assets[0])
    return {'original_setup_events':events,'controls':rows,
      'all_inputs_are_derived_or_mutated_fixtures_not_current_camera_states':True}


def run(out):
    prior=BASE/'stage56-native-stop-name-flow/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for x in json.loads(prior.read_text())['files']:assert im.sha((ROOT/x['path']).read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    pins=json.loads((STAGE/'prototype-source-origin.json').read_text())
    for name,pin in pins['outputs'].items():assert im.sha((STAGE/name).read_bytes())==pin
    command=['/usr/bin/clang',*old.FLAGS,'-c',str(STAGE/'resource_alias.c'),'-o',str(out/'resource_alias.a64.o')]
    built=subprocess.run(command,capture_output=True,text=True);assert built.returncode==0,built.stderr
    raw=(out/'resource_alias.a64.o').read_bytes();code,ro,functions,relocs=object_image(raw)
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    kernel=(n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    assets=(blob,module,kernel,code,ro,functions)
    cases=[positive(assets,seed) for seed in (0xa5,0xc3)]
    negative=negatives(assets)
    # Reuse exact prior raw-input/no-alias native observations, rather than
    # pretend an extra repeated run adds new coverage.
    prior_native=BASE/'stage54-native-open-matcher-input/run-native-quality-and-tail-20261025/open-matcher-input-results.json'
    baseline=json.loads(prior_native.read_text())
    assert [(x['label'],x['independent_native_matcher_row']) for x in baseline['cases']]==[
      ('target_MAIN_FH',-1),('artificial_MAIN_FF_quality24',386),('proxy_FH_control',-1),('stock_UHD_QT150M_control',431)]
    original_fragments=sum(len(x['original_events']) for x in cases)+len(negative['original_setup_events'])
    proto_calls=sum(len(x['prototype_events']) for x in cases)+len(negative['controls'])
    proof={'status':'PASS_COMPILED_SCOPED_MATCH_VIEW_AND_FH_IDENTITY_PRIVATE16M_OFFLINE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'original_fragments':original_fragments,'compiled_prototype_calls':proto_calls,
      'prototype':{'functions':{k:hex(v) for k,v in functions.items()},'object_sha256':im.sha(raw),
        'text_bytes':len(code),'rodata_bytes':len(ro),'relocations':relocs,'code_sha256':im.sha(code),
        'compile_command':command,'compiler_version':subprocess.check_output(['/usr/bin/clang','--version'],text=True)},
      'positive_cases':cases,'negative_controls':negative,
      'existing_baseline_receipt':{'path':str(prior_native.relative_to(ROOT)),
        'sha256':im.sha(prior_native.read_bytes()),'not_replayed_this_stage':True},
      'scope':{'original_source_FH_and_static_match_table_unchanged':True,
        'temporary_match_view_changes_quality_only_then_native_row386_selects19450':True,
        'compiled_writer_uses_exact_original_FH_descriptor_and_original_decoder_packs16M':True,
        'actual_hook_placement_or_temporary_view_lifetime_bound_to_live_Sony_caller':False,
        'full_native_log_state_owner_epoch_shared_lock_or_all_consumers':False,
        'full_Open_Start_Hal_MP4_audio_longrun_or_hardware_accepted':False,
        'data_pointer_restore_is_real_stock_mode_or_hardware_recovery':False,
        'camera_remote_interfaces_files_auth_drivers_modules_WBI_or_flash':False,
        'same_body_backup_restore_coldboot_or_independent_rescue':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(out/'resource-alias-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    (out/'compiled-source.c').write_bytes((STAGE/'resource_alias.c').read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'C_source_sha256':im.sha((STAGE/'resource_alias.c').read_bytes()),
      'source_origin_sha256':im.sha((STAGE/'prototype-source-origin.json').read_bytes()),
      'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(module),'kernel_sha256':im.sha(kernel),
      'previous_manifest_sha256':PRIOR_SHA,'volume_uuid':im.VOLUME})
    print(json.dumps({'status':proof['status'],'original_fragments':original_fragments,
      'compiled_prototype_calls':proto_calls,'native_row':386,'private_target':16000000,'goal_complete':False}))


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
