#!/usr/bin/env python3
"""Original QoS request/cache/encoding and synthetic HAL-feedback fragments.

No actual bitrate producer, HAL/backend output, firmware command, channel,
transport, camera or recovery is executed. Open-comp bitrate fields are NOT the
same layout as set-QoS requests. Explicit fixtures never stand for real replies.
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
sys.path.insert(0,str(BASE/'stage33-imola-format-matcher'))
import imola_matcher as q
r,V=q.r,q.V
CTRL=r.ARENA+0x10000
PARAM_OWNER=CTRL+0x20
QOS=PARAM_OWNER+0x2aa20
REQUEST=r.ARENA+0x330000
EVENT=r.ARENA+0x340000
META=r.ARENA+0x350000
OUTPUT=r.ARENA+0x360000
CHANGE=r.ARENA+0x361000
COMMON=r.ARENA+0x100000
HAL=r.ARENA+0x370000
FEEDBACK=r.ARENA+0x371000
REPLY=r.ARENA+0x372000
SENTINEL=0xa5a5a5a5


def put32(m,at,value):m.uc.mem_write(at,struct.pack('<I',value))


def request(value,update=True):
    b=bytearray(0x48);b[4]=int(update);struct.pack_into('<I',b,8,value)
    return bytes(b)


def context(m):
    # Sender descriptor-owner needs context->configuration; resource receiver
    # and action need channel0 and notification-id fields, all fixture values.
    m.uc.mem_write(CTRL,r.p64(META));put32(m,META,0)
    put32(m,PARAM_OWNER+0x720+0x14,0x805700f9)


def sender(blob,req):
    m=r.RawGuest(blob,[(0x135f28,0x135f64),(0x135fd4,0x13600c),(0xd80,0xeec)],
       {0x960a4:'before_message_object_constructor'})
    context(m)
    m.uc.mem_write(PARAM_OWNER,r.p64(q.s.t.f.CTX))
    m.uc.mem_write(q.s.t.f.CTX,r.p64(r.CONFIG));m.uc.mem_write(r.CONFIG+8,b'\0')
    m.uc.mem_write(REQUEST,req);m.regs(x0=PARAM_OWNER,x1=REQUEST)
    result=m.run(0x135f28)
    assert result['reason']=='boundary: before_message_object_constructor'
    sp=m.uc.reg_read(r.reg.UC_ARM64_REG_SP);value=m.read(sp+0x1a8,0x54)
    assert value[:8]==struct.pack('<HHHH',0x2103,0x10a,0x54,0)
    assert value[8:12]==bytes(4) and value[12:]==req
    result.update(envelope_hex=value.hex(),
      scope='Original QoS sender copies request48 and channel into wire54 stack envelope; stops before constructor/serializer/send, no actual source or channel binding.')
    return result


def cache_ack(blob,req,old_target,trace_cap):
    m=r.RawGuest(blob,[(0x24d78c,0x24d7d0),(0x2486fc,0x24870c),
         (0x248b8c,0x248d4c),(0x246144,0x24614c)],
         {0x27dab4:'before_reply_send_wrapper'})
    context(m)
    put32(m,QOS+0xe0,old_target);put32(m,QOS+0x18,old_target)
    put32(m,QOS+0xe8,trace_cap)
    # Source event is channel4 + request48, the same payload bytes as sender.
    event=bytes(4)+req;m.uc.mem_write(EVENT,event)
    m.regs(x19=CTRL,x20=EVENT,x21=PARAM_OWNER)
    result=m.run(0x24d78c)
    assert result['reason']=='boundary: before_reply_send_wrapper'
    value=struct.unpack_from('<I',req,8)[0]
    expected=value if req[4] else old_target
    assert int.from_bytes(m.read(QOS+0xe0,4),'little')==expected
    assert m.read(QOS+0x14,1)==bytes([int(bool(req[4]))])
    ptr=m.uc.reg_read(r.reg.UC_ARM64_REG_X1);ack=m.read(ptr,0x14)
    assert ack==struct.pack('<HHHHIII',0x2103,0x117,0x14,0,0,0,0)
    assert not any(V+0x248d64<=p<V+0x249548 for p in m.pcs)
    result.update(cached_target=expected,cached_target_update_flag=int(bool(req[4])),
      ack_before_send_hex=ack.hex(),quantizer_or_Hal_not_executed_before_ack=True,
      precondition='Independent post-diagnostic static-QoS action prefix0x24d78c. Owner/frame/register graph and previous target/trace upper bound are explicit fixtures; actual state eligibility/log effects/transport not executed.',
      scope='Original cache setter and ack construction only; reply sender unexecuted. This prefix does not encode/apply hardware rate.')
    return m,result


def encode(m,blob,case):
    # Same guest fixture contents, NEW independent parameter-conversion call.
    # The action has not run beyond reply send; no scheduling/application order
    # is inferred by calling this separate routine afterward.
    m.ranges=[(V+0x248d64,V+0x249548)]
    m.boundaries={V+0x27d528:'before_quantizer_diagnostic',V+0x27da9c:'before_runtime_pending_clear'}
    q.s.t.f.reset_trace(m)
    m.uc.mem_write(OUTPUT,bytes(0x80));put32(m,OUTPUT+0x18,SENTINEL)
    m.regs(x0=QOS,x1=0,x2=30,x3=0,x4=CHANGE,x5=OUTPUT)
    result=m.run(0x248d64)
    flag=int.from_bytes(m.read(OUTPUT,4),'little')
    word=int.from_bytes(m.read(OUTPUT+0x18,4),'little')
    emitted=bool(flag&0x80)
    decoded=(((word>>8)+1)<<(6+(word&0xff))) if emitted else None
    result.update(target_word_hex=hex(word),target_update_bit_set=emitted,
      decoded_target_scalar=decoded,
      cached_target_after=int.from_bytes(m.read(QOS+0xe0,4),'little'),
      precondition='Independent original quantizer call on cached fixture; frame scalar30 and other scalar0 are explicit arguments. Original logs, pending-clear runtime and actual caller/frame/HAL application are unexecuted.',
      scope='Native target clamp/field encode prefix only. Encoded numeric value is not measured bitrate or proof of upstream bps units.')
    if case['expect']=='encode':
        assert result['reason']=='boundary: before_quantizer_diagnostic'
        assert m.pcs[-2]==V+0x248eec and emitted
        expected=(min(case['value'],case['trace_cap'])//64)*64
        assert decoded==expected
        result['diagnostic_callsite']='0x248eec'
    elif case['expect']=='no_update':
        assert result['reason']=='boundary: before_runtime_pending_clear'
        assert not emitted and word==SENTINEL
        result['diagnostic_callsite']=None
    else:
        assert result['reason']=='boundary: before_quantizer_diagnostic'
        expected=0x248f50 if case['expect']=='bad_target' else 0x248e8c
        assert m.pcs[-2]==V+expected and not emitted and word==SENTINEL
        result['diagnostic_callsite']=hex(expected)
    return result


def qos_case(blob,case):
    req=request(case['value'],case['update'])
    wire=sender(blob,req)
    m,ack=cache_ack(blob,req,case['old_target'],case['trace_cap'])
    encoding=encode(m,blob,case)
    return {'input':case,'request48_hex':req.hex(),'sender_prefix':wire,
      'independent_cache_and_ack_prefix':ack,'independent_quantizer_prefix':encoding,
      'same_state_eligible_end_to_end_or_Hal_application_verified':False}


def route(blob,envelope):
    m=r.RawGuest(blob,[(0x245dac,0x246040),(0x249ad0,0x249e20)],
       {0x27d528:'before_resource_receiver_diagnostic'})
    context(m);m.uc.mem_write(CTRL+0x18,r.p64(META));m.uc.mem_write(EVENT,envelope)
    m.regs(x0=CTRL,x1=EVENT,x2=0x805700f9)
    result=m.run(0x245dac)
    assert result['reason']=='boundary: before_resource_receiver_diagnostic'
    assert m.pcs[-2]==V+0x249e1c and m.read(EVENT,0x54)==envelope
    result.update(scope='Original already-received source/CID/channel/MID route selects QoS action10a through first diagnostic; actual251f90 state dispatcher and full action not executed.')
    return result


def feedback(blob,stream,target,trace):
    m=r.RawGuest(blob,[(0x225b7c,0x225e40),(0x22c3cc,0x22c430),
       (0x246154,0x246200),(0x22c324,0x22c334)],
       {0x27d528:'before_unexpected_feedback_diagnostic'})
    put32(m,COMMON+0xe128,stream);m.uc.mem_write(COMMON+0xe000,r.p64(HAL))
    # Explicit synthetic cached HAL parameters; NOT returned by a backend.
    m.uc.mem_write(HAL+0xac,b'\0');put32(m,HAL+0xb0,target//64-1)
    put32(m,HAL+0xb4,0);put32(m,HAL+0xb8,trace//64-1)
    m.uc.mem_write(HAL+0xbc,b'\0');put32(m,HAL+0xc0,65535)
    m.uc.mem_write(HAL+0x97,b'\1');m.uc.mem_write(HAL+0x98,struct.pack('<HH',30,30))
    put32(m,HAL+0x58,0x12345678)
    before=m.read(HAL,0xd8);m.regs(x0=COMMON,x8=FEEDBACK)
    decoded=m.run(0x225b7c);assert decoded['reason']=='returned'
    data=m.read(FEEDBACK,0x34)
    values=struct.unpack_from('<3Q',data)
    assert values==(trace,target,1048576) and m.read(HAL,0xd8)==before
    decoded.update(trace_scalar=values[0],target_scalar=values[1],cpb_scalar=values[2],
      precondition='Native helper receives synthetic cached HEVC HAL parameter pointer through common+e000; backend query/mutex/channel and real cached output are not executed or observed.',
      scope='Original cached-parameter decode only; no real returned bitrate or accepted default for FF preset.')
    q.s.t.f.reset_trace(m);put32(m,PARAM_OWNER+0x738,stream)
    m.regs(x0=PARAM_OWNER,x1=REPLY,x2=FEEDBACK)
    copied=m.run(0x246154);assert copied['reason']=='returned'
    reply=m.read(REPLY,0x48)
    assert struct.unpack_from('<3Q',reply,0x20)==(trace,target,1048576)
    copied.update(open_comp_payload_hex=reply.hex(),
      trace_offset='0x20',target_offset='0x28',cpb_offset='0x30',
      precondition='Independent Open-completion payload marshaler with synthetic decoded cache as input.',
      scope='Original numeric copy into reply fields; not actual feedback, transport, ack or hardware verification.')
    return {'stream_type_fixture':stream,'synthetic_Hal_parameter_hex':before.hex(),
      'cached_parameter_decode':decoded,'independent_reply_marshalling':copied,
      'Open_comp_layout_not_set_QoS_request_layout':True,'real_backend_output_observed':False}


def static_evidence(blob):
    ranges=[('input_if QoS forwarding after state command',0x14555c,0x145588),
      ('parent QoS forwarding',0x1345e4,0x1345ec),
      ('QoS sender request and envelope',0x135f28,0x13606c),
      ('resource source router',0x245dac,0x245f18),
      ('resource MID switch',0x249ad0,0x249b1c),
      ('QoS MID10a action',0x249e1c,0x249e68),
      ('QoS action incl excluded logs and ack',0x24d738,0x24d82c),
      ('second QoS action cache/ack and third ack-only prefix',0x24d8c0,0x24da54),
      ('resource to cache setter',0x2486fc,0x24870c),
      ('cache field update flags',0x248b8c,0x248d4c),
      ('target quantizer with log boundaries',0x248d64,0x248fc0),
      ('pending clear and return',0x249508,0x249548),
      ('frame parameter conversion caller1',0x2463e0,0x246400),
      ('frame parameter conversion caller2',0x24671c,0x246754),
      ('HAL stream selector',0x22c3cc,0x22c430),
      ('cached HAL parameters and numeric feedback',0x225b7c,0x225e40),
      ('Open completion numeric marshaller',0x246154,0x246200),
      ('Open completion dump bitrate offsets',0x1390a8,0x13915c),
      ('strategy selection caller',0x189c74,0x189ce8)]
    labels=[0x443b1c,0x443af4,0x443b58,0x4180ae,0x41818e,0x4181b9,0x4181e4,0x4452b1]
    return {'regions':[{'name':n,'instructions':r.im.dump(blob,a,z,V)} for n,a,z in ranges],
      'diagnostic_labels':[{'offset':hex(p),'text':r.im.cstring(blob,p,180)} for p in labels],
      'MID10a_action_table':{'offset':hex(0x37ea48+10*8),'target':hex(struct.unpack_from('<Q',blob,0x37ea48+10*8)[0])},
      'semantic_refinement':'The64-bit target field at Open-comp+28 is a result/cache description, not the32-bit set-QoS request+8. Neither synthetic source proves current FF preset actual bitrate.',
      'next_bitrate_producer':'Original strategy selection189c74->18cb0c/18cb84/18cc64/18cdd8 selects pointer at owner+278; actual request creation, bps units, preset defaults and profile consistency remain unresolved.'}


def run(out):
    prior=q.STAGE/'final-receipt.json';assert r.im.sha(prior.read_bytes())=='f1f5393b412f4f3fe26f0b399df5f010c9947b9641002d9fddf9637dbc30623b'
    manifest=json.loads(prior.read_text());assert all(r.im.sha((ROOT[v['path']]).read_bytes())==v['sha256'] for v in manifest['files'])
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    common={'update':True,'old_target':10000000,'trace_cap':20000000,'expect':'encode'}
    specs=[dict(common,label='target scalar16000000',value=16000000),
      dict(common,label='target scalar16000001',value=16000001),
      dict(common,label='target scalar16000063',value=16000063),
      dict(common,label='trace bound10000000',value=16000000,trace_cap=10000000),
      dict(common,label='target update flag disabled',value=16000000,update=False,expect='no_update'),
      dict(common,label='zero target',value=0,expect='bad_target'),
      dict(common,label='zero trace bound',value=16000000,trace_cap=0,expect='bad_trace')]
    cases=[qos_case(blob,c) for c in specs]
    routed=route(blob,bytes.fromhex(cases[0]['sender_prefix']['envelope_hex']))
    feedbacks=[feedback(blob,14,16000000,18000000),feedback(blob,21,9000000,12000000)]
    proof={'status':'PASS_ORIGINAL_QOS_NUMERIC_PATH_AND_SYNTHETIC_FEEDBACK_SCOPE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'QoS_cases':cases,'resource_QoS_route':routed,'synthetic_feedback_cases':feedbacks,
      'static_evidence':static_evidence(blob),
      'findings':['QoS has a distinct CID2103/MID10a wire54 request; bit/update flags and target32 differ from Open-comp64 fields.',
        'One post-log action caches request then constructs117 ack before quantizer/HAL; another ack-only action exists. State eligibility and actual dispatch unproven, so ack alone cannot establish application.',
        'On explicit cache and upper-bound fixtures native encoder prefix represents16000000 exactly, rounds16000001..63 down to16000000, clamps to trace bound and ignores target input with update flag0.',
        'Synthetic HEVC HAL cached data can be decoded into64-bit trace/target and copied into Open-comp reply. No actual backend output or FF-preset bitrate was observed.',
        'Actual strategy selection/request producer, rate units and FF preset defaults, native frame application and full readback/bitstream still unresolved.'],
      'scope':'Independent guest-only request/cache/quantizer fragments and explicit synthetic HAL cache decode/reply copy. No real producer/units/HAL channel/transport/bitrate/hardware/restore.',
      'native_output_or_diagnostic_adapters':False,'camera_or_remote_access_attempted':False,
      'actual_FF16Mbps_hardware_or_restore_verified':False,'modified_firmware_or_patch_exported':False,
      'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'QoS_scenarios':7,'sender_message':{'CID':'0x2103','MID':'0x010a','length':'0x54'},
      'constructed_ack_before_send':{'MID':'0x0117','length':'0x14','not_hardware_applied_proof':True},
      'target_encoded_scalars':[v['independent_quantizer_prefix']['decoded_target_scalar'] for v in cases],
      'real_FF_default_bitrate_or_rate_units_verified':False,'synthetic_feedback_scenarios':2,
      'hardware_or_restore_verified':False,'goal_complete':False,'persistent_write_release':False}
    assert r.im.sha(blob)==r.im.sha(image.read_bytes())
    r.im.write_json(out/'qos-path-results.json',proof);r.im.write_json(out/'summary.json',summary)
    r.im.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
      'script_sha256':r.im.sha(Path(__file__).read_bytes()),'stage33_helper_sha256':r.im.sha(Path(q.__file__).read_bytes()),
      'raw_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),'raw_image_sha256':r.im.sha(blob),
      'previous_manifest_sha256':r.im.sha(prior.read_bytes()),'volume_uuid':r.im.VOLUME,
      'proof_sha256':r.im.sha((out/'qos-path-results.json').read_bytes()),
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
