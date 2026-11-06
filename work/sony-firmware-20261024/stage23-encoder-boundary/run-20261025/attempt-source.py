#!/usr/bin/env python3
"""Pinned encoder-library inspection; no native loader or camera access."""
from pathlib import Path
import io
import hashlib
import json
import struct
import sys
import argparse
import datetime
import traceback

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'work/sony-firmware-20261024'
STAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'stage22-lifetime-registry'))
import lifetime_registry as l
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM


class PinnedNative:
    def __init__(self, path, expected):
        self.path = Path(path)
        self.blob = self.path.read_bytes()
        assert hashlib.sha256(self.blob).hexdigest() == expected
        self.elf = ELFFile(io.BytesIO(self.blob))
        assert self.elf['e_machine'] == 'EM_AARCH64'
        self.segments = [s for s in self.elf.iter_segments() if s['p_type'] == 'PT_LOAD']
        self.md = Cs(CS_ARCH_ARM64, CS_MODE_ARM); self.md.detail = True
        sym = self.elf.get_section_by_name('.dynsym')
        self.symbols = {s.name: {'va': s['st_value'], 'size': s['st_size']}
                        for s in sym.iter_symbols() if s.name and s['st_shndx'] != 'SHN_UNDEF'}
        ps, pr = self.elf.get_section_by_name('.plt'), self.elf.get_section_by_name('.rela.plt')
        self.plt = {ps['sh_addr'] + 32 + i * 16: sym.get_symbol(r['r_info_sym']).name
                    for i,r in enumerate(pr.iter_relocations())} if ps and pr else {}

    def read(self, address, count):
        for s in self.segments:
            if s['p_vaddr'] <= address and address + count <= s['p_vaddr'] + s['p_filesz']:
                start = s['p_offset'] + address - s['p_vaddr']
                return self.blob[start:start+count]
        raise ValueError(f'not file-backed: {address:x}+{count:x}')

    def dump(self, start, end):
        return [{'va': hex(i.address), 'bytes': i.bytes.hex(), 'asm': i.mnemonic + ' ' + i.op_str}
                for i in self.md.disasm(self.read(start, end-start), start)]


AV = PinnedNative(STAGE / 'inputs/libInfraAvbbc.so', '87a2246084567abca0e43228b5289bc728839a13ab4251e92828ea4c463e3c26')
MPR = l.a.cr.MPR
pp, qp, q, w, reg = l.pp, l.qp, l.q, l.w, l.reg
SCRATCH, FP = w.SCRATCH, w.FP
PACKET, HEADER, RECEIVED = SCRATCH + 0x2000, SCRATCH + 0x6000, SCRATCH + 0x8000


def packet_case(label, values, proxy=False):
    entry, end, offset = (0xd166c,0xd18d8,0x780) if proxy else (0xd13f8,0xd166c,0x764)
    ranges=[(entry,end)]+list(pp.PACKET_RANGES[1:])
    m=pp.StrictMicro(MPR,ranges,resolve=True,logging_adapter=True)
    m.uc.mem_write(SCRATCH+offset,struct.pack('<4I',*values,0))
    r=m.run(entry,[SCRATCH,PACKET]);assert r['reason']=='returned'
    raw=bytes(m.uc.mem_read(PACKET,0x98))
    r.update(label=label,proxy_parameter_builder=proxy,input_vpc_quality_frame=values,
        packet_hex=raw.hex(),fields={'raw_flag_64':raw[0x64],
          'GetCodecAudioFormat_result_65':raw[0x65],'video_codec_66':raw[0x66],
          'width':int.from_bytes(raw[0x68:0x6a],'little'),'height':int.from_bytes(raw[0x6a:0x6c],'little'),
          'codec_FramePerSec_enum_80':raw[0x80],'progressive_flag_81':raw[0x81],
          'mpr_quality_82':raw[0x82],'raw_capture_rate_86':int.from_bytes(raw[0x86:0x88],'little'),
          'chroma_94':raw[0x94],'bitdepth_95':raw[0x95]},
        buffers_and_unlisted_flags='Synthetic zero inputs; no actual buffers, address translation, receiver, Open or Start.',
        logging_adapter='Existing MPR diagnostic PC<-LR only, original nonconsumption proof; no output/return-value writes')
    return r,raw


def codec_identity(vpc, stream):
    m=pp.StrictMicro(MPR,[(0xcd40c,0xcd4f8)],logging_adapter=True)
    r=m.run(0xcd40c,[vpc,stream]);assert r['reason']=='returned'
    r.update(vpc=vpc,stream_type=stream,codec_FileFormat_value=m.uc.reg_read(reg.UC_ARM64_REG_X0),
        binding='Original enqueue stores this return at exec+0x77c for MAIN; ExecEncOpen passes it as Codec::EncOpen FileFormat.')
    return r


