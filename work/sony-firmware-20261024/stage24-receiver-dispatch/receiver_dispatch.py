#!/usr/bin/env python3
"""Original receiver dispatch and decode-mask provenance, bounded guest only.

No parameter-controller outputs, allocation, constructors, state transition,
MC validation, transport, native mutex, backup or camera execution.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'work/sony-firmware-20261024'
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'stage23-encoder-boundary'))
import encoder_boundary as e
AV,pp,qp,q,w,reg=e.AV,e.pp,e.qp,e.q,e.w,e.reg
SCRATCH,FP=w.SCRATCH,w.FP
PACKET,PAYLOAD,FACTORY,NEW,MSG,CTRL=(SCRATCH+v for v in (0x2000,0x6000,0x9000,0x5000,0xa000,0xb000))


def p64(value):return struct.pack('<Q',value)


def seed(m,fmt=15,cid=0,mid=0x210,input60=0,invalid=False):
    old=json.loads((e.STAGE/'run-corrected-20261025/encoder-boundary-results.json').read_text())
    packet=bytearray.fromhex(old['packet_cases'][0]['packet_hex'])
    packet[0x60]=input60
    if invalid:packet[0x66]=packet[0x80]=0xff
    raw=bytearray(0x30);struct.pack_into('<H',raw,2,cid)
    raw[0x18]=0x20;raw[0x1c]=fmt
    struct.pack_into('<I',raw,0x24,mid);struct.pack_into('<Q',raw,0x28,PACKET)
    m.uc.mem_write(PACKET,bytes(packet));m.uc.mem_write(PAYLOAD,bytes(raw))
    return bytes(packet),bytes(raw)


def command_jump(mid,cid):
    target=0xaf3b8+4*struct.unpack('<h',AV.read(0x145f4c+cid*2,2))[0]
    destinations={0xaf4d4,0xaf658,0xaf598,0xaf648,0xaf650,0xaf5c0,0xaf3b8}
    m=q.BoundaryMicro(AV,[(0xaf374,0xaf3b8)],boundaries={v:'command_table_destination' for v in destinations})
    seed(m,mid=mid,cid=cid);w.putregs(m,x19=PAYLOAD)
    r=m.run(0xaf374);assert r['reason']=='phase boundary: command_table_destination'
    assert r['stop_pc']==hex(target) and not r['stores']
    r.update(message_id=hex(mid),command_id=cid,original_destination=hex(target),
        scope='Original table dispatch after excluded initial parameter-controller write; destination body not executed.')
    return r


def ordinary_usecase(fmt,input60=0,invalid=False):
    boundaries={0xaf3bc:'before_UcsMgr_singleton',0xaf500:'before_controller_input1',0xaf524:'before_controller_input2'}
    m=q.BoundaryMicro(AV,[(0xaf4f4,0xaf57c),(0xaf3b8,0xaf3bc)],boundaries=boundaries)
    before=seed(m,fmt=fmt,input60=input60,invalid=invalid)
    w.putregs(m,x19=PAYLOAD,x20=PACKET,x21=FACTORY)
    r=m.run(0xaf4f4)
    expected=(1 if fmt!=0x44 else 14) if input60==0 else {1:None,2:None,3:16}[input60]
    if expected is not None:
        assert r['reason']=='phase boundary: before_UcsMgr_singleton'
        assert m.uc.reg_read(reg.UC_ARM64_REG_X20)==expected
    else:assert r['stop_pc']==hex(0xaf500 if input60==1 else 0xaf524)
    assert before==(bytes(m.uc.mem_read(PACKET,0x98)),bytes(m.uc.mem_read(PAYLOAD,0x30))) and not r['stores']
    r.update(outer_FileFormat=fmt,raw_input_selector_60=input60,invalid_codec_and_frame_fixture=invalid,
        selected_usecase=expected,packet_and_payload_unchanged=True,
        scope='Post-diagnostic ordinary Open decision only. UcsMgr, initial parameter writes and actual state changes excluded; not format validation.')
    return r


ALLOCATORS={0xaf948:('EncOpenAstra',0x240),0xaf928:('2ndEncOpen',0x1c0),
            0xaf98c:('EncStartAstra',0x1c0),0xaf96c:('2ndEncStart',0x1c0),
            0xafbb4:('EncOpen2Astra',0x1c0),0xafbd0:('EncStart2Astra',0x1c0)}


def create_selection(cid,key104a,key104b=0):
    m=q.BoundaryMicro(AV,[(0xaf790,0xafe48)],boundaries={0x9e710:'before_allocation'})
    m.uc.mem_write(FP+0x4c,bytes([0,key104a,key104b,0]))
    w.putregs(m,x20=FACTORY,x21=0x38,x22=cid,x29=FP)
    r=m.run(0xaf790);assert r['reason']=='phase boundary: before_allocation'
    pc=int(r['pcs'][-2],16);name,size=ALLOCATORS[pc]
    expected={0:'2ndEncOpen' if key104a else 'EncOpenAstra',
              1:'2ndEncStart' if key104a else 'EncStartAstra',5:'EncOpen2Astra',6:'EncStart2Astra'}[cid]
    assert name==expected and m.uc.reg_read(reg.UC_ARM64_REG_X0)==size
    r.update(command_id=cid,assumed_controller_values={'0x1049':0,'0x104a':key104a,'0x104b':key104b,'0x106b':0},
        selected_class=name,original_allocation_call=hex(pc),allocation_size=size,
        scope='Independent original post-controller-read selection; values are explicit fixtures, no controller getter or allocation output stub.')
    return r


CTOR_SLICES=[('EncOpenAstra',0xaf94c,0xaf95c,0x9ccf0),('2ndEncOpen',0xaf92c,0xaf940,0x9cc50),
             ('EncStartAstra',0xaf990,0xaf9a0,0x9ba00),('2ndEncStart',0xaf970,0xaf984,0x9d940),
             ('EncOpen2Astra',0xafbb8,0xafbc8,0x9bd50),('EncStart2Astra',0xafbd4,0xafbe4,0x9cd10)]


def constructor_arguments(name,start,end,plt):
    m=q.BoundaryMicro(AV,[(start,end)],boundaries={plt:'before_original_constructor_PLT'})
    m.uc.mem_write(FACTORY+8,struct.pack('<QQ',MSG,CTRL))
    w.putregs(m,x0=NEW,x20=FACTORY,x21=0x38,x23=2)
    r=m.run(start);assert r['reason']=='phase boundary: before_original_constructor_PLT'
    actual=[m.uc.reg_read(getattr(reg,'UC_ARM64_REG_X'+str(i))) for i in range(4)]
    assert actual==[NEW,MSG,CTRL,0x38]
    if name.startswith('2nd'):assert m.uc.reg_read(reg.UC_ARM64_REG_X4)==2
    symbol=AV.plt[plt];assert name in symbol
    r.update(selected_class=name,original_constructor_symbol=symbol,arguments=[hex(x) for x in actual],
        secondary_argument4=2 if name.startswith('2nd') else None,
        scope='Independent post-allocation precondition; constructor import is not executed and no object is allocated or constructed.')
    return r


def null_state_binding():
    vptr=AV.symbols['_ZTV12UcsStateNull']['va']+0x10;slot=vptr+0x10;matches=[]
    for section in AV.elf.iter_sections():
        if section['sh_type']!='SHT_RELA':continue
        symbols=AV.elf.get_section(section['sh_link'])
        for relocation in section.iter_relocations():
            if relocation['r_offset']!=slot:continue
            symbol=symbols.get_symbol(relocation['r_info_sym'])
            assert relocation['r_info_type']==257 and symbol['st_shndx']!='SHN_UNDEF'
            matches.append({'slot':slot,'vptr':vptr,'type':257,'symbol':symbol.name,
                            'value':symbol['st_value']+relocation['r_addend']})
    assert len(matches)==1 and matches[0]['symbol']=='_ZN12UcsStateNull12RcvEncOpenHDEv'
    return matches[0]


def state_dispatch(binding):
    m=q.BoundaryMicro(AV,[(0x13d4b8,0x13d658)],boundaries={binding['value']:'original_Null_EncOpenHD_entry'})
    manager,state=SCRATCH+0xc000,SCRATCH+0xc800
    m.uc.mem_write(manager+0xa0,p64(state));m.uc.mem_write(state,p64(binding['vptr']))
    # Materialize exactly the original ABS64 S+A slot, not a made-up function
    # return. The older generic harness does not resolve relocation257.
    m.uc.mem_write(binding['slot'],p64(binding['value']))
    w.putregs(m,x19=1,x21=manager)
    r=m.run(0x13d4b8);assert r['reason']=='phase boundary: original_Null_EncOpenHD_entry'
    assert m.uc.reg_read(reg.UC_ARM64_REG_X0)==state and not r['stores']
    r.update(relocation_materialized=binding,
        scope='Assumed-held Ucs mutex and synthetic Null state. Original dispatch reaches handler entry only; actual state, handler and SetState are not executed.')
    return r


def mask_rows(address):
    rows=[]
    for i in range(64):
        value=int.from_bytes(AV.read(address+i*4,4),'little')
        if value==0xffffffff:return rows
        rows.append(value)
    raise AssertionError('mask table missing bounded terminator')


def mask_helper(address,flag,raw):
    rows=mask_rows(address);m=pp.StrictMicro(AV,[(0x13c660,0x13c68c)])
    m.uc.mem_write(SCRATCH,pp.p32(0xffffffff));r=m.run(0x13c660,[SCRATCH,address,raw,flag])
    assert r['reason']=='returned'
    expected=0xffffffff
    if not raw&flag:
        for value in rows:expected&=~value&0xffffffff
    actual=int.from_bytes(m.uc.mem_read(SCRATCH,4),'little');assert actual==expected
    r.update(table_address=hex(address),table_masks=[hex(v) for v in rows],raw_backup_byte_fixture=raw,
        flag=flag,output_mask=hex(actual),
        scope='Pure original bit-mask helper and static table only; no backup read, current device capability, decode start or encode validation.')
    return r


def decoder_mask_copy(value):
    m=pp.StrictMicro(AV,[(0x12a908,0x12a918)],end=0x12a918)
    m.uc.mem_write(FP+0x38,p64(PAYLOAD));m.uc.mem_write(FP+0x34,pp.p32(value))
    m.uc.mem_write(PAYLOAD+0x30,p64(PACKET));w.putregs(m,x29=FP)
    r=m.run(0x12a908);assert r['reason']=='conversion block complete'
    assert int.from_bytes(m.uc.mem_read(PACKET+0x2c,4),'little')==value
    r.update(mask_fixture=hex(value),owning_symbol='_ZN19ExecCmd_MC_DecStart7ExecCmdEPKh',
        scope='Original copy after assumed parameter getter; proves a decode-command consumer, not an encoding capability table.')
    return r


def mask_key_refs():
    section=AV.elf.get_section_by_name('.text');raw=section.data();base=section['sh_addr'];hits=[]
    for offset in range(0,len(raw)-3,4):
        word=struct.unpack_from('<I',raw,offset)[0]
        if word&0x7f800000==0x52800000 and ((word>>5)&0xffff)==0x1030:
            pc=base+offset;owners=[n for n,v in AV.symbols.items() if v['va']<=pc<v['va']+v['size']]
            hits.append({'pc':hex(pc),'owners':owners,'instructions':e.dump_native(AV,pc-16,pc+24)})
    assert [v['pc'] for v in hits]==['0x12a900','0x13cd64']
    assert any('DecStart' in name for name in hits[0]['owners'])
    return hits


def run(out):
    source=BASE/'stage23-encoder-boundary/run-corrected-20261025/encoder-boundary-results.json'
    paths=[AV.path,e.MPR.path,source]+[Path(m.__file__) for m in (e,e.l,e.l.a,w,q,e.l.a.cr,e.l.a.cr.cp,pp,qp)]
    paths += [BASE/'stage4-windows-collab/mac-verification/offline_verify.py']
    hashes={str(p.relative_to(ROOT)):qp.sha(p) for p in paths}
    previous=e.STAGE/'final-receipt.json'
    assert all(qp.sha(ROOT/v['path'])==v['sha256'] for v in json.loads(previous.read_text())['files'])
    jumps=[command_jump(mid,cid) for mid in (0x210,0x1610) for cid in (0,1,5,6)]
    decisions=[ordinary_usecase(fmt) for fmt in (15,18,0x44,0xff)]
    decisions += [ordinary_usecase(15,invalid=True),ordinary_usecase(15,input60=3),
                  ordinary_usecase(15,input60=1),ordinary_usecase(15,input60=2)]
    assert [v['selected_usecase'] for v in decisions]==[1,1,14,1,1,16,None,None]
    creation=[create_selection(cid,second,sub) for cid in (0,1) for second in (0,1) for sub in (0,1)]
    creation += [create_selection(cid,0) for cid in (5,6)]
    constructors=[constructor_arguments(*row) for row in CTOR_SLICES]
    binding=null_state_binding();state=state_dispatch(binding)
    masks=[mask_helper(address,flag,raw) for address,flag in [(0x16a618,1),(0x16a628,2),(0x16a5e8,4),(0x16a458,8)] for raw in (0,0xff)]
    decode=[decoder_mask_copy(value) for value in (0,0xffffffff)]
    refs=mask_key_refs()
    assert hashes=={str(p.relative_to(ROOT)):qp.sha(p) for p in paths}
    regions=[('receiver ExecuteCommand',0xadcf8,0xadea4),('SetCommandId',0xaf304,0xaf6a8),
      ('CreateCommandSequence',0xaf6a8,0xafe48),('Ucs SetCommand',0x13d478,0x13d694),
      ('Null EncOpenHD handler',binding['value'],binding['value']+AV.symbols[binding['symbol']]['size']),
      ('AvailableFormat mask helper',0x13c660,0x13c68c),('AvailableFormat final store',0x13cd60,0x13cd88),
      ('DecodeStart mask consumer',0x12a8c0,0x12aa00)]
    proof={'status':'PASS_ORIGINAL_RECEIVER_SELECTION_AND_DECODE_MASK_SCOPE_ONLY',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'AV_sha256':qp.sha(AV.path),'prior_manifest_sha256':qp.sha(previous),
      'command_jump_cases':jumps,'ordinary_usecase_cases':decisions,'create_selection_cases':creation,
      'constructor_argument_cases':constructors,'assumed_Null_state_dispatch':state,
      'mask_helper_cases':masks,'decoder_mask_copy_cases':decode,'direct_MOVZ_key1030_refs':refs,
      'static_regions':[{'name':n,'start':hex(s),'end_exclusive':hex(z),'instructions':e.dump_native(AV,s,z)} for n,s,z in regions],
      'findings':['For ordinary input selector0 and codec type0x20, MAIN FileFormat15 and proxy18 both choose usecase1; FileFormat0x44 chooses14. Invalid enums can also choose1, so this is sequence selection, not validation.',
        'Under explicit post-getter controller fixtures, command0/1 choose Astra Open/Start when key104a is0 and second-stream variants when it is1. Commands5/6 select dual Open2/Start2. No real controller values or allocation were supplied as successful outputs.',
        'Usecase1 dispatches through the current-state vtable. A synthetic Null-state instance with the original ABS64 relocation reaches RcvEncOpenHD; actual state and SetState remain unexecuted. The HD name is not a resolution acceptance check.',
        'The AvailableFormat mask stored under key0x1030 has a confirmed consumer in ExecCmd_MC_DecStart. Direct constant scan is limited to MOVZ references in this library; no universal absence of encoding consumers is claimed.',
        'The actual MC encoder receiving/validation and replies, live UCS/controller state, resources and hardware Open/Start remain unresolved.'],
      'scope':'Bounded original branches on independent fixtures; no full receiver, controller outputs, singleton/mutex, allocation/constructor, state change, backup, transport, MC or hardware execution.',
      'no_diagnostic_or_native_output_stubs':True,'ABS64_resolution_scope':'One original symbol+addend vtable slot in a guest Null fixture only; no host loader.',
      'actual_EncOpen_Start_or_hardware_acceptance_verified':False,
      'camera_interface_auth_driver_files_module_WBI_or_write':False,'new_remote_attempts':False,
      'modified_firmware_or_patch_exported':False,'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'command_jump_cases':len(jumps),'ordinary_usecase_cases':len(decisions),
      'post_controller_create_cases':len(creation),'constructor_argument_cases':len(constructors),
      'Null_state_entry_dispatch_cases':1,'mask_helper_cases':len(masks),'decoder_mask_copy_cases':len(decode),
      'MAIN_proxy_same_ordinary_usecase':1,'known_mask_consumer':'decode start',
      'actual_hardware_acceptance_verified':False,'goal_complete':False,'persistent_write_release':False}
    qp.write_json(out/'receiver-dispatch-results.json',proof);qp.write_json(out/'summary.json',summary)
    qp.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
      'script_sha256':qp.sha(Path(__file__)),'inputs':hashes,'results_sha256':qp.sha(out/'receiver-dispatch-results.json'),
      'summary_sha256':qp.sha(out/'summary.json'),'previous_manifest_sha256':qp.sha(previous),'volume_uuid':qp.EXPECTED_VOLUME})
    print(json.dumps(summary,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();qp.verify_volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
      with (out/'attempt-source.py').open('xb') as f:f.write(Path(__file__).read_bytes())
      qp.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
