#!/usr/bin/env python3
"""Unchanged original FH rejection from matcher to pending message callback.

Do not infer successful cleanup, receipt delivery, retry or recovery from this
bounded unsupported-mode request. No private writer or new code is executed.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage69-native-16M-callpath'))
import channel_callpath as c
r,im,V,n,f=c.r,c.im,c.V,c.n,c.f
BASE,ROOT=c.BASE,c.ROOT
EXTRA=[(0x21efc4,0x21f048),(0x21ead0,0x21eafc),(0x229ae4,0x229c84),(0x22f408,0x22f45c)]


def snapshot(m):
    q=f.last;word=lambda a:struct.unpack('<I',m.read(a,4))[0]
    ptr=lambda a:struct.unpack('<Q',m.read(a,8))[0]
    tree=q.FACTORY+0x55f10;root=ptr(tree)
    return {'dispatcher_pending':word(q.CTX+0x108),'free_ID_count':word(q.FACTORY+8),
            'free_MAIN_count':word(q.FACTORY+0x55ec8),'free_other_count':word(q.FACTORY+0xa33d8),
            'free_MAIN_map_nodes':word(tree+0x120),'MAIN_tree_root':hex(root),
            'MAIN_tree_root_key_u32':word(root+0x18) if root else None,
            'MAIN_tree_root_handler':hex(ptr(root+0x20)) if root else None,
            'first_MAIN_handler':hex(q.HANDLER),'first_COMMON_channel_byte':m.read(c.COMMON+8,1)[0],
            'first_COMMON_request_word':word(c.COMMON+0x10ac),
            'first_COMMON_manager':hex(ptr(c.COMMON+0x10a0)),
            'first_COMMON_selected_preset':hex(ptr(c.COMMON+0xe000)),
            'first_COMMON_preset_ID':word(c.COMMON+0xe470),
            'message_first_pointer':hex(ptr(q.MESSAGE)),
            'private_control':c.old.control(m)}


def assert_images(m):
    # Both Sony callsites have their original instructions. The compiled
    # adapters remain mapped as inert fixture storage and are never entered.
    raw=bytearray(m.read(V,len(m.blob)))
    assert raw[0x1ec:0x884]==m.read(n.MDATA,0x698)
    raw[0x1ec:0x884]=m.blob[0x1ec:0x884]
    for a,value in m.expected_data.items():assert raw[a-V]==value;raw[a-V]=m.blob[a-V]
    assert raw==m.blob
    assert not m.writer_entries and not m.adapter_entries and not m.bridge_entries
    assert not m.rate_entries and not m.admitted_channel_entries and not m.module_writes
    for module in m.modules.values():
        for section in module.sections.values():assert m.read(section['base'],section['size'])==bytes(section['data'])
    for a,data in [(f.f58.BRIDGE,m.code_bytes),(f.f58.CONST,m.ro_bytes),(c.old.CODE,m.writer_code),
                   (c.old.RODATA,m.writer_ro),(c.BRIDGE,m.adapter_code),(c.CONST,m.adapter_ro)]:
        assert m.read(a,len(data))==data


def one_case(assets,modules,providers,adapter,label,descriptor,seed):
    m,events=c.linked(assets,modules,providers,adapter)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    # Restore original call instructions BEFORE constructing/requesting. This
    # experiment does not use the alias or admission adapter at all.
    for a in (f.f58.SITE,c.SITE):m.uc.mem_write(a,m.blob[a-V:a-V+4])
    m.ranges.extend((V+a,V+z) for a,z in EXTRA)
    m.boundaries.pop(V+0x21efc4)
    m.boundaries[V+0x21ead0]='before_original_common_sentinel_return'
    m.boundaries[V+0x229ae4]='after_original_common_sentinel_return_before_factory_branch'
    m.boundaries[V+0x22f45c]='after_original_factory_return_before_request_callback'
    c.prepare(m,events,descriptor,seed,None)
    initial=snapshot(m);assert [initial[k] for k in ('free_ID_count','free_MAIN_count','free_MAIN_map_nodes')]==[8,6,6]
    private_before=m.read(c.old.CONTROL,296)
    e=c.phase(m,'unmodified original queued FH Open takes no-row branch '+label,V+0x22f34c,x0=f.last.CTX)
    events.append(e);assert e['reason']=='boundary: before_original_common_sentinel_return',e['reason']
    assert len(m.real_returns)==1 and m.real_returns[0]['W0']==0xffffffff
    assert len(m.real_match_entries)==1
    source=int(m.real_match_entries[0]['input_pointer'],16);source98=m.read(source,152)
    assert source98[:136]==descriptor and m.read(c.COMMON+0xe110,136)==descriptor
    inner_snapshot=snapshot(m)
    m.boundaries.pop(V+0x21ead0)
    e=c.phase(m,'same original common failure sentinel and epilogue '+label,V+0x21ead0,independent=False)
    events.append(e);assert e['reason']=='boundary: after_original_common_sentinel_return_before_factory_branch'
    common_return=m.uc.reg_read(r.reg.UC_ARM64_REG_X0)&0xffffffff
    assert common_return==m.blob[0x44fcea]==0xff
    common_snapshot=snapshot(m)
    m.boundaries.pop(V+0x229ae4)
    e=c.phase(m,'same original factory no-channel branch to message callback boundary '+label,V+0x229ae4,independent=False)
    events.append(e);assert e['reason']=='boundary: after_original_factory_return_before_request_callback',e['reason']
    outer_return=m.uc.reg_read(r.reg.UC_ARM64_REG_X0)&0xffffffff
    assert outer_return==struct.unpack_from('<I',descriptor)[0]==0
    final=snapshot(m)
    for state in (inner_snapshot,common_snapshot,final):
        assert [state[k] for k in ('free_ID_count','free_MAIN_count','free_MAIN_map_nodes')]==[7,5,5]
        assert state['MAIN_tree_root_handler']==hex(f.last.HANDLER)
    assert final['first_COMMON_channel_byte']==0xff and final['first_COMMON_selected_preset']=='0x0'
    assert final['dispatcher_pending']==0
    assert final['message_first_pointer']=='0x0'
    assert m.read(c.old.CONTROL,296)==private_before
    assert not m.kernel_service_entries and not m.message_entries and not m.channel_entries
    assert m.read(c.COMMON+0xe110,136)==descriptor and m.read(source,152)==source98
    assert_images(m)
    return {'label':label,'seed':seed,'initial':initial,'at_no_row_return':inner_snapshot,
            'after_common_return':common_snapshot,'before_pending_message_callback':final,
            'matcher_return_signed':-1,'common_return_sentinel':common_return,'factory_return_u32':outer_return,
            'source98_hex':source98.hex(),'FH_common_descriptor_preserved':True,
            'events':events,'original_diagnostics':m.all_logs,
            'original_code_callsites_unchanged':True,'private_writer_adapter_or_kernel_services_executed':False,
            'callback_or_full_cleanup_or_retry_or_recovery_executed':False}


def run(out):
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    prior=BASE/'stage69-native-16M-callpath/final-receipt.json'
    assert im.sha(prior.read_bytes())=='417033856d0b31e1019bd64b932199d826ebdefcc9321a96dae1334fae8c1d8e'
    for row in json.loads(prior.read_text())['files']:assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    modules,providers,kernel=c.d.link.build()
    matchobj=f.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o'
    code,ro,_=f.f58.object_image(matchobj.read_bytes())
    writerobj=c.old.STAGE/'run-bounded-stores-20261026/resource_alias.a64.o'
    wcode,wro,functions,_=c.old.object_image(writerobj.read_bytes())
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes();assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    liro=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    obj=BASE/'stage69-native-16M-callpath/run-same-instance-slices-20261026/channel_adapter.a64.o'
    adapter=c.object_image(obj.read_bytes())
    assets=blob,liro,kernel,code,ro,wcode,wro,functions;descriptor=c.d.p.inputs()[0][1]
    cases=[one_case(assets,modules,providers,adapter,'original FH priorA5',descriptor,0xa5),
           one_case(assets,modules,providers,adapter,'original FH priorC3',descriptor,0xc3)]
    proof={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'status':'PASS_ORIGINAL_UNSUPPORTED_FH_PATH_TO_PENDING_CALLBACK_NOT_FULL_CLEANUP',
           'cases':cases,'bounded_fragments':sum(len(x['events']) for x in cases),
           'original_extra_ranges':[{'start':hex(a),'end':hex(z),'instructions':im.dump(blob,a,z,V)} for a,z in EXTRA],
           'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
                             'runner_sha256':im.sha((c.STAGE/'channel_callpath.py').read_bytes()),
                             'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(liro),'kernel_sha256':im.sha(kernel),
                             'prior_manifest_sha256':im.sha(prior.read_bytes())},
           'conclusions':['Unmodified original target FH descriptor returns matcher -1 and common channel sentinel FF in this partial guest.',
                          'Before the message callback, ID/MAIN/map-node pools remain borrowed and the handler remains registered. This is not by itself a leak or a failure of the real camera.',
                          'The external request header fixture lacks its first virtual-table pointer; callback/acknowledgement is not executed, so cleanup/retry completion is not established.',
                          'Do not implement a camera adapter rejection or restore guarantee from a bare boolean, sentinel or a decremented dispatcher queue.',
                          'No bitrate publication, kernel service, USB protocol, hardware start/recording or recovery was executed.'],
           'actual_Sony_failure_cleanup_complete':False,'UU_Windows_camera_operations':False,
           'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'open-rejection-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':proof['status'],'cases':2,'bounded_fragments':proof['bounded_fragments'],
                      'pools_before_callback':[7,5,5],'full_cleanup_proven':False}))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    im.volume();out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        if 'CURRENT_GUEST' in globals():
            m=CURRENT_GUEST;im.write_json(out/'failure-state.json',{'pc':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
                'reason':m.reason,'last_pcs':[hex(x) for x in m.pcs[-12:]],'snapshot':snapshot(m)})
        raise


if __name__=='__main__':main()
