"""Register new source/code evidence and user-resumed goal without new grants."""
from pathlib import Path
from hashlib import sha256,sha1
from datetime import datetime,timezone
from copy import deepcopy
from io import BytesIO
import ast,importlib.util,json,os,plistlib,re,stat,struct,subprocess
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];REL=str(H.relative_to(R))
P=B/'stage215-AP-boot-capture-worker-candidate'
PREV='2fac85a39d9a28e748c4dfd5dd7d278c2c418426f4e7e550c0aa8af513407287'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):(H/n).open('x').write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def volume():
 v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']));assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists() and sha(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==3959
for x in prior['files']:
 p=R/x['path'];s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_size==x['bytes'] and sha(p)==x['sha256']
source=[]
for name in ['source-capture.json','source-retry-capture.json','source-followup-capture.json']:
 for x in json.loads((H/name).read_text())['files']:
  if 'sha256' not in x:continue
  p=H/x['output'];raw=p.read_bytes();assert len(raw)==x['bytes'] and sha256(raw).hexdigest()==x['sha256']
  assert sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()==x['git_blob_sha1'];source.append(x)
assert len(source)==24 and len({(x['repo'],x['path']) for x in source})==24
for slug,count in [('dino2048--zv-e10-toolkit',152),('cokeenet--zve10-qemu',919),('YuuLuo--a7c2-service-preload',5)]:
 head=json.loads((H/'upstream'/(slug+'-head.json')).read_text());tree=json.loads((H/'upstream'/(slug+'-tree.json')).read_text());assert not tree['truncated'] and len(tree['tree'])==count and head['sha']==tree['sha']
 rows={x['path']:x for x in tree['tree']}
 rec=next(x for x in json.loads((H/'git-tree-object-proof.json').read_text())['repositories'] if x['repo'].replace('/','--')==slug)
 assert rec['commit']==head['sha'] and rec['expected_root_tree']==head['commit']['tree']['sha'] and rec['recursive_members']==count
 assert len(rec['verified_tree_objects'])==1+sum(x['type']=='tree' for x in tree['tree'])
 assert next(x for x in rec['verified_tree_objects'] if x['path']=='/')['git_tree_sha1']==head['commit']['tree']['sha']
 for x in source:
  if x['repo'].replace('/','--')==slug:assert x['commit']==head['sha'] and rows[x['path']]['sha']==x['git_blob_sha1']
proof=json.loads((H/'portability-proof.json').read_text());assert len(proof['source_lines'])==23 and len(proof['original_ranges'])==4 and len(proof['raw_instruction_checks'])==16
for x in proof['source_lines']:assert (H/x['path']).read_text().splitlines()[x['line']-1]==x['text'] and sha(H/x['path'])==x['source_sha256']
raw=(H/'originals/app/bin/bootin.elf').read_bytes();assert sha256(raw).hexdigest()==proof['original_bootin_sha256']=='dab3ce4b6c28a6c9ffd9f0b893dce1d08f3ee7302a09df87e518409e728be2f2'
e=ELFFile(BytesIO(raw))
def original(va,n):
 s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']);at=s['p_offset']+va-s['p_vaddr'];return raw[at:at+n],at
for x in proof['original_ranges']:
 b,at=original(int(x['start'],16),x['bytes']);assert at==x['file_offset'] and b==(H/x['output']).read_bytes() and sha256(b).hexdigest()==x['sha256']
for x in proof['raw_instruction_checks']:
 at=int(x['VA'],16);w=struct.unpack('<I',original(at,4)[0])[0];assert w==int(x['word'],16)
 if 'mask' in x:assert w&int(x['mask'],16)==int(x['expected'],16)
 else:
  width=26 if x['meaning']=='b' else 19;bits=w&0x3ffffff if width==26 else (w>>5)&0x7ffff
  assert at+((bits-(1<<width) if bits>>(width-1) else bits)<<2)==int(x['branch_target'],16)