def quality_conversion(value):
    m=pp.StrictMicro(MPR,[(0x2823a0,0x2823b0)])
    r=m.run(0x2823a0,[value]);assert r['reason']=='returned'
    out=m.uc.reg_read(reg.UC_ARM64_REG_X0)
    assert out==(0x39 if value==0xbc else value)
    r.update(input_mpr_quality=value,output_avif_quality=out)
    return r


def enqueue_metadata(main_vpc):
    m=pp.StrictMicro(MPR,[(0xd670c,0xd678c),(0xcd40c,0xcd4f8)],resolve=True,logging_adapter=True,end=0xd678c)
    info=SCRATCH+0x1000
    for off,value in [(0x1c8,main_vpc),(0x1cc,6),(0x1d0,3),(0x1f0,6),(0x1f4,6),(0x1f8,3)]:
        m.uc.mem_write(info+off,pp.p32(value))
    w.putregs(m,x19=info,x20=FP+0x40,x29=FP)
    r=m.run(0xd670c);assert r['reason']=='conversion block complete'
    main=int.from_bytes(m.uc.mem_read(FP+0x7bc,4),'little')
    proxy=int.from_bytes(m.uc.mem_read(FP+0x7d8,4),'little')
    assert (main,proxy)==(15,18)
    r.update(main_vpc_fixture=main_vpc,proxy_vpc_fixture=6,main_FileFormat=main,proxy_FileFormat=proxy,
        main_field='exec+0x77c == FP+0x7bc',proxy_field='exec+0x798 == FP+0x7d8',
        scope='Original scalar marshalling and same-library identity helper; larger constructor/memcpy prefix and actual enqueue excluded.')
    return r


def message_header(file_format):
    m=pp.StrictMicro(MPR,[(0x27def8,0x27df38)],end=0x27df38)
    m.uc.mem_write(FP+0x60,struct.pack('<QQI',SCRATCH+0x7000,0,0))
    m.uc.mem_write(FP+0x70,pp.p32(0))
    w.putregs(m,x19=HEADER,x20=0,x21=0,x22=file_format,x23=0x20,x24=0x210,x25=0,x26=0x98,x29=FP)
    r=m.run(0x27def8);assert r['reason']=='conversion block complete'
    raw=bytes(m.uc.mem_read(HEADER,0x30));assert raw[0x1c]==file_format
    r.update(file_format_input=file_format,header_hex=raw.hex(),payload_format_offset='0x1c',
             scope='Original post-GetFixedArea metadata slice with synthetic virtual pointer and zero physical pointer; allocator and full CreateMessage excluded.')
    return r,raw


def sender_copy(header):
    m=pp.StrictMicro(MPR,[(0x27e14c,0x27e168)],end=0x27e168)
    m.uc.mem_write(HEADER,header);m.uc.mem_write(FP+0x38,struct.pack('<Q',RECEIVED))
    w.putregs(m,x19=HEADER,x29=FP)
    r=m.run(0x27e14c);assert r['reason']=='conversion block complete'
    assert bytes(m.uc.mem_read(RECEIVED,0x30))==header
    r.update(payload_unchanged=True,scope='Original three LDP/STP pairs after assumed OSAL allocation; no allocation, event expectation, send or wait executed.')
    return r


def receiver_header(header):
    m=pp.StrictMicro(AV,[(0x138ee8,0x138f00)],end=0x138f00)
    m.uc.mem_write(RECEIVED+8,header);w.putregs(m,x20=RECEIVED)
    r=m.run(0x138ee8);assert r['reason']=='conversion block complete'
    raw=bytes(m.uc.mem_read(RECEIVED,0x38))
    assert raw[8:]==header and raw[0x24]==header[0x1c]
    r.update(received_hex=raw.hex(),MPR_CMD_format_offset='0x24',
        scope='Independent post-DataflowInfraMsg::GetMsg(out+8,0x30) precondition; that external copy, transport and full ReceiveCommand are not executed.')
    return r,raw


