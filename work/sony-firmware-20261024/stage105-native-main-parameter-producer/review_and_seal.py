#!/usr/bin/env python3
"""Seal original MAIN conversion evidence without relaxing the camera goal."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import main_parameter as t
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
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-checker-sentinel-controls-20261027';j=json.loads((run/'main-parameter-results.json').read_text())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'main_parameter.py').read_bytes()
    assert j['matrix_cases']==32 and j['negative_cases']==10 and len(j['native_checker_fixtures'])==12
    assert j['bounded_phases']==108 and j['native_MAIN_VPC_set']==[0,1,2,3,4,5,7,9,10,12]
    assert not j['goal_complete'] and not j['persistent_write_release'] and not j['Windows_UU_camera_operations']
    for c in j['cases']+j['native_checker_fixtures']:
        for e in c['events']:
            assert e['whole_stack_outside_declared_frame_unchanged']
            assert e['whole_scratch_outside_declared_outputs_unchanged']
            assert e['mapped_original_ELF_guest_readonly_and_no_patch_or_resolution_requested']
            assert not e['imports_logs_or_return_adapters_executed']
    good=[c for c in j['cases'] if c['local_conversion_reaches_audio_boundary']]
    groups={}
    for c in good:
        k=tuple(c['declared_selectors'].values());groups.setdefault(k,[]).append(c['native_core_at_stop_hex'])
        assert c['native_core_vpc_quality_frame'][1:]==[6,3]
        assert set(c['core_stores'])>={'0x170','0x174','0x178'}
    assert len(groups)==16 and all(len(v)==2 and v[0]==v[1] for v in groups.values())
    diag={x['label']:x['native_diagnostic_ID'] for x in j['native_checker_fixtures']}
    assert diag=={'declared_target_not_app_produced':0x40f,'original_app_core_zero_other_fields':0x40f,
        'VPC_sentinel':0x402,'quality_sentinel':0x403,'frame_sentinel':0x404,'synthetic_large_VPC_control':0x40f}
    assert not json.loads((STAGE/'run-initial-20261027/attempt-failure.json').read_text())['passing_result']
    assert json.loads((STAGE/'run-call-bounds-20261027/main-parameter-results.json').read_text())['bounded_phases']==84
    app,mpr=t.APP,t.pp.MPR
    assert sha(app.path.read_bytes())==j['original_app_sha256']=='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
    assert sha(mpr.path.read_bytes())=='9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c'
    symbol='_ZN3mpr16SetMovieRecParamERKNS_13movieRecParamE'
    assert app.plt[0x15944f0]==symbol and mpr.symbols[symbol]['va']==0xf0ff0
    s=app.elf.get_section_by_name('.text');base=s['sh_addr'];sites=[]
    for n,(w,) in enumerate(struct.iter_unpack('<I',s.data())):
        if w&0x7c000000!=0x14000000:continue
        imm=w&0x3ffffff;imm=imm-(1<<26) if imm&(1<<25) else imm;pc=base+n*4
        if pc+imm*4==0x15944f0:sites.append(hex(pc))
    assert sites==['0x2e6f7bc','0x2e6f9b0']
    def listing(lib,a,z):return {'library':lib.path.name,'VA_range':[hex(a),hex(z)],
        'bytes_sha256':sha(lib.read(a,z-a)),'original_disassembly':lib.disasm(a,z)}
    def text(a):return app.read(a,240).split(b'\0')[0].decode()
    table_symbol='_ZN3mpr16g_videoParamCombE';table=mpr.symbols[table_symbol]
    assert table['size']==312
    reloc=[]
    for section in mpr.elf.iter_sections():
        if section.name!='.rela.dyn':continue
        syms=mpr.elf.get_section(section['sh_link'])
        for v in section.iter_relocations():
            if v['r_offset'] in (0x2f9a40,0x2f9658):
                sym=syms.get_symbol(v['r_info_sym'])
                reloc.append({'GOT_VA':hex(v['r_offset']),'type':v['r_info_type'],'addend':v['r_addend'],
                    'symbol':sym.name,'definition_VA':hex(sym['st_value']),'bytes':sym['st_size']})
    assert len(reloc)==2
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    audit={'created_utc':now,'original_app_sha256':j['original_app_sha256'],
        'original_mpr_sha256':sha(mpr.blob),
        'direct_SetMovieRecParam_calls':{'text_VA':hex(base),'text_bytes':len(s.data()),'sites':sites,
            'symbol':symbol,'PLT':'0x15944f0','defined_mpr_VA':'0xf0ff0','indirect_calls_excluded':True},
        'original_names':[{'VA':hex(a),'text':text(a)} for a in (0x398d4f8,0x398d510,0x398a373,0x398a397,0x398a3f9)],
        'original_tables':[{'VA':hex(a),'hex':app.read(a,n).hex()} for a,n in ((0x398965c,16),(0x398966c,26),(0x3989688,26))],
        'producer_scope':'Original prologue to first log; independent2e6ea58 with prologue-preserved pointers/frame. Prior memset/other initialization/logs not executed. Only core fields/adjacent observed stores are results; no complete1bd parameter or normal wrapper call.',
        'producer_result':'32 declared format5..12 x variant0/1 x A5/C3 cases produce MAIN VPC0,1,2,3,4,5,7,9,10,12; quality6/frame3. No VPC6 in this branch. Does not exclude other writers, later state, alternative input producer or firmware modification.',
        'checker_scope':'Twelve explicit zero-background1c0 fixtures; target6 and large synthetic VPC both reach final diagnostic40f. Sentinel13/ff/c hit402/403/404. Neither final log nor native checker return executed, no complete parameter or valid profile acceptance.',
        'global_copy_static_scope':{'setter':'0xf1088..f1094','getter':'0xf1258..f1268',
            'shared_ELF_VA':'0x38c810','native_copy_length':'0x1bd',
            'record_context_copy':'0xccb04..ccb10 -> MovieRecInfo+58',
            'copy_provider_locks_actual_global_value_and_runtime_unexecuted':True},
        'original_app_listings':[listing(app,a,z) for a,z in ((0x2e6e5d8,0x2e6e6a8),
            (0x2e6ea58,0x2e6ea84),(0x2e6ec58,0x2e6ec74),(0x2e6ed04,0x2e6ed24),
            (0x2e6ed84,0x2e6edc8),(0x2e6ee28,0x2e6ee50),(0x2e6eeb0,0x2e6efa8),
            (0x2e6f038,0x2e6f0a8),(0x2e6f0f8,0x2e6f140),(0x2e6f45c,0x2e6f4c0),
            (0x2e6f7b8,0x2e6f7c4),(0x2e6f9ac,0x2e6f9bc))],
        'original_mpr_listings':[listing(mpr,a,z) for a,z in ((0xf0ff0,0xf1120),(0xf1238,0xf1284),
            (0xcca10,0xccb1c),(0xcc4d4,0xcc824),(0xd6698,0xd6808),(0xcd40c,0xcd4f8))],
        'next_codec_table':{'symbol':table_symbol,'defined_VA':hex(table['va']),'bytes':table['size'],
            'row_bytes_from_original_query':24,'original_table_hex':mpr.read(table['va'],table['size']).hex(),
            'GOT_relocations':reloc,'original_query':'0xcd40c','actual_query_or_EnqueueOpen_not_executed':True},
        'official_crosscheck':{'checked_utc':now,'classic_FX3':True,
            'menu_URL':'https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888827.html',
            'File_Format_URL':'https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868279.html',
            'fact':'Current classicFX3 file-format page lists HS4K, S4K/HD, S-I4K/HD/DCI4K; no HS HD main entry.',
            'not_proof_of_internal_enum_numbers_or_absolute_hardware_inability':True},
        'host_failure_correction':'Initial allowed-range end excluded original2e6f070 call. Extended4 bytes, plus read invalid-rate diagnostic prefix to its first call. Firmware unchanged; failure and84-phase intermediate retained.',
        'actual_MAIN16M_42010_SPS_hardware_audio_longrun_restore_or_safe_flash_proven':False}
    put(STAGE/'source-and-scope-audit.json',audit)
    review={'status':j['status'],'created_utc':now,'prior_files_verified':len(pm['files']),
        'matrix_cases':32,'negative_cases':10,'checker_cases':12,'bounded_phases':108,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'complete_producer_checker_runtime_hardware_or_recovery_proven':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);rel=str(STAGE.relative_to(ROOT));result_rel=str((run/'main-parameter-results.json').relative_to(ROOT))
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_original_MAIN_parameter_producer_gap_and_generic_checker_scope'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage104的13件封存/canonical及目标卷核对；仅Mac。',
            '补到应用SetMovieRecParam原MAIN三字生产；8格式入口x2选择x2旧值32组未生成目标VPC6，质量6/帧率3原生成。10负例到原诊断。',
            '原MPR检查在声明候选及大类型合成值都到结束诊断40f；13/ff/c哨兵对照到402/403/404，不能把检查分支当支持/合法配置。共108有界阶段。',
            'Set/Get共享全局1bd复制及MovieRecInfo+58来源、Open队列到原类型表的静态连接已定位；复制/锁/当前实例/完整Open未执行。',
            '新的上游MAIN生产缺口改变下一步：需与资源/码率一起解决真实参数来源和全消费者绑定，不能仅改底层或绕过检查。',
            '全部16项状态、权限、Mac-only和stage75不可部署原型保持；目标实录与同机恢复尚未验收。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage105_MAIN_producer_gap']={'readme':rel+'/README.md','result':result_rel,
        'source_audit':rel+'/source-and-scope-audit.json','review':rel+'/completed-evidence-review.json',
        'scope':'One original MAIN converter does not produce candidateVPC6 under32 declared cases; generic checker final branch is weaker than supported-type validation.108 bounded phases, no complete MovieRecParam/runtime/Open/MAIN/recovery.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G10'):
            req['evidence'].extend([result_rel,rel+'/source-and-scope-audit.json'])
            req['stage105_scope']='原应用此MAIN转换分支32组未生成候选VPC6，质量6/帧率3可生成；新增上游参数来源缺口。MPR特定哨兵检查的结束分支不是有效配置/硬件准入。全部实际MAIN/同步/完整初始化及恢复状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'MPR media RecStart depends on a separately saved MovieRecParam. Original app MAIN converter matrix lacks targetVPC6, while generic checker admits even a large synthetic type to its final diagnostic. Existing declared candidate/core tests cannot establish natural MAIN producer or full semantic admission.',
        'actual_MAIN_SPS_hardware_shared_instance_or_recovery_proven':False})
    g['next_safe_offline_actions'].append('stage105后从原MPR g_videoParamComb表/查询cd40c和EnqueueExecEncOpen/消费者继续核对类型6与主/代理配置；追实际Set/GetMovieRecParam和MovieRecInfo+58复制来源、同步/代次及应用生产者此处缺VPC6的上游改动需求。不用通用检查到40f当支持证明，不把合成大类型交下游，不以覆盖一个字段替代完整有效配置。目标42010/16M MAIN和实机/同机恢复要求保持，仅Mac。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
          'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 原MAIN参数生产者缺口](<'+rel+'/README.md>)：此格式转换32组无候选VPC6，通用检查结束分支不足以证明支持；108阶段，配置/编码Open来源继续追，实录与恢复未验收，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():
            d=p.read_bytes();files.append({'path':str(p.relative_to(ROOT)),'bytes':len(d),'sha256':sha(d)})
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage105-native-main-producer/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':t.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':sha((STAGE/'final-receipt.json').read_bytes()),
        'bounded_phases':108,'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
