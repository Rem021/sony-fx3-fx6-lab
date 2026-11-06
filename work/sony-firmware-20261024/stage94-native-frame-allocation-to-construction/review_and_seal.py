#!/usr/bin/env python3
"""Review stored native allocation evidence and preserve every acceptance gate."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import frame_allocation as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def verify_manifest(path,sha):
    assert im.sha(path.read_bytes())==sha
    j=json.loads(path.read_text())
    for f in j['files']:
        raw=(ROOT/f['path']).read_bytes()
        assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    return len(j['files'])


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage93-native-frame-header-and-crop-reconciliation/final-receipt.json'
    previous_files=verify_manifest(prior,a.PRIOR_SHA)
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    source_manifest=BASE/'stage91-native-type4-first-cache-buffer/final-receipt.json'
    source_sha=json.loads((BASE/'stage92-native-geometry-builder-and-IRQ-scope/final-receipt.json').read_text())['previous_manifest_sha256']
    source_files=verify_manifest(source_manifest,source_sha)
    source=BASE/'stage91-native-type4-first-cache-buffer/run-corrected-call-frame-20261027/type4-cache-results.json'
    metadata=bytes.fromhex(json.loads(source.read_text())['cases'][0]['declared_metadata48_hex'])
    run=STAGE/'run-initial-20261027';j=json.loads((run/'frame-allocation-results.json').read_text())
    assert not (run/'failed-attempt.json').exists()
    assert j['status']=='PASS_NATIVE_TYPE5_FRAME_ALLOCATION_THROUGH_ORIGINAL_CONSTRUCTION_WITH_EXPLICIT_IRQ_GAPS'
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'frame_allocation.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'frame_allocation.py').read_bytes()
    assert j['source_receipt']['prior_manifest_sha256']==a.PRIOR_SHA
    assert j['source_receipt']['stage91_result_sha256']==im.sha(source.read_bytes())
    path=BASE/'stage2/extraction/files/nflasha15/codec/vcd_firmware_imola2.bin';blob=path.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(path.relative_to(BASE))]
    assert len(metadata)==48 and struct.unpack_from('<HH',metadata)==(119,67)
    assert len(j['cases'])==5 and j['bounded_phases']==203
    all_events=[];normal=0;empty=0;allocations=0
    ctor_shas={165:'3cb43c3244aabd4145b3ee06b012d808074ed132804bc6a622dc2541e949e2c5',
               195:'78de61e955af570d831e2e7dcd82dd5f29818683c03f9d6399656bafaa782620'}
    for c in j['cases']:
        es=c['events'];all_events+=es
        seed,flag,exhaust=c['seed'],c['declared_update_byte50'],c['frame_pool_exhausted']
        assert seed in (165,195) and flag in (0,16)
        assert len(es)==(143 if exhaust else 15)
        pages={int(k,16):bytes.fromhex(v) for k,v in c['final_regions'].items()}
        assert set(pages)==set(a.old.PAGES)|{a.REG_PA,a.ARENA_PA,a.POOL_PA}
        for p in a.old.PAGES:assert len(pages[p])==4096
        assert len(pages[a.REG_PA])==4096 and len(pages[a.ARENA_PA])==0x4000
        assert len(pages[a.POOL_PA])==0x38000
        r,arena,pool=pages[a.REG_PA],pages[a.ARENA_PA],pages[a.POOL_PA]
        assert a.old.word(r,0)==0x4d4d6772 and r[4]==255
        assert a.old.word(r,0x14)==a.ARENA and a.old.word(r,0x18)==0x4000
        assert a.old.word(r,0x1c)==0x1c80
        assert [a.old.word(r,0x20+i*4) for i in range(110)]==[a.P4 if i==4 else a.P5 if i==5 else 0 for i in range(110)]
        assert c['native_parameter_handle']==a.H4 and c['native_type4_reference_byte']==1
        assert c['native_type5_reference_byte']==1 and c['native_free_type4']==127
        assert c['native_free_type5']==(0 if exhaust else 127)
        for kind,spec in a.SPECS.items():
            desc=struct.unpack_from('<4I',blob,spec['rom']-a.IMAGE)
            assert desc==(kind,spec['physical'],spec['bytes'],128)
            assert desc[2]//desc[3]==spec['block']
            n=128 if kind==5 and exhaust else 1
            p=spec['provider']-a.ARENA;h=spec['handles']-a.ARENA
            assert a.old.word(arena,p)==a.VTABLE and a.old.word(arena,p+4)==kind
            assert struct.unpack_from('<III',arena,p+8)==(spec['physical'],spec['bytes'],128)
            assert a.old.word(arena,p+0x14)==spec['handles']
            assert a.old.word(arena,p+0x18)==(spec['handles']+n*28 if n<128 else 0)
            assert struct.unpack_from('<H',arena,p+0x1c)[0]==128-n
            assert a.old.word(arena,p+0x34)==spec['block']
            for i in range(128):
                wanted=(spec['physical']+i*spec['block'],0x11c if kind==4 and i<n else spec['block'],
                        1 if i<n else 0,spec['provider'],
                        spec['handles']+(i+1)*28 if i>=n and i<127 else 0,0,0)
                assert struct.unpack_from('<7I',arena,h+i*28)==wanted,(kind,i)
        expected_pool=bytearray([seed])*a.POOL_SIZE
        m=a.PHYS4-a.POOL_PA+0xec;expected_pool[m:m+48]=metadata
        assert pages[a.old.FRAME_PA]==bytes([0x73])*4096
        assert struct.unpack_from('<II',pages[a.old.HANDLES_PA])==(a.old.FRAME_PA,a.old.PACK_PA)
        assert pages[a.old.HANDLES_PA][8:]==bytes(4088)
        assert a.old.word(pages[a.old.SRC_PA],0x54)==a.H4
        assert pages[a.old.SRC_PA][0x50]==flag
        assert es[7]['V0']==hex(a.H4) and es[7]['stop']=='returned_via_original_jr_ra'
        assert [int(x['entry'],16)-a.IMAGE for x in es[-4:]]==[0x143f98,0x143fc4,0x144030,0x1440c8]
        assert es[-3]['pc']==hex(a.IMAGE+0x143ff8)
        assert es[-2]['pc']==hex(a.IMAGE+0x144090)
        assert es[-2]['V0']==hex(0 if exhaust else a.H5)
        assert all(hex(a.IMAGE+off) in es[-3]['CODE_observed_PCs'] for off in (0x143fdc,0x143ff4))
        assert all(hex(a.IMAGE+off) in es[-2]['CODE_observed_PCs'] for off in (0x14407c,0x5ef3c,0x606d0,0x5fff0,0x144088))
        allocations+=1
        if exhaust:
            empty+=1
            assert seed==165 and flag==16 and c['native_frame_handle']==0 and c['native_frame_VA'] is None
            assert c['frame_after_hex'] is None and not es[-1]['frame_checkpoints']
            assert es[-1]['pc']==hex(a.IMAGE+0x144334)
            assert es[-1]['SP']==hex(a.BODY_SP)
            assert c['preallocated_frame_handles']==[a.H5+i*28 for i in range(128)]
            assert [int(e['V0'],16) for e in es[11:139]]==c['preallocated_frame_handles']
            assert all(hex(a.IMAGE+0x1f8550) not in e['CODE_observed_PCs'] for e in es)
            allocations+=128
        else:
            normal+=1
            assert c['native_frame_handle']==a.H5 and c['native_frame_VA']==hex(a.FRAME)
            assert c['preallocated_frame_handles']==[]
            f=bytes.fromhex(c['frame_after_hex']);assert len(f)==0x4f0
            at=a.PHYS5-a.POOL_PA;expected_pool[at:at+len(f)]=f
            assert struct.unpack_from('<HH',f,4)==(120,68)
            assert struct.unpack_from('<HH',f,0x10)==(1920,1088)
            assert a.old.word(f,0x4c8)==(a.H4 if flag else 0) and f[0x4c4]==flag
            assert f[0x143]==seed and f[0x27c:0x280]==bytes([seed])*4
            assert f[0x14:0x28]==bytes([seed])*20
            checkpoints=es[-1]['frame_checkpoints']
            assert checkpoints==[{'point':'original_constructor_entry','A0':hex(a.FRAME)},
                {'point':'constructor_return_to_original_parent','frame_VA':hex(a.FRAME),
                 'frame_sha256':ctor_shas[seed],'parameter_handle':0,'update_flag':0}]
            assert all(hex(a.IMAGE+off) in es[-1]['CODE_observed_PCs'] for off in
                       (0x1440d0,0x69c90,0x14411c,0x1f8550,0x1f87b8,0x144124,0x131888))
            assert es[-1]['pc']==hex(a.IMAGE+(0x131c20 if flag else 0x1441e4))
            assert es[-1]['SP']==hex(a.BODY_SP-(0x80 if flag else 0))
        assert pool==bytes(expected_pool)
        assert c['raw_metadata_still_declared_not_real_message']
        assert not c['host_sets_frame_address_descriptor_handle_free_count_or_return_value']
        assert not c['actual_MAIN_IRQ_sync_HEVC_video_or_recovery_proven']
    assert normal==4 and empty==1 and allocations==133 and len(all_events)==203
    for e in all_events:
        assert e['all_regions_and_entire_stack_exact_poststate_checked']
        assert e['image_unchanged_except_native_registry_global']
        assert not e['memory_read_write_hooks_installed'] and not e['native_interrupts']
        assert e['PC_observation_may_include_annulled_delay_slots'] and not e['MMIO_instruction_patch_or_fake_return']
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    public=json.loads((STAGE/'public-source-check.json').read_text())
    assert len(public['sources'])==2 and not public['new_flash_or_recovery_authority']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    md=a.cs.Cs(a.cs.CS_ARCH_MIPS,a.cs.CS_MODE_MIPS32|a.cs.CS_MODE_LITTLE_ENDIAN)
    offsets={0x5d49c:'executed native runtime registry binding',0x5d304:'unexecuted CACHE boundary',
        0x5d988:'executed native type registration store',0x5ef78:'executed native registry global read',
        0x5ef98:'executed dispatch through original fixed-pool vtable',0x60034:'executed native free-count store',
        0x6003c:'executed native free-list head store',0x60730:'executed initial native reference-byte store',
        0x143fc0:'unexecuted GP lock-ID read',0x143fdc:'executed original parent descriptor first store',
        0x143ff4:'executed original empty frame-handle slot',0x143ff8:'unexecuted lock-ID save',
        0x143ffc:'unexecuted interrupt-control encoded word',0x144074:'executed allocation type5',
        0x144078:'executed allocation size4f0',0x14407c:'executed native allocator call',
        0x144088:'executed original parent handle store',0x144090:'unexecuted IRQ-release boundary',
        0x1440c8:'original native status branch after IRQ gap',0x1440d0:'executed native handle physical load',
        0x14411c:'executed original frame-constructor call',0x144124:'native constructor return checkpoint',
        0x1f8740:'native new-frame parameter-handle initialization',0x131c1c:'executed new parameter pointer assignment',
        0x131c20:'unexecuted GP/reference increment boundary',0x1441e4:'unexecuted external virtual lookup',
        0x144334:'unexecuted exhausted-pool diagnostic boundary'}
    rows=[]
    for off,meaning in offsets.items():
        ins=next(md.disasm(blob[off:off+4],a.IMAGE+off),None)
        rows.append({'VA':hex(a.IMAGE+off),'word_hex':blob[off:off+4].hex(),
            'instruction':ins.mnemonic+' '+ins.op_str if ins else 'not decoded by this MIPS decoder',
            'meaning':meaning})
    im.write_json(STAGE/'native-provenance-and-boundaries.json',{'created_utc':now,'VCD_sha256':im.sha(blob),
        'instructions':rows,'ROM_descriptors':[{'type':k,'file_offset':hex(s['rom']-a.IMAGE),
             'words':list(struct.unpack_from('<4I',blob,s['rom']-a.IMAGE)),'block_bytes':s['block']} for k,s in a.SPECS.items()],
        'original_vtable_allocation_slot_VA':hex(a.VTABLE+0x10),
        'original_vtable_allocation_target':hex(a.old.word(blob,a.VTABLE-a.IMAGE+0x10)),
        'native_frame_address_is_from_original_type5_returned_handle':True,
        'raw_reference_and_metadata48_are_declared':True,'new_parameter_reference_or_IRQ_proven':False,
        'actual_MAIN_encoder_video_or_independent_recovery_proven':False})
    review={'status':'PASS_STORED_NATIVE_POOL_ALLOCATION_CALLER_CONSTRUCTION_AND_EXHAUSTION_EVIDENCE',
        'created_utc':now,'prior_sealed_files_verified':previous_files,'stage91_source_files_verified':source_files,
        'cases':5,'formal_phases':203,'type5_allocation_requests':133,'type5_native_successes':132,
        'type5_native_exhaustion_failures':1,'type4_parameter_allocations':5,
        'normal_constructor_chains':4,'all128_type4_and_type5_records_checked_per_case':True,
        'whole_physical_pools_checked_against_metadata_and_constructor_scope':True,
        'review_scope':'Same-agent source and saved-output review plus harness exact image/all-region/full-stack checks. No independent engine, actual full boot or camera acceptance.',
        'public_recovery_case_scope':'User-reported A7CII application-mode recovery; not FX3 or independent failure-entry proof.',
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_frame_pool_allocation_through_original_frame_constructor_and_header'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':old['progress_audit']['classification'],
        'basis':['stage93封存及stage91参数源封存复核；Mac-only、16项与授权保持。',
            '同一RAM原type4/type5池构造及原分配；原parent原生置空slot、获取type5句柄并从句柄取得地址，连续进入原帧构造/几何/header，减少预置帧地址来源。注册/CACHE/GP锁ID与IRQ仍有明确未执行边界。',
            '5场景203阶段；4正常链、128原帧预分配耗尽后第129次原返回空并转错误分支，未入构造。source参数ref仍1，RAW/48字节内容仍声明，未声称共享引用完成或真实MAIN。',
            '重读A7CII Issue31见多名用户刷后故障及视频模式进系统后回滚的报告和成功回复；属于用户报告且依赖仍可启动的应用路径，不构成FX3独立救砖或flash回读证据。',
            'fwtool PR52仍Open且作者解包测试列表含FX3；不等于修改包刷写/恢复。MAIN编码、视频音画/长录/冷启动、同机备份与独立救砖均未验收。'],
        'completion_not_claimed':True}
    result=rel+'/run-initial-20261027/frame-allocation-results.json'
    g['latest_stage_evidence']['stage94_native_frame_allocation']={'readme':rel+'/README.md',
        'review':rel+'/completed-evidence-review.json','result':result,'public_sources':rel+'/public-source-check.json',
        'scope':'Original type5 allocator -> parent native handle translation -> constructor/header in same RAM, with explicit registration/CACHE/IRQ gaps. Type4 source ownership exists but declared metadata production/new sharing remain unproved.',
        'authorization_unchanged':True,'goal_complete':False}
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':prior.parent.name,
        'finding':'Original frame allocation and parent handle translation now executed offline, replacing the previously declared frame address within explicit IRQ/CACHE gaps. Source raw producer, new reference and real MAIN/hardware still unproved. A7CII app-mode recovery report is not an independent FX3 recovery path.',
        'hardware_or_independent_recovery_proven':False})
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11'):
            req['evidence'].append(result)
            req['stage94_scope']='同RAM原type4参数分配与type5帧分配→原caller地址转换/构造/header；5场景203阶段，耗尽失败原分支。注册/CACHE/IRQ/新引用/RAW真实生产者/MAIN硬件仍未证，不能替代实机。'
        if req['id'] in ('G15','G16'):
            req['evidence'].append(rel+'/public-source-check.json')
            req['stage94_public_recovery_scope']='A7CII Issue31用户报告通过视频模式进入应用后用项目回滚，有成功回复；非FX3、非独立恢复入口/健康备份/flash回读验收。'
    g['next_safe_offline_actions'].append('stage94已接原type5帧分配到构造/header，勿重复此目标。继续追原参数引用共享GP/IRQ与外部虚分派/MAIN及owner历史输入；不捏造IRQ返回或绑定虚表来通过。恢复研究区分仍可启动的应用模式回滚与不能启动时独立入口；A7CII反馈不替代FX3同机备份、受限恢复回读、独立救砖。Windows仍不可用，仅Mac离线。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n'
    assert text.count(marker)==1
    entry='- [2026-10-27 FX3 原帧分配接原构造与恢复案例边界](<'+rel+'/README.md>)：原type5分配句柄→原caller地址转换→构造/header，5场景203阶段含耗尽；IRQ/MAIN/实际编码及FX3救砖仍未验。A7CII应用模式回滚反馈单列，仅Mac。'
    assert entry not in text
    text=text.replace(marker,marker+'\n'+entry+'\n',1)
    assert canonical.read_bytes()==before
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{'schema':'fx3-stage94-native-frame-allocation/1',
        'created_utc':now,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':a.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
        'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
        'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