def resource_case(label, packet, message, debug_level=0):
    rows={}
    for name,start,end,args in [
        ('NeedAcquire4KRsrc',0xb0fe8,0xb1008,[RECEIVED,PACKET]),
        ('NeedAcquire60pRsrc',0xb1090,0xb11b4,[PACKET,int(bool(packet[0x64]))]),
        ('GetExternalCodec',0xb1284,0xb1354,[PACKET,RECEIVED,int(bool(packet[0x64]))])]:
        m=pp.StrictMicro(AV,[(start,end)])
        m.uc.mem_write(PACKET,packet);m.uc.mem_write(RECEIVED,message)
        # This is an explicitly unresolved imported READ-ONLY debug input,
        # not a logger output or codec-state stub. Positive debug is a stop case.
        m.uc.mem_write(0x1b2720,struct.pack('<Q',SCRATCH+0xe000))
        m.uc.mem_write(SCRATCH+0xe000,pp.p32(debug_level))
        r=m.run(start,args)
        if debug_level>0 and name=='NeedAcquire60pRsrc':
            assert r['reason']=='unapproved PLT _ZN17OBJAVBBCBASECLASS9BizPrintfEtiijPKcz'
        else:assert r['reason']=='returned',(name,r['reason'])
        r.update(return_value=m.uc.reg_read(reg.UC_ARM64_REG_X0) if r['reason']=='returned' else None,
            debug_import_fixture={'name':'avbizPrintLevel','GLOB_DAT':'0x1b2720','value':debug_level},
            guest_codec_fields_unchanged=bytes(m.uc.mem_read(PACKET,len(packet)))==packet)
        assert r['guest_codec_fields_unchanged'];rows[name]=r
    return {'label':label,'helpers':rows,'scope':'Original resource/external-codec selectors on a synthesized packet/message. These are not supported-format validators or hardware Open acceptance.'}


def native_boundary_stops():
    # Each starts at an actual function entry; unknown dependencies must stop.
    cases=[]
    for label,native,start,end,args,expected in [
      ('Codec::EncOpen',MPR,0x2829a4,0x282da8,[PACKET,0x20,15,1,0,0],'unapproved execution 27dba8'),
      ('AvailableFormat backup',AV,0x13c68c,0x13ce1c,[SCRATCH,SCRATCH+0x1000],
       'unapproved PLT _ZN11AvbbcBackup9Read1ByteEjPh'),
      ('SendMsgToAvbbc',MPR,0x27e0cc,0x27e244,[HEADER,0],'unapproved PLT osal_valloc_msg_wait')]:
        m=pp.StrictMicro(native,[(start,end)]);r=m.run(start,args)
        assert r['reason']==expected,(label,r['reason'])
        r.update(label=label,native_dependency_executed=False);cases.append(r)
    return cases


