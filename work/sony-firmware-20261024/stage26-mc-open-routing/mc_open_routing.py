#!/usr/bin/env python3
"""Original MC route/state/copy fragments on explicit guest-only fixtures.

No native output adapter, task hook, resource, transport, real OSAL registration,
hardware encoder, host firmware loader or camera interface is executed.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

import capstone
import unicorn
from unicorn import arm64_const as reg

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'work/sony-firmware-20261024'
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'stage25-mc-image-map'))
import mc_image_map as im
sys.path.insert(0,str(BASE/'stage24-receiver-dispatch'))
import receiver_dispatch as d
V=im.A64_BASE
ARENA,ARENA_SIZE=0x11000000,0x400000
STACK,STACK_SIZE,SP=0x10000000,0x10000,0x10008000
STOP=0x12000000
CONFIG,MSGIF,HEADER,PACKET,DECODER,ENCODER,WRAPPER=(ARENA+n for n in (0,0x1000,0x2000,0x3000,0x4000,0x10000,0x200000))
NORMAL,CACHE=WRAPPER+0x18,WRAPPER+0x690
SOURCE_FIXTURE=0x1234


def p64(value):return struct.pack('<Q',value)


class RawGuest:
    def __init__(self,blob,ranges,boundaries):
        self.blob=blob
        self.ranges=[(V+a,V+b) for a,b in ranges]
        self.boundaries={V+p:name for p,name in boundaries.items()}
        self.uc=unicorn.Uc(unicorn.UC_ARCH_ARM64,unicorn.UC_MODE_ARM)
        self.uc.mem_map(V,(len(blob)+4095)&~4095,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC)
        self.uc.mem_write(V,blob)
        for start,size in ((ARENA,ARENA_SIZE),(STACK,STACK_SIZE)):
            self.uc.mem_map(start,size,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        self.uc.mem_map(STOP,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC)
        self.uc.reg_write(reg.UC_ARM64_REG_SP,SP)
        self.uc.reg_write(reg.UC_ARM64_REG_X30,STOP)
        self.md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM)
        self.pcs=[];self.writes=[];self.reason=None
        self.uc.hook_add(unicorn.UC_HOOK_CODE,self.code)
        self.uc.hook_add(unicorn.UC_HOOK_MEM_WRITE,self.store)
        self.uc.hook_add(unicorn.UC_HOOK_MEM_INVALID,self.invalid)

    def stop(self,reason):
        self.reason=reason;self.uc.emu_stop()

    def code(self,u,pc,size,user):
        self.pcs.append(pc)
        if pc==STOP:return self.stop('returned')
        if pc in self.boundaries:return self.stop('boundary: '+self.boundaries[pc])
        if not any(a<=pc and pc+size<=b for a,b in self.ranges):
            return self.stop('unapproved execution '+hex(pc))
        instruction=next(self.md.disasm(bytes(u.mem_read(pc,size)),pc),None)
        if instruction is None or instruction.mnemonic in {
            'svc','hvc','smc','msr','mrs','dc','ic','at','tlbi','sys','brk','hlt','udf'}:
            return self.stop('unapproved instruction '+hex(pc))

    def store(self,u,access,address,size,value,user):
        if not any(a<=address and address+size<=a+b for a,b in ((ARENA,ARENA_SIZE),(STACK,STACK_SIZE))):
            return self.stop('unapproved write '+hex(address))
        self.writes.append({'pc':hex(u.reg_read(reg.UC_ARM64_REG_PC)),
                            'address':hex(address),'size':size})

    def invalid(self,u,access,address,size,value,user):
        self.stop('invalid guest memory '+hex(address));return False

    def regs(self,**values):
        for name,value in values.items():
            self.uc.reg_write(getattr(reg,'UC_ARM64_REG_'+name.upper()),value)

    def read(self,address,count):return bytes(self.uc.mem_read(address,count))

    def run(self,start):
        self.uc.emu_start(V+start,0,count=2000,timeout=100000)
        assert self.reason is not None, 'instruction/time limit reached without expected boundary'
        return {'start_offset':hex(start),'reason':self.reason,'stop_pc':hex(self.uc.reg_read(reg.UC_ARM64_REG_PC)),
          'pcs':[hex(p) for p in self.pcs],'writes':self.writes,
          'x0_to_x5':[hex(self.uc.reg_read(getattr(reg,'UC_ARM64_REG_X'+str(n)))) for n in range(6)],
          'native_output_or_diagnostic_adapters':False}


def packet_variants():
    source=json.loads((BASE/'stage23-encoder-boundary/run-corrected-20261025/encoder-boundary-results.json').read_text())
    cases=[(source['packet_cases'][n]['label'],bytes.fromhex(source['packet_cases'][n]['packet_hex']),fmt)
           for n,fmt in ((0,15),(1,18),(3,15))]
    invalid=bytearray(cases[0][1]);invalid[0x66]=invalid[0x80]=0xff
    cases.append(('invalid codec/frame fixture',bytes(invalid),15))
    return cases


def seed(m,packet,fmt=15,cid=0,pointer=PACKET,decoder_active=0):
    header=bytearray(0x38)
    struct.pack_into('<HHH',header,0,0x2003,0x201,0x38)
    struct.pack_into('<H',header,0xa,cid)
    struct.pack_into('<Q',header,0x10,pointer)
    struct.pack_into('<I',header,0x18,0x98)
    header[0x20]=0x20;header[0x24]=fmt
    struct.pack_into('<I',header,0x2c,0x210)
    m.uc.mem_write(HEADER,bytes(header));m.uc.mem_write(PACKET,packet)
    m.uc.mem_write(CONFIG+0xc,struct.pack('<I',SOURCE_FIXTURE))
    for off,value in [(0,CONFIG),(0x18,ENCODER),(0x20,DECODER)]:
        m.uc.mem_write(MSGIF+off,p64(value))
    m.uc.mem_write(DECODER+0x490,bytes([decoder_active]))
    m.uc.mem_write(ENCODER+0x116980,p64(WRAPPER))
    m.uc.mem_write(WRAPPER,p64(V+0x367b20))
    m.uc.mem_write(WRAPPER+0x10,p64(NORMAL))
    m.uc.mem_write(NORMAL,p64(V+0x36bca8))
    m.uc.mem_write(CACHE,p64(V+0x367d38))
    return bytes(header)


def converters():
    output=[]
    for label,start,end,args,expected in [
        ('internal CID5',0x140d48,0x140d6c,[0,5],0x2003),
        ('MC internal MID0x520',0x140eac,0x140eec,[0,0x520],0x201)]:
        m=d.pp.StrictMicro(d.AV,[(start,end)],resolve=True)
        r=m.run(start,args);assert r['reason']=='returned'
        value=m.uc.reg_read(reg.UC_ARM64_REG_X0);assert value==expected
        r.update(label=label,output_value=hex(value),scope='Original pure converter only; no message transport or hardware.')
        output.append(r)
    assert d.AV.read(0x16afac+5,1)==b'\x05'
    assert d.AV.plt[0xa15f0]=='_ZN11ObjAvbbcCmn17ConvertCmdMidToMcEt'
    return output


def route(blob,label,packet,fmt,decoder_active=0):
    m=RawGuest(blob,[(0xa12d8,0xa19f4),(0xa8920,0xa8928),(0xb1e04,0xb1e0c),
                    (0x12c81c,0x12c834),(0x168e9c,0x168f78)],
               {0x168f78:'before_unexecuted_task_hook',0xa88a8:'decoder_active_path_entry'})
    header=seed(m,packet,fmt,decoder_active=decoder_active)
    m.regs(x0=MSGIF,x1=HEADER,x2=0x38,x3=SOURCE_FIXTURE)
    r=m.run(0xa12d8)
    assert r['reason']=='boundary: '+('decoder_active_path_entry' if decoder_active else 'before_unexecuted_task_hook')
    assert m.read(HEADER,0x38)==header
    after=m.read(PACKET,0x98)
    assert after[:0x67]+after[0x68:]==packet[:0x67]+packet[0x68:]
    assert after[0x67]==0
    r.update(label=label,decoder_active_fixture=decoder_active,raw_packet67_after=after[0x67],
      actual_source_ID_observed=False,
      preconditions={'source_ID':hex(SOURCE_FIXTURE),'config_source_matches':True,
        'physical_address_conversion':'Bypassed by original equal-owner branch; not executed or proven',
        'object_graph_and_state':'Independent synthetic fixtures following observed constructor pointer wiring',
        'decoder_active_byte':'Synthetic value read by original0xb1e04, no getter-output stub'},
      scope='Original ordinary MC route into state wrapper, stopping before task hook. Invalid video enums can reach same boundary; no format acceptance.')
    return r


def state_selection(blob,cache_flag):
    m=RawGuest(blob,[(0x168f18,0x168f78)],{0x177934:'normal_state_handler_entry',0x169268:'cache_state_handler_entry'})
    raw=bytearray(packet_variants()[0][1]);raw[0x88]=cache_flag
    seed(m,bytes(raw));m.regs(x22=WRAPPER,x23=PACKET,x19=HEADER,x20=SOURCE_FIXTURE,x21=0x38)
    r=m.run(0x168f18)
    chosen=CACHE if cache_flag else NORMAL
    target=struct.unpack_from('<Q',blob,(0x367d38 if cache_flag else 0x36bca8))[0]
    # Stop at the original table value even if an unknown build changes it.
    assert int(r['stop_pc'],16)==target
    assert r['reason'].startswith('boundary: ')
    assert int.from_bytes(m.read(WRAPPER+0x10,8),'little')==chosen
    r.update(raw_packet88_fixture=cache_flag,selected_state_pointer=hex(chosen),
      precondition='Independent post-task-hook fragment; hook0x168f78 and its effects not executed. Current object graph is a fixture.',
      scope='Original raw-byte state choice and vtable entry dispatch only; no state handler executed.')
    return r


def command_dispatch(blob,cid):
    targets={struct.unpack_from('<Q',blob,0x36b990+i*8)[0]-V for i in range(9)}
    m=RawGuest(blob,[(0x177a78,0x177a94)],{p:'original_command_destination' for p in targets})
    seed(m,packet_variants()[0][1],cid=cid);m.regs(x22=HEADER)
    r=m.run(0x177a78)
    expected=(struct.unpack_from('<Q',blob,0x36b990+cid*8)[0] if cid<9 else V+0x178238)
    assert int(r['stop_pc'],16)==expected and not r['writes']
    r.update(command_id=cid,scope='Original post-state-hook/post-metadata command switch only. Selected body and preceding hooks not executed.')
    return r


def open_copy(blob,label,packet,fmt,null=False):
    m=RawGuest(blob,[(0x177ad8,0x177b18),(0xd80,0xeec)],{0x177b18:'before_open_parameter_dependencies'})
    header=seed(m,packet,fmt,pointer=0 if null else PACKET)
    m.regs(x19=NORMAL,x23=HEADER+8,x22=HEADER,x20=0x38)
    r=m.run(0x177ad8);assert r['reason']=='boundary: before_open_parameter_dependencies'
    assert m.read(HEADER,0x38)==header and m.read(PACKET,0x98)==packet
    saved=bytearray(m.read(NORMAL+0x28,0x28));original=bytearray(header[8:0x30])
    if not null:
        struct.pack_into('<Q',original,8,NORMAL+0x50)
        struct.pack_into('<I',original,0x10,0x98)
        assert m.read(NORMAL+0x50,0x98)==packet
    assert saved==original
    assert int.from_bytes(m.read(NORMAL+0xe8,4),'little')==0x38
    r.update(label=label,null_packet_fixture=null,FileFormat_after=m.read(NORMAL+0x44,1)[0],
      packet98_copied_unchanged=not null,header_and_source_packet_unchanged=True,
      precondition='Independent post-command0 setup; earlier task/state/diagnostic hooks not executed. Guest inputs are fixtures.',
      scope='Original0x28 header-copy and conditional0x98 packet-copy including original copy routine; no codecs/resources/Open replies.')
    return r


def static_evidence(blob):
    regions=[('upstream MC Open sender',0xb1694,0xb178c),
             ('pure CID converter',0x140d48,0x140d6c),
             ('pure MC MID converter',0x140eac,0x140eec),
             ('generic MID group dispatch',0x141660,0x1416c8)]
    raw_regions=[('MC message route',0xa12d8,0xa19f4),
      ('McApp constructor fields and encoder pointer wiring',0xa5aac,0xa5bd4),
      ('sfmc encoder current-state pointer load',0x12c81c,0x12c834),
      ('state wrapper message and raw88 selection',0x168e9c,0x168f78),
      ('normal parser through raw packet copy',0x177934,0x177b20),
      ('original bounded memcpy',0xd80,0xeec),
      ('original decoder-active getter',0xa8920,0xa8928),
      ('original decoder-active byte load',0xb1e04,0xb1e0c)]
    table=struct.unpack_from('<9Q',blob,0x36b990)
    assert table[0]==V+0x177a94
    cache=im.vtable(blob,0x367d28,'N8sfmc_enc23sfmc_enc_state_cacherecE')
    return {'upstream_ELF_regions':[{'name':n,'instructions':d.e.dump_native(d.AV,a,z)} for n,a,z in regions],
      'raw_regions':[{'name':n,'start_offset':hex(a),'end_offset_exclusive':hex(z),
                      'instructions':im.dump(blob,a,z,V)} for n,a,z in raw_regions],
      'normal_vtable':im.vtable(blob,0x36bc98,'N8sfmc_enc21sfmc_enc_state_normalE'),
      'wrapper_vtable':im.vtable(blob,0x367b10,'N8sfmc_enc14sfmc_enc_stateE'),
      'cache_vtable':cache,'normal_command_table':[{'cid':i,'target':hex(v)} for i,v in enumerate(table)],
      'constructor_pointer_graph':{'root_encoder_object':'McApp+0x2d00 constructed by0xa60dc',
        'message_router':'McApp+0x308', 'router_encoder_field':'router+0x18 == McApp+0x320 stores the encoder object pointer',
        'encoder_state_field':'encoder+0x116980','actual_OSAL_registration_or_live_objects_verified':False}}


def run(out):
    previous=BASE/'stage25-mc-image-map/final-receipt.json'
    assert im.sha(previous.read_bytes())=='f8c2b75533a2da9a8bb41770763e54e5292f05de9380cb84629092323213a824'
    assert all(im.sha((ROOT/f['path']).read_bytes())==f['sha256'] for f in json.loads(previous.read_text())['files'])
    prior_inputs=json.loads((d.STAGE/'run-20261025/source-receipt.json').read_text())['inputs']
    assert all(im.sha((ROOT/name).read_bytes())==expected for name,expected in prior_inputs.items())
    inputs={str(d.AV.path.relative_to(ROOT)):im.sha(d.AV.path.read_bytes()),
      str((BASE/'stage2/extraction/files/nflasha3/av-cam.bin').relative_to(ROOT)):im.PINS['stage2/extraction/files/nflasha3/av-cam.bin'],
      str((BASE/'stage23-encoder-boundary/run-corrected-20261025/encoder-boundary-results.json').relative_to(ROOT)):
        im.sha((BASE/'stage23-encoder-boundary/run-corrected-20261025/encoder-boundary-results.json').read_bytes())}
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    conversion=converters();variants=packet_variants()
    routes=[route(blob,*v) for v in variants]
    routes.append(route(blob,'target with active decoder fixture',variants[0][1],15,1))
    states=[state_selection(blob,v) for v in (0,1)]
    commands=[command_dispatch(blob,v) for v in range(10)]
    copies=[open_copy(blob,*v) for v in variants]
    copies.append(open_copy(blob,'null packet control',variants[0][1],15,True))
    proof={'status':'PASS_ORIGINAL_MC_ROUTE_STATE_AND_PACKET_COPY_FRAGMENTS_ONLY',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'pure_converter_cases':conversion,'MC_route_cases':routes,'post_hook_state_cases':states,
      'normal_command_dispatch_cases':commands,'post_hook_open_copy_cases':copies,
      'static_evidence':static_evidence(blob),
      'findings':[
        'Original group5/internal0x520 converts to CID0x2003/MID0x201, matching the raw MC message parser; these are distinct from original payload message0x210 and command0.',
        'Constructor pointer stores bind the message router encoder field to the sfmc_enc object. Actual OSAL queue registration, sender source identity and live initialized objects remain unobserved.',
        'Under explicit equal-owner address and inactive-decoder fixtures, target, proxy, factory control and invalid video enums reach the same encoder state task-hook boundary. No hardware or format acceptance follows from this.',
        'Independent original post-hook fragment selects normal/cache state via packet raw0x88 and dispatches the real vtable; the excluded task hook remains a necessary unresolved dependency.',
        'Normal command0 copies the raw0x98 packet into state-owned storage without changing video enums in this fragment. Validation, resource calls, replies and actual Open/Start remain unexecuted.'],
      'scope':'Bounded original A64 fragments on independent fixtures. Separate fragments are not an end-to-end execution. No native output adapters or fake successful backend returns.',
      'raw_guest_high_address_model':'Original encoded instructions and original absolute table values at static candidate VAs; guest mappings are analysis coordinates, not actual camera MMU or loader state.',
      'task_hooks_state_transitions_resources_transport_or_hardware_executed':False,
      'actual_MC_registration_or_hardware_acceptance_verified':False,
      'camera_or_remote_access_attempted':False,'modified_firmware_or_patch_exported':False,
      'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'pure_converters':len(conversion),'MC_route_cases':len(routes),
      'post_hook_state_cases':len(states),'normal_command_dispatch_cases':len(commands),
      'post_hook_open_copy_cases':len(copies),'native_output_adapters':False,
      'actual_OSAL_registration_or_format_acceptance_verified':False,
      'camera_or_remote_access_attempted':False,'goal_complete':False,'persistent_write_release':False}
    assert all(im.sha((ROOT/p).read_bytes())==h for p,h in inputs.items())
    im.write_json(out/'mc-open-routing-results.json',proof);im.write_json(out/'summary.json',summary)
    im.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
      'script_sha256':im.sha(Path(__file__).read_bytes()),'inputs':inputs,
      'prior_harness_inputs_checked':prior_inputs,'previous_manifest_sha256':im.sha(previous.read_bytes()),
      'volume_uuid':im.VOLUME,'unicorn_version':unicorn.__version__,'capstone_version':capstone.__version__,
      'result_sha256':im.sha((out/'mc-open-routing-results.json').read_bytes()),
      'summary_sha256':im.sha((out/'summary.json').read_bytes())})
    print(json.dumps(summary,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        with (out/'attempt-source.py').open('xb') as f:f.write(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
