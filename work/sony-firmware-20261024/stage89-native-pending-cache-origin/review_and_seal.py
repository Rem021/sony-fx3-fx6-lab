#!/usr/bin/env python3
"""Seal bounded pending-cache provenance without promoting device acceptance."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import cache_origin as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage88-native-frame-publication-and-gop-gate/final-receipt.json'
    assert im.sha(prior.read_bytes())==a.PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-initial-20261027';j=json.loads((run/'cache-origin-results.json').read_text())
    assert not (run/'failed-attempt.json').exists()
    assert j['status']=='PASS_NATIVE_PENDING_CACHE_INIT_AND_DECLARED_EXISTING_BUFFER_RELAY'
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'cache_origin.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'cache_origin.py').read_bytes()
    src=BASE/'stage86-hevc-vui-mode-conversion/run-20261026/vui-mode-results.json'
    assert im.sha(src.read_bytes())==j['source_receipt']['stage86_result_sha256']
    sources=json.loads(src.read_text())['cases']
    blob_path=a.old.old.prev.a.prev.p.a.v.VCD_PATH;blob=blob_path.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(blob_path.relative_to(BASE))]
    assert len(j['arena_cases'])==8 and len(j['relay_cases'])==12 and j['bounded_phases']==66
    events=[];successful=0
    for c in j['arena_cases']:
        seed=c['seed'];available=c['declared_available_bytes'];success=available>=8
        assert seed in (0xa5,0xc3) and available in (0,7,8,16) and c['cursor_before']==0x20
        manager=bytes.fromhex(c['manager_after_hex']);arena=bytes.fromhex(c['arena_after_hex'])
        assert len(manager)==len(arena)==4096
        assert struct.unpack_from('<III',manager)==(a.old.RECORD,0x20+available,0x28 if success else 0x20)
        assert a.word(manager,0xc90)==(a.old.RECORD+0x20 if success else 0)
        want=bytearray([seed])*4096
        if success:
            want[0x20]=0;want[0x24:0x28]=bytes(4)
            assert c['record_after_hex']==bytes(want[0x20:0x28]).hex()
            assert c['record_handle_is_null']
        else:assert c['record_after_hex'] is None
        assert arena==want
        assert len(c['events'])==1 and c['events'][0]['stop']==a.STOPS[0x13c31c if success else 0x13c408]
        assert not c['kernel_or_cache_payload_allocation_or_full_constructor_completed']
        events+=c['events']
    for c in j['relay_cases']:
        es=c['events'];events+=es;flag=c['declared_raw_metadata_flag'];kind=c['kind'];on=bool(flag)
        assert flag in (0,0x10) and c['source_native_saved_frame_preserved']
        assert not any(c[k] for k in ('host_sets_source_frame_cache_record_or_GOP_update_bit',
            'raw_metadata_real_producer_refcount_backend_merge_or_scheduling_executed',
            'module_ACK_MAIN_hardware_or_recovery_proven'))
        source=next(s for s in sources if s['seed']==c['seed'] and s['kind']==c['source_kind'] and s['source_label']==c['source_label'])
        assert c['source_GOP_hex']==source['GOP_after_hex']
        meta=a.old.declared_metadata(bytes.fromhex(source['GOP_after_hex']))
        assert c['metadata48_hex']==meta.hex()
        pages={int(k,16):bytes.fromhex(v) for k,v in c['final_pages'].items()}
        assert all(len(v)==4096 for v in pages.values()) and len(pages)==15
        sf=pages[a.SOURCEFRAME_PA];cache=pages[a.old.RECORD_PA];payload=pages[a.old.PAYLOAD_PA]
        assert sf[0x4c4]==flag and a.word(sf,0x4c8)==a.old.HANDLE+20
        assert pages[a.RAW_PA][0x50]==flag
        assert a.word(pages[a.RAW_PA],0x54)==a.old.HANDLE+(12 if kind=='different_source_handle' else 20)
        assert es[0]['stop']==a.STOPS[0x131888] and es[0]['sp']==hex(a.PRODUCER_SP-0x80)
        assert es[0]['ra']==es[1]['ra']==hex(a.IMAGE+0x1351c0) and es[1]['sp']==es[0]['sp']
        assert all(hex(a.IMAGE+x) in es[0]['CODE_observed_PCs'] for x in (0x1351b8,0x131818,0x131844))
        assert hex(a.IMAGE+0x131b38) in es[1]['CODE_observed_PCs']
        if kind=='different_source_handle':
            assert len(es)==2 and es[1]['stop']==a.STOPS[0x131b68]
            assert cache[0]==0 and a.word(cache,4)==a.old.HANDLE+12
            assert payload[0xec:0x11c]==bytes([0x37])*48
            assert c['decoded_output_target'] is None and c['GOP_before_pack_hex'] is None
        else:
            assert es[1]['stop']==a.STOPS[0x131ca8 if on else 0x131cb8]
            assert hex(a.IMAGE+0x140a00) in es[2]['CODE_observed_PCs']
            assert cache[0]==flag and struct.unpack_from('<H',pages[a.old.MANAGER_PA],0xca0)[0]==0x1235
            if on:assert hex(a.IMAGE+0x140c68) in es[2]['CODE_observed_PCs']
            if kind=='missing_cache_handle':
                assert len(es)==3 and es[2]['stop']==a.STOPS[0x140d04] and a.word(cache,4)==0
                assert payload[0xec:0x11c]==bytes([0x37])*48 and c['GOP_before_pack_hex'] is None
                assert c['decoded_output_target'] is None
            else:
                assert kind=='normal' and len(es)==6 and es[2]['stop']==a.STOPS[0x140e64]
                assert a.word(cache,4)==a.old.HANDLE+12
                assert payload[0xec:0x11c]==(meta if on else bytes([0x37])*48)
                assert struct.unpack_from('<H',pages[a.old.INFRAME_PA],0xe0)[0]==0x1235
                assert pages[a.old.INFRAME_PA][0x4c4]==flag and pages[a.old.OUTFRAME_PA][0x4c4]==flag
                assert a.word(pages[a.old.GOP_PA],0xe8)&1==0
                if on:
                    successful+=1
                    assert c['decoded_output_target']==(16000000 if c['source_kind']=='captured' else 20000000)
                    assert es[4]['stop']==a.old.STOPS[0xd9110] and es[5]['stop']==a.old.STOPS[0xd98b8]
                    assert pages[a.old.INPACK_PA][0xec:0x11c]==pages[a.old.OUTPACK_PA][0xec:0x11c]==meta
                    assert a.word(pages[a.old.OUTPACK_PA],0x84)&1==1
                    before_pack=bytes.fromhex(c['GOP_before_pack_hex'])
                    assert pages[a.old.OUTPACK_PA][0x14:0xb0]==before_pack[0x78:0x114]
                    assert [s['GOP_gate'] for s in c['snapshots']]==[False,False,False,True,False]
                    assert all(hex(a.IMAGE+x) in es[2]['CODE_observed_PCs'] for x in (0x140cf4,0x140e30,0x140e40,0x140e58))
                else:
                    assert c['decoded_output_target'] is None
                    assert pages[a.old.GOP_PA].hex()==c['source_GOP_hex']
                    assert not any(s['GOP_gate'] for s in c['snapshots'])
        if kind!='normal':assert pages[a.old.GOP_PA].hex()==c['source_GOP_hex']
    assert successful==4 and len(events)==66
    for e in events:
        assert e['original_image_immutable_inputs_and_exact_expected_full_stack_checked']
        assert not e['memory_read_write_hooks_installed'] and not e['native_interrupts']
        assert e['PC_observation_may_include_annulled_delay_slots'] and not e['MMIO_code_replacement_or_fake_return']
    refresh=STAGE/'public-source-refresh-20261027';r=json.loads((refresh/'receipt.json').read_text())
    for f in r['docs']:
        raw=(refresh/f['name']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    assert (refresh/'executed-source.py').read_bytes()==(STAGE/'refresh_public_sources.py').read_bytes()
    assert not r['binaries_payloads_camera_attachments_downloaded_or_third_party_code_run']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    md=a.cs.Cs(a.cs.CS_ARCH_MIPS,a.cs.CS_MODE_MIPS32|a.cs.CS_MODE_LITTLE_ENDIAN)
    bindings={0x13c2ec:'manager record-pointer alias',0x13c30c:'native empty record flags zero',
        0x13c310:'native empty record buffer handle zero',0x13c318:'native manager+c90 pointer store',
        0x131b38:'declared raw metadata flag source +50',0x131b48:'native source frame flag store',
        0x131b54:'declared raw metadata handle source +54',0x131b58:'identical owned-handle fast path',
        0x140c58:'native pending record pointer load',0x140c64:'native pending bit4 OR',
        0x140c68:'native pending flags store',0x140cf4:'existing cached-buffer handle load',
        0x140cf8:'source parameter buffer +ec',0x140e28:'cached parameter buffer +ec',
        0x140e40:'native metadata copy store',0x140d04:'unexecuted GP allocation boundary',
        0x131b68:'unexecuted GP reference-count boundary'}
    instructions=[]
    for off,meaning in bindings.items():
        ins=next(md.disasm(blob[off:off+4],a.IMAGE+off))
        instructions.append({'VA':hex(a.IMAGE+off),'word_hex':blob[off:off+4].hex(),
            'instruction':ins.mnemonic+' '+ins.op_str,'meaning':meaning,
            'boundary_not_executed':off in (0x140d04,0x131b68)})
    im.write_json(STAGE/'native-provenance-audit.json',{'created_utc':now,'VCD_sha256':im.sha(blob),
        'instructions':instructions,'refinement':'c90 pending cache is not an encoder success ACK; raw metadata and ownership remain unproven.'})
    review={'status':'PASS_NATIVE_PENDING_CACHE_PROVENANCE_WITH_DECLARED_RAW_INPUTS',
        'created_utc':now,'prior_sealed_files_verified':8,'arena_cases':8,'existing_buffer_relay_cases':12,
        'formal_bounded_phases':66,'native_output_copies':4,
        'empty_record_null_handle_separate_from_existing_owned_buffer':True,
        'pending_bit_set_before_unexecuted_allocation_not_completion':True,
        'c90_cache_not_encoder_success_ACK':True,
        'review_scope':'Same-agent original-instruction and saved-result review; whole-region checks performed by execution harness. No independent engine or real camera acceptance.',
        'real_metadata_production_ownership_scheduling_MAIN_hardware_recovery':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_pending_cache_origin_and_existing_buffer_relay'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage88封存8件及canonical复核；仅Mac，16项和授权保持。',
            '原arena片段8例初始化c90的8字节记录：flags0/handle0，3填充字节保留；不足8字节写空指针，未执行完整构造/内核分配。',
            '原元数据+50/+54→已有帧flag/句柄检查→原待处理缓存bit4/48字节转存→原发布/HEVCgate/输出复制，12例58阶段；连同初始化共20例66阶段。4开启例保留16M/20M目标字。',
            '细化来源：c90是帧参数待处理缓存，不是编码成功ACK。缺cache句柄先置bit4后停GP分配前；不同源句柄先写frameflag后停GP引用计数前，均不继续发布。',
            '空初始化与已有缓存缓冲为分开实验。真实元数据生产/缓冲所有权/后端合并转交/公共虚回调/调度/MAIN/硬件与全部恢复仍缺。公开REA/A7CII/A6700范围已刷新，不直接套用其它机型。'],
        'completion_not_claimed':True}
    result=rel+'/run-initial-20261027/cache-origin-results.json'
    g['latest_stage_evidence']['stage89_pending_cache_origin']={'readme':rel+'/README.md',
        'review':rel+'/completed-evidence-review.json','result':result,
        'provenance_audit':rel+'/native-provenance-audit.json',
        'public_refresh':rel+'/public-source-refresh-20261027/receipt.json',
        'scope':'Native empty-record initialization and separate declared existing-owned-buffer relay. c90 pending flag is not hardware ACK; raw metadata and actual ownership/dispatch remain unproved.',
        'authorization_unchanged':True,'goal_complete':False}
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,
        'prior_stage':'stage88-native-frame-publication-and-gop-gate',
        'finding':'manager+c90 is an 8-byte pending cache written from frame metadata. Prior local publication/gate/copy results stand; record/gate must not be interpreted as encoder-success ACK.',
        'actual_raw_metadata_producer_module_ACK_or_hardware_proven':False})
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11'):
            req['evidence'].append(result)
            req['stage89_scope']='原空记录8例与已有缓冲转存12例共66阶段；元数据+50帧flag原转存c90缓存及48字节，再接原发布/HEVC门控。c90不是编码成功ACK；不同句柄/缺缓冲停GP工作前。真实元数据/所有权/调度/MAIN/硬件与同机恢复未证。'
    g['next_safe_offline_actions'].append('stage89后优先追原源元数据+50/+54的真实生产/传入及首次cache缓冲获取，核对后端合并/转交、引用计数/锁、公共虚回调/调度和MAIN。原空记录handle0与已有句柄转存必须分开，不以待处理bit4/GOPgate证明编码ACK、复制完成或硬件成功；保留全部主录/恢复验收。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 待处理缓存的原初始化与转存来源](<'+str(STAGE.relative_to(ROOT))+'/README.md>)：原空8字节记录/已有缓冲分别验证，共20例66阶段；c90是帧参数缓存，不是编码成功ACK。真实元数据/所有权/调度/MAIN与硬件恢复未证，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{'schema':'fx3-stage89-native-pending-cache-origin/1',
        'created_utc':now,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':a.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
        'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
                     'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