def run(out):
    sources=[AV.path,MPR.path,l.a.cr.APP.path]+[Path(m.__file__) for m in (l,l.a,w,q,l.a.cr,l.a.cr.cp,l.a.cr.ss,pp,qp,l.a.cr.a)]
    sources += [Path(sys.modules[pp.Image.__module__].__file__),BASE/'stage4-windows-collab/mac-verification/offline_verify.py',STAGE/'extraction-receipt.json']
    hashes={str(p.relative_to(ROOT)):qp.sha(p) for p in sources}
    previous=BASE/'stage22-lifetime-registry/final-receipt.json'
    assert all(qp.sha(ROOT/f['path'])==f['sha256'] for f in json.loads(previous.read_text())['files'])
    packets=[];raws={}
    for label,values,proxy in [('target MAIN',[6,6,3],False),('matching proxy',[6,6,3],True),
                               ('HD59.94 proxy',[6,6,7],True),('factory UHD59.94 control',[5,13,7],False)]:
        r,raw=packet_case(label,values,proxy);packets.append(r);raws[label]=raw
    target=packets[0]['fields'];assert (target['video_codec_66'],target['width'],target['height'],
        target['codec_FramePerSec_enum_80'],target['progressive_flag_81'],target['mpr_quality_82'],
        target['chroma_94'],target['bitdepth_95'])==(15,1920,1080,3,1,22,0,1)
    identities=[codec_identity(v,s) for v in (6,5,1) for s in (0,1)]
    assert [v['codec_FileFormat_value'] for v in identities]==[15,18,15,18,5,17]
    qualities=[quality_conversion(v) for v in (22,49,57,188,189)]
    metadata=[enqueue_metadata(v) for v in (6,5)]
    transport=[];messages={}
    for stream,fmt in [('MAIN',15),('proxy',18)]:
        h,raw=message_header(fmt);sent=sender_copy(raw);recv,msg=receiver_header(raw)
        transport.append({'stream':stream,'header':h,'sender_copy':sent,'receiver_header':recv});messages[stream]=msg
    resources=[resource_case(label,raws[label],messages['proxy' if 'proxy' in label else 'MAIN']) for label in raws]
    assert all(resources[0]['helpers'][n]['return_value']==0 for n in resources[0]['helpers'])
    assert resources[2]['helpers']['NeedAcquire60pRsrc']['return_value']==1
    assert resources[3]['helpers']['NeedAcquire4KRsrc']['return_value']==1
    assert resources[3]['helpers']['GetExternalCodec']['return_value']==1
    invalid=bytearray(raws['target MAIN']);invalid[0x66]=0xff;invalid[0x80]=0xff
    invalid_resource=resource_case('invalid enum input: resources are not validation',bytes(invalid),messages['MAIN'])
    assert all(v['return_value']==0 for v in invalid_resource['helpers'].values())
    verbose_stop=resource_case('HD59.94 positive debug must stop',raws['HD59.94 proxy'],messages['proxy'],debug_level=1)
    stops=native_boundary_stops()
    for item in packets+identities+metadata:
        assert all(p['status']!='pending' for p in item['logging_return_nonconsumption_proofs'])
    assert hashes=={str(p.relative_to(ROOT)):qp.sha(p) for p in sources}
    regions=[('MAIN queue marshalling',MPR,0xd670c,0xd678c),('actual EncOpen caller',MPR,0xd1b80,0xd1bc4),
        ('packet MAIN builder',MPR,0xd13f8,0xd166c),('packet proxy builder',MPR,0xd166c,0xd18d8),
        ('Codec EncOpen',MPR,0x2829a4,0x282da8),('CreateMessage',MPR,0x27deac,0x27df44),
        ('SendMsgToAvbbc',MPR,0x27e0cc,0x27e244),('receiver envelope',AV,0x138e78,0x138fa0),
        ('Astra SetParameter',AV,0xb2958,0xb2d40),('MC EncOpenAstra forwarding',AV,0xb1694,0xb178c),
        ('4K resource',AV,0xb0fe8,0xb1008),('60p resource',AV,0xb1090,0xb11b4),
        ('external codec selector',AV,0xb1284,0xb1354),('AvailableFormat backup entry',AV,0x13c68c,0x13c778)]
    proof={'status':'PASS_ORIGINAL_ENCODER_BOUNDARY_AND_RESOURCE_FRAGMENTS_ONLY',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'library_hashes':{'libmpr.so':qp.sha(MPR.path),'libInfraAvbbc.so':qp.sha(AV.path)},
        'packet_cases':packets,'codec_identity_cases':identities,'quality_conversion_cases':qualities,
        'enqueue_metadata_cases':metadata,'transport_fragments':transport,'resource_cases':resources,
        'invalid_enum_resource_negative':invalid_resource,'positive_debug_dependency_stop':verbose_stop,
        'native_boundary_stops':stops,
        'matching_MAIN_proxy_packet_differing_offsets':[hex(i) for i,(x,y) in enumerate(zip(raws['target MAIN'],raws['matching proxy'])) if x!=y],
        'static_regions':[{'name':n,'image':im.path.name,'start':hex(s),'end_exclusive':hex(e),'instructions':im.dump(s,e)} for n,im,s,e in regions],
        'field_corrections':{'packet65':'GetCodecAudioFormat result; legacy file_format label must not be used for outer Codec::FileFormat',
                            'packet80':'codec FramePerSec enum','packet81':'progressive flag'},
        'findings':['MAIN VPC6 uses outer Codec::FileFormat15 while matching proxy uses18, even though the inner HEVC packet fields match. These are distinct namespaces.',
          'The target packet keeps quality22 through the original AVIF converter; only188 maps to57 in this helper.',
          'Target HD29.97 selects no4K/60p/external-codec resource in the tested helper conditions. Invalid codec/frame enums can select the same values, so this is not a capability validation pass.',
          'The downstream AvailableFormat routine reads actual backup fields and sends/receives messages; no live capability state was obtained.',
          'Full EncOpen includes normal locks, address conversion, shared buffers, message allocation/send/wait and receiver state/resource controllers. No successful native return is supplied by this experiment.'],
        'scope':'Pinned original helper/fragments and static source bindings; receiver transport gap and other native dependencies excluded. Synthetic zero buffer inputs, MPR diagnostic PC<-LR adapter, explicit AV debug input fixture. No hardware Open/Start, bitstream, live capability read, loader, restore or camera acceptance.',
        'actual_EncOpen_Start_or_hardware_acceptance_verified':False,'full_transport_or_resource_controller_executed':False,
        'camera_interface_auth_driver_files_module_WBI_or_write':False,'new_remote_attempts':False,
        'modified_firmware_or_flashable_patch_exported':False,'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'packet_builders':len(packets),'identity_cases':len(identities),
        'quality_cases':len(qualities),'queue_metadata_cases':len(metadata),'transport_fragment_sets':len(transport),
        'resource_helper_invocations':len(resources)*3+6,'native_boundary_stop_cases':len(stops),
        'MAIN_outer_FileFormat':15,'proxy_outer_FileFormat':18,
        'matching_MAIN_proxy_packet_differing_offsets':proof['matching_MAIN_proxy_packet_differing_offsets'],
        'target_resource_selectors_are_not_validation':True,'actual_hardware_acceptance_verified':False,
        'goal_complete':False,'persistent_write_release':False}
    qp.write_json(out/'encoder-boundary-results.json',proof);qp.write_json(out/'summary.json',summary)
    qp.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
        'script_sha256':qp.sha(Path(__file__)),'inputs':hashes,'results_sha256':qp.sha(out/'encoder-boundary-results.json'),
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
