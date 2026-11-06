#!/usr/bin/env python3
"""Review original MPR field provenance and keep all camera/recovery gates."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import mpr_open as t
BASE,ROOT=t.BASE,t.ROOT


def sha(d):return hashlib.sha256(d).hexdigest()


def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    t.im.volume();assert not (STAGE/'final-receipt.json').exists()
    assert sha(t.PRIOR.read_bytes())==t.PRIOR_SHA
    pm=json.loads(t.PRIOR.read_text())
    for f in pm['files']:
        d=(ROOT/f['path']).read_bytes();assert len(d)==f['bytes'] and sha(d)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-negative-boundaries-20261027';j=json.loads((run/'mpr-open-results.json').read_text())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'mpr_open.py').read_bytes()
    assert len(j['produced'])==len(j['native_classifications'])==10 and j['bounded_phases']==376
    reuse=j['producer_reuse'];assert reuse['producer_native_phases_reused_not_reexecuted']==280
    assert sha((run/'producer-source.py').read_bytes())==reuse['executed_producer_source_sha256']
    prefix=(STAGE/'mpr_open.py').read_bytes().split(b'def classify(',1)[0]
    assert prefix==(run/'producer-source.py').read_bytes().split(b'def classify(',1)[0]
    assert sha(prefix)==reuse['producer_source_prefix_sha256']
    assert sha((ROOT/reuse['source_run']/'producer-checkpoint.json').read_bytes())==reuse['checkpoint_sha256']
    assert json.loads((run/'producer-checkpoint.json').read_text())==j['produced']
    assert json.loads((run/'producer-reuse-receipt.json').read_text())==reuse
    assert not j['goal_complete'] and not j['persistent_write_release'] and not j['Windows_UU_camera_operations']
    for p in j['produced']:
        assert not p['complete_valid_Open_packet_normal_logging_or_recording_proven']
        assert len(p['unwritten_output_offsets'])==51
        a,b=bytes.fromhex(p['raw98_before_codec_normalization_hex']),bytes.fromhex(p['raw98_hex'])
        assert a[0x82]==b[0x82] and all(a[i]==b[i] for i in range(0x98) if i!=0x7d)
        for e in p['original_builder_events']+sum([q['events'] for q in p['category_queries']],[]):
            assert e['whole_stack_outside_200_byte_declared_frame_unchanged']
            assert e['whole_scratch_outside_declared_outputs_unchanged']
            assert e['whole_original_relocated_ELF_image_unchanged']
            assert not e['stubs_logger_or_success_return_adapters_executed']
            assert all('stub' not in c for c in e['original_local_PLT_and_return_observations'])
        for gap in p['log_gaps']:
            site=int(gap['original_callsite'],16);entry=int(gap['new_independent_entry'],16)
            assert entry==site+4 and t.MPR.disasm(site,entry)[0].endswith('bl #0xc8c70')
            assert not gap['actual_logger_effects_or_normal_continuity_proven']
    for c in j['native_classifications']:
        assert not c['full_receiver_builder_or_real_SPS_MAIN_hardware_or_recovery_proven']
        assert c['decoded']['frame']['original_name']=='29_97'
        if c['label']=='table_row8_negative_control':
            for name in ('chroma','depth'):
                assert not c['decoded'][name]['conversion_completed']
                assert c['decoded'][name]['original_diagnostic_getter_boundary']=='0xffffffc00127d528'
        for e in c['events']:
            assert e['whole_arena_outside_declared_outputs_unchanged']
            assert e['whole_stack_outside_declared_1280_byte_range_unchanged'] and e['whole_original_image_unchanged']
    target=[c for c in j['native_classifications'] if c['label']=='target_HEVC_HD420']
    assert len(target)==2
    assert all([c['decoded'][n]['original_name'] for n in ('coding','frame','quality','chroma','depth')]==
        ['HEVC_MP4','29_97','FH','CHROMA_420','BIT_DEPTH_10'] for c in target)
    assert sum(len(c['events']) for c in j['native_classifications'])==96
    assert all(len(x['seed_dependent_offsets'])==51 for x in j['retained_output_scope'])
    for dirname in ('run-initial-20261027','run-MPR-format-corrected-20261027','run-native-normalization-20261027'):
        assert not json.loads((STAGE/dirname/'attempt-failure.json').read_text())['passing_result']
    mpr=t.MPR;chain=t.prev.prev.prev.src.prev;blob=chain.IMAGE.read_bytes()
    assert sha(mpr.path.read_bytes())==j['original_mpr_sha256']==t.MPR_SHA
    assert sha(blob)==j['original_avcam_sha256']==chain.IMAGE_SHA
    table=mpr.symbols['_ZN3mpr16g_videoParamCombE'];assert table['va']==0x2cb108 and table['size']==312
    table_rows=[{'VPC':i,'original_six_words':list(struct.unpack('<6I',mpr.read(table['va']+24*i,24)))} for i in range(13)]
    def listing(lib,a,z):return {'library':lib.path.name,'VA_range':[hex(a),hex(z)],
        'original_bytes_sha256':sha(lib.read(a,z-a)),'original_disassembly':lib.disasm(a,z)}
    def avlisting(a,z):return {'file_range':[hex(a),hex(z)],'original_bytes_sha256':sha(blob[a:z]),
        'original_disassembly':[{'offset':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
            for i in chain.r.capstone.Cs(chain.r.capstone.CS_ARCH_ARM64,chain.r.capstone.CS_MODE_LITTLE_ENDIAN).disasm(blob[a:z],a)]}
    bindings=[]
    for plt in (0x7d9d0,0x7c350,0x82c00,0x7b7e0,0x83800,0x82d10,0x7ba40,0x7c990,0x82600,0x83730):
        name=mpr.plt[plt];s=mpr.symbols[name]
        bindings.append({'PLT':hex(plt),'symbol':name,'original_defined_VA':hex(s['va']),'size':s['size']})
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    audit={'created_utc':now,'original_mpr_sha256':j['original_mpr_sha256'],
        'original_avcam_sha256':j['original_avcam_sha256'],'original_local_bindings':bindings,
        'table':{'symbol':'_ZN3mpr16g_videoParamCombE','VA':'0x2cb108','bytes':312,'stride':24,'rows':table_rows,
            'local_GOT_resolution_guest_fixture_not_runtime_loader':True},
        'actual_source_relationships':{'original_query':'0xcd40c',
            'native_MAIN_and_proxy_query_callers':'0xd6744 / 0xd6780 set StreamType0/1; return stored into exec request.',
            'declared_exec_input_fields':{'VPC':'0x764','quality':'0x768','frame':'0x76c'},
            'original_builder':'0xd13f8','original_normalization':'0x282b08..282b20',
            'original_ExecOpen_FileFormat_argument':'0xd1ba4 loads exec+77c intoW2 -> Codec::EncOpen at0xd1bbc',
            'queue_message_actual_instance_and_same_epoch_unexecuted':True},
        'explicit_input_scope':'Runtime addresses zero; audio combo/channel and active-video condition are declared inputs. Not original allocated buffers, real media/MAIN owner or full MovieRecInfo source.',
        'logging_scope':'Each original log call is a stop; original return address+4 is a separately declared post-log experiment. Logger effects and whole-function continuity are unproved. Pure helper RETs are original. No logging return/encoder/OSAL provider is fabricated.',
        'normalization_scope':'Only original audio bit-length and picture-quality normalization body, independent of its unexecuted prologue/locks/state; targetquality22 remains22.',
        'source_gap_from_stage105_retained':'Natural app MAIN producer still not shown to produceVPC6; typed declaration is not a fix.',
        'target_quality_scope':'Original upperquality6 -> MPR/Avif22 -> avcamFH. Not measured16M or solved resource/preset matching.',
        'negative8_scope':'Row8 has geometry/category but native GetChroma/GetVideoBitLen returnfe. Both original avcam converters stop at27d528 diagnostic getter, not valid conversion/unknown-name success.',
        'retained_output_scope':'51 seed-dependent bytes; original caller clear/buffer allocation not executed. Not an actual packet, unused-byte proof or Sony uninitialized-memory allegation.',
        'producer_reuse':reuse,'recorded_phases':{'producer_reused':280,'new_receiver_phases':96,'total':376},
        'original_MPR_listings':[listing(mpr,a,z) for a,z in ((0xcd40c,0xcd4f8),(0xd13f8,0xd166c),
            (0xd6698,0xd6808),(0xd1b80,0xd1bc4),(0x282390,0x2823b0),(0x282b08,0x282b20),
            (0xd0758,0xd0800),(0xd11b0,0xd1338))],
        'original_avcam_listings':[avlisting(a,z) for a,z in ((0x134d44,0x134ec0),(0x134fcc,0x135400))],
        'failed_attempt_scope':'Initial expectedstreaming10/AVC4 were wrong for native MPR15/3. AVC name is XAVCS_MP4. Negativefe takes original diagnostic, not a normal conversion. All failed sources/receipts retained; firmware unchanged.',
        'actual_MAIN16M_SPS_hardware_audio_longrun_restore_safe_flash_proven':False}
    put(STAGE/'source-and-scope-audit.json',audit)
    review={'status':j['status'],'created_utc':now,'prior_files_verified':len(pm['files']),
        'produced_cases':10,'native_classifications':10,'recorded_phases':376,'producer_phases_reused':280,
        'receiver_phases_new':96,'producer_source_prefix_equivalence_verified':True,
        'same_agent_review_not_independent_engine':True,'Windows_UU_camera_operations':False,
        'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);rel=str(STAGE.relative_to(ROOT));result_rel=str((run/'mpr-open-results.json').relative_to(ROOT))
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_original_MPR_Open_field_provenance_with_explicit_log_gaps'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage105的13件/canonical及目标卷核对，仅Mac。',
            '原MPR类型表和查询在声明输入/本库重定位下生成MAIN类别15、代理18；不是同实例证明。',
            '原SetEncOpenParam及纯helper分段原执行，原Codec规范化保留22；候选原生字段被原avcam识别HEVC_MP4/29_97/FH/42010。',
            '表行8虽有几何和类别，原色度/位深返回fe并使接收侧进入原诊断getter，不能以表行/检查分支当支持。',
            '证据合计376阶段：核验源码前缀等价后复用生产280阶段，新接收侧96阶段；日志均为未执行的独立输入边界，非连续函数/完整Open。',
            '51字节保留旧值及声明地址0，不能提交硬件；上游MAIN生产缺口、FH资源/16M、真实上下文/同步和恢复保持未验收。',
            '全部16项状态、权限、Mac-only及stage75不可部署原型保持。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage106_original_MPR_Open_fields']={'readme':rel+'/README.md','result':result_rel,
        'source_audit':rel+'/source-and-scope-audit.json','review':rel+'/completed-evidence-review.json',
        'scope':'Original MPR field construction with independent log gaps yields targetHD42010/HEVC_MP4/FH classifications;280 producer phases reused plus96 new receiver phases. Not upstream source fix, valid packet, full Open, measured16M, hardware or recovery.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G10'):
            req['evidence'].extend([result_rel,rel+'/source-and-scope-audit.json'])
            req['stage106_scope']='原MPR构造字段及关联查询生成HD42010/HEVC_MP4身份，但上层quality6原转换为22/FH；日志是未执行的独立输入边界。自然MAIN生产/质量资源16M/完整Open及运行时/实录/恢复仍缺。表行8负例说明不能以类别或表行当支持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Original MPR producer now supplies candidate Open scalar provenance: HD42010 with main format15 and quality22/FH; it differs from streamingraw10/4208. Row8 still has geometry/category but invalid color/depth. Conditional post-log experiments and scalar classification are not normal Open, frontend source fix, resource alignment or hardware support.',
        'actual_MAIN_SPS_16M_shared_instance_or_recovery_proven':False})
    g['next_safe_offline_actions'].append('stage106后核对MPR ExecEncOpen/Codec::EncOpen完整消息、通道/实例和配置代次，以及候选原quality6->22/FH与资源matcher/16M私有预置的实际绑定。保留stage105自然MAIN来源缺口；不把表行8或类别15当支持，不提交保留51字节旧值/声明零地址的参数，不将独立日志后入口当连续正常执行。全部实录与同机恢复门槛保持，仅Mac。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 原MPR Open字段来源](<'+rel+'/README.md>)：声明候选由原构造/转换识别HEVC_MP4、HD42010、29_97、FH；280生产阶段复用+96接收阶段，原日志未执行。上游来源/16M资源/完整Open/实录恢复仍缺，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():
            d=p.read_bytes();files.append({'path':str(p.relative_to(ROOT)),'bytes':len(d),'sha256':sha(d)})
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage106-original-MPR-Open-fields/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':t.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':sha((STAGE/'final-receipt.json').read_bytes()),
        'recorded_phases':376,'new_receiver_phases':96,'producer_phases_reused':280,'goal_complete':False}))


if __name__=='__main__':main()