# Re-read the five chosen files from the saved official read-only Ext2 images.
p=B/'stage2/extraction/read_filesystems.py';assert sha(p)=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
sp=importlib.util.spec_from_file_location('readonly216seal',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
loc=json.loads((H/'FX3-boot-mode-locators.json').read_text());assert sum(loc['regular_unique_inodes_scanned'].values())==847
chosen=loc['selected_originals']+[dict(image='nflasha15.img',image_sha256='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5',inode=80993,output='originals/app/bin/change_mode.sh',sha256='0c277c24e503f214ebdb651ea1bec569ebd31d6c19c27156f3df29394621fc75')]
assert len(chosen)==5
for image in {x['image'] for x in chosen}:
 f=m.Ext2(B/'stage2/extraction'/image)
 for x in chosen:
  if x['image']==image:assert sha256(f.b).hexdigest()==x['image_sha256'] and f.data(x['inode'])==(H/x['output']).read_bytes() and sha(H/x['output'])==x['sha256']
 f.b.close();f.f.close()
for path in H.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert sha(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.5.0.zip')=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
release=json.loads((P/'release-receipt.json').read_text())
for x in release['files']:assert sha(R/'outputs/fx3-recovery-adapter'/x['path'])==x['sha256']
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
 if '://' not in link and link not in ('final-receipt.json','verification-receipt.json'):assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes();assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-recheck.json').read_text());assert native['goal']['status']=='active'
assert len(old['requirements'])==16 and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('verification-receipt.json',dict(schema='fx3-stage216-new-source-and-mode-proof-verification-v1',created_utc=now,
 status='PASS_PINNED_SOURCE_AND_ORIGINAL_WORD_PROOF',previous_manifest_sha256=PREV,previous_members_reverified=3959,
 upstream_fixed_sources=24,complete_tree_member_counts=[152,919,5],git_tree_objects_independently_reconstructed=133,source_lines_bound=23,original_ELF_ranges=4,
 original_instruction_word_or_branch_checks=16,saved_official_image_regular_unique_inodes_scanned=847,original_files_reextracted_and_matched=5,
 original_text_bytes=7952,decoded_instruction_bytes=7940,explicit_skipped_data_bytes=12,
 selected_mode_parser_requires_LF_after_ASCII3=False,actual_camera_boot_with_one_byte_mode_verified=False,
 reviewed_independent_rescue_requires_Pico=True,pure_PC_USB_recovery_demonstrated=False,
 no_upstream_program_or_Sony_code_or_guest_executed=True,root_or_camera_or_USB_operations=0,
 no_new_runtime_tests=True,existing58_tests_not_repeated_or_recounted=True,release04_and05_source_and_archives_unchanged=True,
 root01_bundle_unchanged=True,root01_job_absent=True,all16_requirements_and_authorizations_unchanged=True,
 native_goal_user_resumed_active=True,goal_complete=False,persistent_write_release=False))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
 research_activity='Pinned24new reference files from ZV-E10 toolkit bd2b4ac and QEMU48e6490 plus service1619f93, complete trees152/919/5. Verified independent route needs Pico, SD route remains untested candidate, QEMU display incomplete. Checked write-relative/read-absolute offsets, empty same-reference diff and floor64KiB verify gap. FX3 saved images847inodes/5files, bootin4ranges/16word+branch checks show selected ASCII3 parse has no mandatoryLF; do not port ZV-E10 repair bytes or claim full boot health. No upstream/Sony/guest/root/USB/device execution. User resumed native goal active;16requirements and195pending unchanged,0.5 retained.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-recheck.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only; user resumed goal',device_authorization_expanded=False)
new['current_manual_goal_continuation']=dict(user_request='User resumed goal active; continue persistent objective',receipt=REL+'/native-goal-observed.json',classification='progress',native_status_remains='active',native_goal_resumed_by_user=True,fresh_blocked_audit=True,same_blocker_no_progress_count=0,meaningful_safe_offline_work_remains=True,assistant_resumed_native_goal=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('216取得24份新固定来源、完整树152/919/5和23行证据；Pico独立入口/SD候选未验/QEMU显示未完分开。核出分区相对写/绝对读换算、同reference零写、64KiB向下取整漏尾。FX3两原镜像847inode扫描、5文件原件复核，bootin4范围/16指令字证明局部ASCII3解析无强制LF，不套ZVE10修复字节、不充整机运行证明。无Sony/上游/guest/root/设备动作；用户恢复active已核，16要求、195待答和0.5不变。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',proof=REL+'/portability-proof.json',decisions=REL+'/adaptation-decisions.json',source_capture=REL+'/source-capture.json',source_followup=REL+'/source-followup-capture.json',FX3_locators=REL+'/FX3-boot-mode-locators.json',scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',upstream_or_Sony_or_guest_execution=False,root_or_device_operations=0)
new['latest_stage_evidence']['stage216_new_community_recovery_and_FX3_mode_parser']=ev
new['recovery_new_community_portability']={**ev,'selected_public_models':'ZV-E10 ARMv7 vs FX3 ARM64','reviewed_independent_route_requires_Pico':True,
 'pure_PC_USB_route_proven':False,'community_SD_route_physical_bad_camera_recovery_verified':False,
 'selected_FX3_mode_parser_has_mandatory_newline_for_ASCII3':False,'full_single_byte_mode_boot_health_verified':False,
 'partition_relative_write_vs_absolute_LBA_read_contract_required':True,'zero_writes_not_restore_proof':True,
 'full_readback_must_cover_positive_exact_length_and_tail':True,'healthy_same_body_source_and_cold_boot_still_required':True,
 'existing0_5_candidate_and_release_unchanged':True,'new_camera_operations':0,'independent_FX3_rescue_or_flash_readiness_proven':False}
new['next_safe_offline_actions']=[
 '195仅主机root01原具体问题待答；不从目标active/继续推导批准，不启动或重问，不扩大相机权限。',
 '继续FX3专用最小ET_DYN动态模块格式和受限子进程入口；先离线构建和装载合同核查，不把0.5静态ET_EXEC当LD_PRELOAD库，不生成或执行持久preload安装命令，不读取源分区。可信owner/root身份与跨进程退出仍未实测。',
 '后续恢复器必须显式绑定数据视图、分区内字节与绝对LBA基准、健康同机原件、正长度和完整尾部；同reference零写或采样0不符不能充恢复。FX3局部模式解析与ZVE10不同，保留同机原字节，不照抄LF/单字节修复。',
 '保留同机boot0/p1/完整配置、独立AP入口、逆写/冷启动/故障恢复及16要求和真实MAIN1080p29.97 HEVC长录；当前新参考须Pico，用户无额外硬件，不能以QEMU或源码检查冒充实机。']
for k in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[k]==old[k],k
for k in old['latest_stage_evidence']:assert new['latest_stage_evidence'][k]==old['latest_stage_evidence'][k]
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib)
marker='## 相机与固件研究\n';entry='- [2026-10-29 FX3新公开救砖方案与模式解析差异](<'+REL+'/README.md>)：24来源/23行、FX3两镜像847inode和4范围/16原字核对；Pico独立路线与SD待测分开，FX3局部解析无强制LF，不能抄修复字节。补相对写/绝对读、零写及漏尾约束；目标已由用户恢复active，0.5/16要求/195待答保留，无设备/root动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').open('xb').write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
 assert dest.read_bytes()==expected;p=H/name
 with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
 os.replace(p,dest)
members=[]
for p in sorted(H.rglob('*')):
 s=p.lstat()
 if stat.S_ISDIR(s.st_mode):continue
 assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 members.append(dict(path=str(p.relative_to(R)),bytes=s.st_size,sha256=sha(p)))
put('final-receipt.json',dict(schema='fx3-stage216-new-community-portability-v1',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=3959,
 files=members,member_count=len(members),goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),mutable_heads_not_manifest_members=True,
 public_fixed_sources=24,source_lines=23,original_ranges=4,original_word_checks=16,original_files_reextracted=5,
 no_upstream_or_Sony_or_guest_execution=True,new_root_or_camera_or_USB_operations=0,root01_bundle_sha256_unchanged=HOST,
 native_goal_observed='active',native_goal_resumed_by_user=True,native_goal_status_changed_by_assistant=False,new_approval_granted=False,
 goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=sha(H/'final-receipt.json'),members=len(members),sources=24,source_lines=23,original_ranges=4,raw_checks=16,
 requirements_unchanged=16,native_goal_status='active',new_camera_operations=0,goal_complete=False,persistent_write_release=False)))
