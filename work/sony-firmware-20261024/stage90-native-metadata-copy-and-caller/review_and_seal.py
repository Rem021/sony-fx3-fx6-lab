#!/usr/bin/env python3
"""Review metadata layouts and ownership stop points; retain device gates."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import metadata_source as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage89-native-pending-cache-origin/final-receipt.json'
    assert im.sha(prior.read_bytes())==a.PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-initial-20261027';j=json.loads((run/'metadata-source-results.json').read_text())
    assert not (run/'failed-attempt.json').exists()
    assert j['status']=='PASS_DISTINCT_LAYOUT_RAW_COPY_REFERENCE_BOUNDARY_AND_ORIGINAL_CALLER'
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'metadata_source.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'metadata_source.py').read_bytes()
    blob_path=a.prev.old.old.prev.a.prev.p.a.v.VCD_PATH;blob=blob_path.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(blob_path.relative_to(BASE))]
    assert a.app_gp(blob)==a.GP
    assert [len(j[k]) for k in ('contrast_cases','raw_copy_cases','caller_cases')]==[4,8,4]
    assert j['bounded_entries']==16
    events=[]
    for c in j['contrast_cases']:
        source=bytes.fromhex(c['source_page_hex']);dst=bytes.fromhex(c['destination_page_hex'])
        assert source[0x50]==dst[0x50]==c['declared_source_flag']
        assert a.word(source,0x54)==a.HANDLES+4
        assert a.word(dst,0x54)==(c['seed']<<24)|((a.HANDLES+4)&0xffffff)
        assert a.word(dst,0x54)!=a.word(source,0x54)
        for off in (0x4f,0x53,0x57):assert dst[off]==c['seed']
        assert c['destination_high_byte_preserved'] and not c['copy_is_raw_parameter_handle_ownership_transfer']
        assert len(c['events'])==1 and c['events'][0]['stop']=='returned_via_original_jr_ra'
        events+=c['events']
    null_returns=0;reference_stops=0
    for c in j['raw_copy_cases']:
        source=bytes.fromhex(c['source_page_hex']);dst=bytes.fromhex(c['destination_page_hex'])
        handle=a.HANDLES+4 if c['nonnull_parameter_handle'] else 0
        assert a.word(source,0x54)==a.word(dst,0x54)==c['destination_word54']==handle
        assert dst[0x50]==source[0x50]==c['declared_source_flag']
        assert not c['nonnull_reference_increment_completed'] and not c['copied_nonnull_handle_consumed_after_stop']
        for lo,hi in ((0xd,0x10),(0x3e,0x40),(0x51,0x54)):
            assert dst[lo:hi]==bytes([c['seed']])*(hi-lo)
        e=c['events'][0];events+=c['events']
        assert len(c['events'])==1
        assert all(hex(a.IMAGE+x) in e['CODE_observed_PCs'] for x in (0x1f3a8c,0x1f3a90,0x1f3a94,0x1f3a9c))
        if handle:
            reference_stops+=1
            assert not c['native_constructor_returned']
            assert e['stop']==a.STOPS[0x1f3b40] and e['SP']==hex(a.SP-0x30)
            assert dst[0x58:]==bytes([c['seed']])*(4096-0x58)
            assert hex(a.IMAGE+0x1f3b48) not in e['CODE_observed_PCs']
        else:
            null_returns+=1
            assert c['native_constructor_returned'] and e['stop']=='returned_via_original_jr_ra'
            assert e['SP']==hex(a.SP) and e['RA']==hex(a.TRAP)
            assert a.word(dst,0x58)==a.GP-0x5d58 and a.word(dst,0x84)==0
            assert dst[0x5c:0x84]==source[0x5c:0x84] and dst[0x88:0x8c]==source[0x88:0x8c]
            assert hex(a.IMAGE+0x1cb594) in e['CODE_observed_PCs']
    assert null_returns==reference_stops==4
    for c in j['caller_cases']:
        pages={int(k,16):bytes.fromhex(v) for k,v in c['final_pages'].items()}
        assert len(pages)==7 and all(len(v)==4096 for v in pages.values())
        assert c['owned_inputs_separate_from_copy_experiment']
        assert not c['geometry_builder_or_full_frame_header_body_or_actual_MAIN_executed']
        e=c['events'][0];events+=c['events'];flag=c['declared_raw_flag']
        assert flag in (0,0x10) and pages[a.SRC_PA][0x50]==flag
        assert a.word(pages[a.SRC_PA],0x54)==a.HANDLES+4
        assert a.word(pages[a.INSTANCE_PA],4)==a.OWNER
        assert struct.unpack_from('<HH',pages[a.PACK_PA],0xec)==(119,67)
        values=struct.unpack_from('<HH',pages[a.OWNER_PA],0x24)
        assert list(values)==c['owner_u16_24_26_after']
        if flag:
            assert values==(120,68) and e['stop']==a.STOPS[0x131e60]
            assert e['SP']==hex(a.SP-0x40) and e['RA']==hex(a.IMAGE+0x134fa0)
            assert all(hex(a.IMAGE+x) in e['CODE_observed_PCs'] for x in (0x144178,0x1441bc,0x134f98,0x131e50,0x131e5c))
            assert hex(a.IMAGE+0x13380c) not in e['CODE_observed_PCs']
        else:
            assert values==(0xaaaa,0xbbbb) and e['stop']==a.STOPS[0x131888]
            assert e['SP']==hex(a.SP-0x80) and e['RA']==hex(a.IMAGE+0x1351c0)
            assert all(hex(a.IMAGE+x) in e['CODE_observed_PCs'] for x in (0x1441d0,0x1351b8,0x131844))
        assert pages[a.DST_PA]==bytes([c['seed']])*4096
    assert len(events)==16
    for e in events:
        assert e['exact_entire_stack_image_and_immutable_inputs_checked']
        assert not e['memory_read_write_hooks_installed'] and not e['native_interrupts']
        assert not e['MMIO_instruction_patch_or_fake_return'] and e['PC_observation_may_include_annulled_delay_slots']
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    md=a.cs.Cs(a.cs.CS_ARCH_MIPS,a.cs.CS_MODE_MIPS32|a.cs.CS_MODE_LITTLE_ENDIAN)
    bindings={0x1f5cf0:'candidate A4 copier destination+3c',0x1f5cf4:'candidate A4 nested helper call',
        0x1cb990:'nested helper source halfword+14 corresponds enclosing offset50',
        0x1cb9a4:'nested helper extracts lower24 bits of word+18',0x1cb9a8:'nested helper preserves destination high8 bits',
        0x1f3a8c:'raw metadata flag load+50',0x1f3a90:'raw metadata flag store+50',
        0x1f3a94:'raw metadata full parameter handle load+54',0x1f3a9c:'raw metadata full parameter handle store+54',
        0x1f3b40:'unexecuted nonnull parameter reference GP read',0x1f88a4:'raw copier at outer container+14',
        0x146830:'raw-copy slot size8c',0x146838:'raw-copy caller for declared queue slot',
        0x144124:'actual caller raw flag load',0x144178:'parameter buffer u16 ec load',
        0x1441bc:'parameter buffer u16 ee load',0x131e50:'owner field24 write',0x131e5c:'owner field26 write',
        0x131e60:'unexecuted geometry builder call',0x1441d0:'actual caller JAL frame wrapper',
        0x69c90:'address/type helper returns normally',0x69c94:'address/type helper returns second argument',
        0x140d84:'cache allocation type4',0x140d88:'cache allocation request size11c',
        0x140d8c:'cache actual allocation dispatcher5ef3c call',0x5ef78:'runtime allocator provider GP load',
        0x5ef98:'runtime allocator virtual call not executed'}
    instructions=[]
    for off,meaning in bindings.items():
        ins=next(md.disasm(blob[off:off+4],a.IMAGE+off))
        instructions.append({'VA':hex(a.IMAGE+off),'word_hex':blob[off:off+4].hex(),
            'instruction':ins.mnemonic+' '+ins.op_str,'meaning':meaning})
    im.write_json(STAGE/'native-provenance-audit.json',{'created_utc':now,'VCD_sha256':im.sha(blob),
        'instructions':instructions,'static_queue_and_allocator_call_sites_not_full_runtime_validation':True,
        'binding_of_true_raw_producer_queue_and_actual_MAIN_unproved':True})
    review={'status':'PASS_DISTINCT_METADATA_LAYOUT_REFERENCE_BOUNDARY_AND_ORIGINAL_CALLER',
        'created_utc':now,'prior_sealed_files_verified':15,'contrast_cases':4,'raw_copy_cases':8,
        'caller_cases':4,'bounded_entries':16,'null_only_raw_copy_returns':4,'nonnull_reference_stops':4,
        'copied_nonnull_handle_never_consumed_after_unexecuted_reference_step':True,
        'caller_owned_inputs_separate':True,
        'review_scope':'Same-agent original instruction and stored-result review; exact whole-stack/page checks by harness. No independent CPU engine or camera acceptance.',
        'actual_producer_refcounts_queues_MAIN_hardware_or_recovery':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    im.write_json(STAGE/'orchestration-coordination.json',{'created_utc':now,
        'received_message_id':'msg_59c5899b085d','received_subject':'Mac 内盘实验资料外置协调',
        'reply_message_id':'msg_a7fb84c113a1','reply_request_id':'7347e1af-0b4e-40e5-aeb3-6906df301cc7',
        'reply_durable_enqueued':True,'recipient_read_or_acceptance_proven':False,
        'reply_scope':'Current firmware root and Python environment already external; no current inner-disk experimental output path created or writing. Not a full historical cleanup inventory.',
        'other_project_migration_deletion_or_windows_actions':False,'followup_check_unread_count':0})
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_distinct_metadata_copy_layout_and_original_frame_caller'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage89封存15件与canonical复核；仅Mac，16项/授权保持。Orca维护问题已回复外盘原位保留，无迁移/删除。',
            '候选A4的+3c原字段助手4例保留offset54高8位，不直接当完整参数句柄复制。原1f399c另8例复制flag50和完整handle54；非空4例停引用GP前，空参数及全空嵌套引用4例原返回。',
            '原144124调用者4例：开更新从声明缓冲ec/ee读119/67，经原setter写owner24/26=120/68后停13380c前；关更新经实际JAL绑定帧/owner/rawmetadata。非空副本未在停点后消费，caller为分开的已有所有权声明。',
            '69c90原两指令为第二参数原样返回，非分配器；首次cache静态类型4/size11c→5ef3c运行时提供者未执行。真实原始生产/队列/引用同步/完整几何/MAIN/硬件和全部同机恢复仍缺。'],
        'completion_not_claimed':True}
    result=rel+'/run-initial-20261027/metadata-source-results.json'
    g['latest_stage_evidence']['stage90_raw_metadata_copy_and_caller']={'readme':rel+'/README.md',
        'review':rel+'/completed-evidence-review.json','result':result,
        'scope':'Distinct candidate field copier vs raw8c copy; stop nonnull reference step, separate owned-input caller. Native119/67→120/68 and caller binding, not geometry body/queue/MAIN/hardware.',
        'authorization_unchanged':True,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11'):
            req['evidence'].append(result)
            req['stage90_scope']='16有界入口区分A4字段部分复制与raw8c完整句柄复制；非空引用停GP前，空引用控制原返回。分开已有所有权caller从ec/ee写owner24/26或原JAL绑定帧，完整几何/真实生产/队列/MAIN/硬件与恢复未证。'
    g['next_safe_offline_actions'].append('stage90后追raw8c元数据原始生产与实际队列→143f98消费者绑定，优先核对类型4/11c参数缓冲提供者初始化及非空引用/同步/释放。不要把A4偏移相同当同布局，也不要把原69c90转换当分配器；非空副本未完成引用不得继续消费。caller声明的119/67→120/68不代替真实几何/主录和恢复验收。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 元数据布局、引用边界与原调用者](<'+str(STAGE.relative_to(ROOT))+'/README.md>)：区分候选A4部分位复制与raw8c完整句柄复制；16例，非空停GP引用前，分开caller写119/67→120/68或绑定帧。真实生产/队列/MAIN与硬件恢复未证，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{'schema':'fx3-stage90-native-metadata-copy-caller/1',
        'created_utc':now,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':a.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
        'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
        'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
