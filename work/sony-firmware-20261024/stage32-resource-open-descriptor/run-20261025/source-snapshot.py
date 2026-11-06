#!/usr/bin/env python3
"""Original resource descriptor fragments on explicit guest-only preconditions.

The runtime clear dispatch and native diagnostic calls are NOT implemented or
stubbed. Each boundary-separated fragment has its own stated precondition. This
does not execute a complete builder, input_if, message transport or hardware.
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
sys.path.insert(0,str(BASE/'stage31-timing-parameter-ownership'))
import timing_parameters as t
r,V=t.r,t.V
OWNER=r.ARENA+0x2e0000
EVENT=r.ARENA+0x2f0000
DESCRIPTOR=r.ARENA+0x300000
RANGES=[(0x1349d0,0x134b70),(0x134bf4,0x134ec0),
 (0x134ec0,0x134f74),(0x134fb0,0x134fc4),(0x134fcc,0x135400),
 (0x13933c,0x1393d4),(0x1394ec,0x139574),(0x1396f4,0x139790),
 (0x1a25a8,0x1a261c),(0x1a26d0,0x1a26e0),(0xd80,0xeec)]
BOUNDARIES={0x2f67c:'before_unbound_runtime_clear_dispatch',
 0x27d528:'before_native_diagnostic',0xa3b04:'before_native_exception',
 0x135400:'before_descriptor_dump',0x135df8:'before_resource_sender'}


def reset_without_stack(m):
    """Start an independent fragment trace without changing its frame fixture."""
    m.reason=None;m.pcs=[];m.writes=[]


def u32(data,at):return struct.unpack_from('<I',data,at)[0]


def describe(value):
    assert len(value)==0x88
    return {'channel_id':u32(value,0),'format_category_enum':u32(value,4),
      'width':struct.unpack_from('<H',value,8)[0],
      'height':struct.unpack_from('<H',value,10)[0],
      'mode_scalar':u32(value,0xc),'packet7a_scalar':u32(value,0x10),
      'config_source_id_fixture':hex(u32(value,0x14)),
      'coding_enum':u32(value,0x18),'event_d0_scalar':u32(value,0x1c),
      'progressive_conversion_copy':u32(value,0x20),
      'frame_enum':u32(value,0x24),'interlace_enum':u32(value,0x28),
      'raw_mode_enum':u32(value,0x2c),'quality_enum':u32(value,0x38),
      'raw67_equals1_flag':u32(value,0x74),'chroma_enum':u32(value,0x78),
      'depth_enum':u32(value,0x7c),
      'field_names_scope':'Source-offset labels except names confirmed by original dump strings; enum values are not literal bitrate, rational rate or hardware capability.'}


def fixture(blob,packet,fmt,prepared):
    m=r.RawGuest(blob,RANGES,BOUNDARIES)
    event=bytearray(prepared)
    struct.pack_into('<Q',event,8,EVENT+0x28)
    m.uc.mem_write(EVENT,bytes(event))
    m.uc.mem_write(OWNER,r.p64(t.f.CTX))
    m.uc.mem_write(t.f.CTX,r.p64(r.CONFIG))
    m.uc.mem_write(r.CONFIG+8,struct.pack('<B',0))
    m.uc.mem_write(r.CONFIG+0xc,struct.pack('<I',0x805700f9))
    assert bytes(event[0x28:0xc0])==packet and event[0x1c]==fmt
    return m,bytes(event)


def sender_prefix(blob,descriptor):
    m=r.RawGuest(blob,[(0x135df8,0x135e30),(0xd80,0xeec)],
        {0x960a4:'before_message_object_constructor'})
    m.uc.mem_write(DESCRIPTOR,descriptor)
    m.regs(x0=OWNER,x1=DESCRIPTOR)
    result=m.run(0x135df8)
    assert result['reason']=='boundary: before_message_object_constructor'
    sp=m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    envelope=m.read(sp+0x1b0,0x90)
    assert envelope[:8]==struct.pack('<HHHH',0x2103,0x100,0x90,0)
    assert envelope[8:]==descriptor
    result.update(envelope_hex=envelope.hex(),CID='0x2103',MID='0x0100',
      length=0x90,descriptor88_copied_unchanged=True,
      precondition='Independent resource-sender prefix with descriptor from separate fragments supplied as explicit input; builder dump and sender call site not executed.',
      scope='Original stack header and memcpy only; no message construction/serialization, source/destination binding, actual send, resource handler or hardware reply.')
    return result


def descriptor_case(blob,label,packet,fmt,expect='complete'):
    upstream=t.open_action(blob,label,packet,fmt)
    assert upstream['prepared_event_hex']
    m,event=fixture(blob,packet,fmt,bytes.fromhex(upstream['prepared_event_hex']))
    m.regs(x0=OWNER,x1=EVENT)
    prefix=m.run(0x1349d0)
    assert prefix['reason']=='boundary: before_unbound_runtime_clear_dispatch'
    assert m.read(OWNER+0x20,0x98)==packet
    assert u32(m.read(OWNER+0xc0,4),0)==fmt
    sp=m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==sp+8
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X1)==0
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X2)==0x88
    prefix.update(copied_video98_unchanged=True,FileFormat=fmt,
       requested_clear={'pointer':hex(sp+8),'fill':0,'bytes':0x88},
       scope='Original builder entry through copy and clear-call arguments; runtime clear function not executed.')

    # Explicit NEW fragment input. This is not a runtime clear implementation,
    # returned-value hook, PC<-LR adapter, or evidence of actual clear completion.
    m.uc.mem_write(sp+8,bytes(0x88))
    reset_without_stack(m)
    calculation=m.run(0x134a1c)
    assert calculation['reason']=='boundary: before_native_diagnostic'
    assert m.pcs[-2]==V+0x134f70
    raw_mode=m.uc.reg_read(r.reg.UC_ARM64_REG_W20)
    assert raw_mode==0
    calculation.update(computed_callee_saved_raw_mode=raw_mode,
       partial_descriptor_hex=m.read(sp+8,0x88).hex(),
       precondition='Independent post-clear entry0x134a1c: explicit zeroed0x88 stack input and original prefix frame/register fixtures. Runtime clear has not run.',
       scope='Original scalar/dimension-independent prefix and raw-mode helper through first diagnostic; no diagnostic or complete builder acceptance.')

    # Another independent fragment begins at the original helper epilogue.
    # It uses the helper-computed callee-saved W20 and original saved frame.
    # Excluded diagnostics may have other effects: they are NOT proven neutral.
    reset_without_stack(m)
    suffix=m.run(0x134fb0)
    if expect=='complete':
        assert suffix['reason']=='boundary: before_descriptor_dump'
        assert m.uc.reg_read(r.reg.UC_ARM64_REG_X1)==sp+8
        value=m.read(sp+8,0x88)
        fields=describe(value)
        assert (fields['width'],fields['height'])==(
            int.from_bytes(packet[0x68:0x6a],'little'),int.from_bytes(packet[0x6a:0x6c],'little'))
        assert fields['coding_enum']==(14 if fmt==15 else 21)
        assert fields['interlace_enum']==0
        assert fields['chroma_enum']==0 and fields['depth_enum']==1
        sent=sender_prefix(blob,value)
    else:
        assert suffix['reason']=='boundary: before_native_diagnostic'
        callsite=V+(0x135334 if expect=='chroma_diagnostic' else 0x1353a8)
        # Keep the exact observed callsite, then verify it falls within the
        # appropriate original converter. Native diagnostics are not executed.
        lo,hi=(0x1352f8,0x13538c) if expect=='chroma_diagnostic' else (0x13538c,0x135400)
        assert V+lo<=m.pcs[-2]<V+hi
        value=None;fields=None;sent=None
        suffix['diagnostic_caller_offset']=hex(m.pcs[-2]-V)
    suffix.update(precondition='Independent original epilogue0x134fb0 plus caller suffix: assume excluded diagnostics completed without changing callee-saved state, saved frame or descriptor storage. This condition is not established by executing diagnostics.',
       scope='Original post-diagnostic scalar return and remaining descriptor writes only; not a contiguous whole builder, input component or resource acceptance.')
    assert m.read(EVENT,0xd4)==event and m.read(OWNER+0x20,0x98)==packet
    return {'label':label,'input_FileFormat':fmt,'input_fields':t.fields(packet),
      'input_packet_hex':packet.hex(),'upstream_Open_action':upstream,
      'builder_prefix':prefix,'independent_post_clear_prefix':calculation,
      'independent_post_diagnostic_suffix':suffix,
      'descriptor_hex':value.hex() if value else None,'descriptor_fields':fields,
      'independent_sender_prefix':sent,
      'continuous_builder_execution':False,'native_dependency_or_output_adapters':False}


def coding_controls(blob):
    cases=[]
    for fmt,expected in ((15,14),(18,21)):
        for codec in (0,15,255):
            m=r.RawGuest(blob,[(0x134d44,0x134ec0)],BOUNDARIES)
            m.regs(x0=OWNER,x1=fmt,x2=codec)
            result=m.run(0x134d44)
            assert result['reason']=='returned'
            out=m.uc.reg_read(r.reg.UC_ARM64_REG_W0)
            assert out==expected
            cases.append(dict(result,FileFormat=fmt,packet_codec66=codec,
              coding_enum=out,scope='Original pure format-to-coding converter. FileFormat15/18 branches ignore codec argument; not support validation.'))
    return cases


def static_evidence(blob):
    regions=[('input_if direct setup',0x1454f4,0x145530),
      ('input parent preparation',0x134568,0x1345dc),
      ('parent and descriptor-owner construction',0x1344a8,0x1344fc),
      ('descriptor owner construction',0x13494c,0x1349d0),
      ('descriptor building and sender call site',0x1349d0,0x134be4),
      ('frame converter',0x134bf4,0x134cc4),
      ('progressive converter',0x134cc4,0x134d44),
      ('format-to-coding converter',0x134d44,0x134ec0),
      ('raw-mode converter including excluded diagnostics',0x134ec0,0x134fc4),
      ('quality converter',0x134fcc,0x1352f8),
      ('chroma converter',0x1352f8,0x13538c),
      ('depth converter',0x13538c,0x135400),
      ('descriptor dump semantic references',0x135400,0x135df8),
      ('resource sender',0x135df8,0x135ef4),
      ('format category converter',0x13933c,0x1393d4),
      ('optional parameter selector',0x1394ec,0x139574),
      ('optional parameter construction',0x1396f4,0x139790),
      ('height interlace selector',0x1a26d0,0x1a26e0),
      ('runtime clear dispatch',0x2f67c,0x2f690)]
    rows=[{'name':name,'instructions':r.im.dump(blob,a,z,V)} for name,a,z in regions]
    md=r.capstone.Cs(r.capstone.CS_ARCH_ARM64,r.capstone.CS_MODE_ARM);md.detail=True
    ins=list(md.disasm(blob[0x135400:0x135df8],V+0x135400));labels=[]
    for i,j in zip(ins,ins[1:]):
        if i.mnemonic=='adrp' and j.mnemonic=='add' and len(i.operands)==2 and len(j.operands)==3:
            if i.operands[0].reg==j.operands[1].reg and j.operands[2].type==r.capstone.CS_OP_IMM:
                off=((i.operands[1].imm+j.operands[2].imm)&((1<<64)-1))-V
                if 0x416000<=off<0x419000:
                    try:label=r.im.cstring(blob,off,200)
                    except (AssertionError,UnicodeDecodeError):continue
                    labels.append({'adrp_offset':hex(i.address-V),'string_offset':hex(off),'text':label})
    assert any('channel_id' in x['text'] for x in labels)
    return {'regions':rows,'bounded_descriptor_diagnostic_labels':labels,
      'unexecuted_native_boundaries':['0x2f67c runtime clear dispatch through image header+20/API+6b8',
        '0x134f70..0x134fb0 raw-mode diagnostics','0x135400 descriptor dump',
        '0x0960a4 message object constructor and all subsequent serializer/send/resource replies'],
      'parent_preparation_gap':'Input parent0x134568 first calls outputIF0x14f96c; full dependency/state and complete input_if not executed.',
      'scope':'Local original byte/disassembly/label evidence only; runtime API identity, receiver and hardware not resolved.'}


def run(out):
    prior=t.STAGE/'final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='fe9f989a43aec83ced9b1a5a861efecea1d1c111007d10203bf0d98365fe8180'
    verified={}
    for name in ('stage25-mc-image-map','stage26-mc-open-routing','stage28-main-frontend-binding','stage31-timing-parameter-ownership'):
        manifest=json.loads((BASE/name/'final-receipt.json').read_text())
        assert all(r.im.sha((ROOT/x['path']).read_bytes())==x['sha256'] for x in manifest['files'])
        verified[name]=len(manifest['files'])
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    target,proxy,uhd,_=r.packet_variants()
    cases=[descriptor_case(blob,*x) for x in (target,proxy,uhd)]
    for label,off,expect in [('codecFF control',0x66,'complete'),
          ('chromaFF control',0x94,'chroma_diagnostic'),('depthFF control',0x95,'depth_diagnostic')]:
        packet=bytearray(target[1]);packet[off]=255
        cases.append(descriptor_case(blob,label,bytes(packet),15,expect))
    controls=coding_controls(blob)
    assert cases[0]['descriptor_fields']['quality_enum']==4
    assert cases[0]['descriptor_hex']==cases[3]['descriptor_hex']
    proof={'status':'PASS_ORIGINAL_RESOURCE_DESCRIPTOR_FRAGMENTS_WITH_EXPLICIT_NATIVE_GAPS',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'cases':cases,'pure_coding_converter_controls':controls,'static_evidence':static_evidence(blob),
      'prior_manifest_files_verified':verified,
      'refinement':'Prior codecFF control is an unused-inner-argument control for FileFormat15/18 conversion, not evidence of failed mandatory validation. Outer format selects14/21.',
      'scope':'Independent original fragments with explicit zero-stack and post-diagnostic preconditions; full builder and input_if dependencies, message transport, resource reply and hardware unexecuted.',
      'continuous_builder_executed':False,'native_output_or_diagnostic_adapters':False,
      'camera_or_remote_access_attempted':False,'hardware_or_restore_verified':False,
      'modified_firmware_or_patch_exported':False,'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'descriptor_scenarios':len(cases),
      'complete_fragment_descriptors':sum(x['descriptor_hex'] is not None for x in cases),
      'pure_coding_converter_cases':len(controls),
      'target':cases[0]['descriptor_fields'],'proxy':cases[1]['descriptor_fields'],
      'UHD_control':cases[2]['descriptor_fields'],
      'resource_envelope':{'CID':'0x2103','MID':'0x0100','length':'0x90'},
      'continuous_builder_or_hardware_or_restore_verified':False,'goal_complete':False,'persistent_write_release':False}
    assert r.im.sha(blob)==r.im.sha(image.read_bytes())
    r.im.write_json(out/'resource-descriptor-results.json',proof)
    r.im.write_json(out/'summary.json',summary)
    r.im.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
      'script_sha256':r.im.sha(Path(__file__).read_bytes()),'timing_helper_sha256':r.im.sha(Path(t.__file__).read_bytes()),
      'raw_guest_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),
      'map_helper_sha256':r.im.sha(Path(r.im.__file__).read_bytes()),
      'raw_image_sha256':r.im.sha(blob),'prior_manifest_sha256':r.im.sha(prior.read_bytes()),
      'volume_uuid':r.im.VOLUME,'proof_sha256':r.im.sha((out/'resource-descriptor-results.json').read_bytes()),
      'summary_sha256':r.im.sha((out/'summary.json').read_bytes())})
    print(json.dumps(summary,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();r.im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        with (out/'attempt-source.py').open('xb') as h:h.write(Path(__file__).read_bytes())
        r.im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
