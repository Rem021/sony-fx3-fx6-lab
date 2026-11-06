#!/usr/bin/env python3
"""Review captured public demonstration evidence; preserve all live-device gates."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import copy
import importlib.util
import json
import os
import re

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
REL = HERE.relative_to(ROOT).as_posix()
PRIOR = BASE / 'stage149-normal-cooperator-and-NIN-checkpoint'
PRIOR_SHA = '889e9553cdc213579b7f1a0575d10d1de73dcde0bbc19704aaa9b2bc2ba24c6d'
HELPER = BASE / 'stage133-FX5-source-availability-and-portability'


def put(name, value):
    with (HERE / name).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def main():
    assert not (HERE / 'final-receipt.json').exists()
    helper_raw = (HELPER / 'final-receipt.json').read_bytes()
    assert sha256(helper_raw).hexdigest() == '564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    member = next(m for m in json.loads(helper_raw)['files'] if m['path'] == (HELPER / 'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER / 'review_and_seal.py').read_bytes()).hexdigest() == member['sha256']
    spec = importlib.util.spec_from_file_location('fixed_public_evidence_sealer', HELPER / 'review_and_seal.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.HERE, helper.REL, helper.PRIOR, helper.PRIOR_SHA = HERE, REL, PRIOR, PRIOR_SHA
    helper.volume()
    count = helper.check_previous()
    assert count == 17
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    index_snapshot = HERE / 'readme-rebased-before.md'
    before, index_before = (HERE / 'goal-status-before.json').read_bytes(), index_snapshot.read_bytes()
    rebase = json.loads((HERE / 'index-rebase-review.json').read_text())
    assert sha256(index_before).hexdigest() == rebase['rebased_before_sha256']
    assert sha256((HERE / 'readme-before.md').read_bytes()).hexdigest() == rebase['original_before_sha256']
    assert canonical.read_bytes() == before == (PRIOR / 'goal-status-after.json').read_bytes()
    assert index.read_bytes() == index_before
    old = json.loads(before)
    fixed = helper.pins(old)
    assert len(old['requirements']) == 16 and not old['goal_complete'] and not old['persistent_write_release']
    assert not old['authorization']['Mac_active_USB_descriptor_read_authorized']
    assert old['authorization']['Mac_descriptor_probe_authorization_consumed']
    assert not old['authorization']['service_auth_mode_or_stop'] and not old['authorization']['driver_change']
    assert not old['prepared_first_device_trial']['Mac_descriptor_probe_released']
    public = HERE / 'work/public-sources'
    reviewed = []
    for label, expected_count in [('camera-tools', 141), ('service-preload', 5)]:
        capture = json.loads((public / label / 'source-capture.json').read_text())
        assert len(capture['text_files']) == expected_count
        assert not capture['downloaded_code_executed'] and capture['camera_or_USB_operations'] == 0
        for m in capture['text_files']:
            path = public / label / m['path']
            assert path.stat().st_size == m['bytes'] and helper.digest(path) == m['sha256']
        reviewed.append({'repo': capture['repo'], 'commit': capture['commit'], 'selected_text_files': expected_count})
    expression = re.compile(r'h[._-]?265|hevc|xavc.?hs|opengate', re.I)
    capture = json.loads((public / 'camera-tools/source-capture.json').read_text())
    hits = [m['path'] for m in capture['text_files'] if expression.search((public / 'camera-tools' / m['path']).read_text(errors='replace'))]
    assert hits == []
    readmes = json.loads((public / 'fl23/readme-capture.json').read_text())
    assert len(readmes['files']) == 2 and not readmes['downloaded_code_executed']
    for m in readmes['files']:
        path = public / 'fl23' / m['path']
        assert path.stat().st_size == m['bytes'] and helper.digest(path) == m['sha256']
    limit = json.loads((public / 'fl23/archive-limit.json').read_text())
    assert limit['status'] == 'ARCHIVE_DOWNLOAD_LIMIT_EXCEEDED_NOT_EXTRACTED'
    posts = [json.loads((HERE / 'work' / name).read_text()) for name in ['x-post-syndication.json', 'x-followup-syndication.json']]
    assert posts[0]['id_str'] == '2113872045637279779' and '25/30' in posts[0]['text']
    assert posts[1]['id_str'] == '2114013688042524892' and '420还没测试' in posts[1]['text']
    assert all(p['user']['screen_name'] == 'liulingyue' and p['created_at'].startswith('2026-10-24') for p in posts)
    embeds = [json.loads((HERE / 'work' / name).read_text()) for name in ['twitter-oembed.json', 'twitter-oembed-followup.json']]
    assert all(e['author_url'] == 'https://x.com/liulingyue' and 'October 24, 2026' in e['html'] for e in embeds)
    media = json.loads((HERE / 'demo-media-capture.json').read_text())
    assert len(media['files']) == 6 and not media['camera_generated_MP4_obtained']
    for m in media['files']:
        path = HERE / 'work' / m['path']
        assert path.stat().st_size == m['bytes'] and helper.digest(path) == m['sha256']
        assert m['url'].startswith('https://pbs.twimg.com/media/') and m['posted_media_type'] == 'photo'
    user = json.loads((HERE / 'user-image-source.json').read_text())
    assert helper.digest(Path(user['source_path'])) == user['source_sha256']
    assert (ROOT / user['decoded_preview']).is_file()
    now = datetime.now(timezone.utc).isoformat()
    put('evidence-review.json', {
        'created_utc': now, 'classification': 'AUTHOR_PROVIDED_CAMERA_AND_PLAYER_IMAGES_NOT_INDEPENDENT_MP4_VALIDATION',
        'primary_X_oembed_and_syndication_agree_on_author_text_and_date': True,
        'primary_post_ids': [p['id_str'] for p in posts], 'downloaded_original_posted_photos': 6,
        'manual_image_observations': {
            'photo1_camera_playback': {'format_label': 'XAVC HS 4K', 'fps_label': '25p', 'rate_label': '140M', 'chroma_bit_depth_label': '4:2:2 10bit', 'clip': 'C0010'},
            'photo2_player_information': {'codec_label': 'HVC1 / FFmpeg hevc', 'width': 3840, 'height': 2160, 'source_fps_label': '25', 'video_kbps_label': 138147},
            'photo3_camera_playback': {'format_label': 'XAVC HS 4K', 'fps_label': '30p', 'rate_label': '140M', 'chroma_bit_depth_label': '4:2:2 10bit', 'clip': 'C0009'},
            'photo4_player_information': {'codec_label': 'HVC1 / FFmpeg hevc', 'width': 3840, 'height': 2160, 'source_fps_label': '29.97', 'video_kbps_label': 133635},
            'both_player_screenshots_audio': {'codec_label': 'twos PCM', 'sample_rate_label': 48000, 'channels_label': 2, 'bits_label': 16},
            'followup_menu': {'format_label': 'XAVC HS 4K30p', 'rate_option_labels': ['140M', '70M', '42M'], 'chroma_bit_depth_labels': '4:2:2 10bit'}},
        'player_NV12_output_not_original_HEVC_chroma_or_bit_depth_proof': True,
        'author_reports_420_untested': True, 'all_three_menu_bitrates_recording_verified': False,
        'exact_fps_fraction_original_SPS_or_timestamps_independently_parsed': False,
        'raw_camera_MP4_obtained_or_decoded_here': False,
        'Douyin_and_X_author_identity_link_proven': False,
        'reviewed_pinned_source_text': reviewed, 'camera_tools_selected_text_keyword_hits': hits,
        'FL23_review_scope': 'Only two pinned README files; archive limit exceeded and whole repository not scanned',
        'HEVC_specific_patch_source_or_firmware_version_obtained_from_demo': False,
        'FX3_HD_420_16M_or_safety_portability_proven': False,
        'new_device_Windows_UU_operations': 0, 'downloaded_code_executed': False,
        'same_agent_local_review_only': True})
    wip = BASE / 'stage150-normal-resource-and-thread-transition'
    put('preserved-stage150-work.json', {'scope': 'Preserved unsealed work only; no new guest experiment or hardware acceptance adopted',
        'unsealed': not (wip / 'final-receipt.json').exists(), 'files': [helper.record(p) for p in sorted(wip.rglob('*')) if p.is_file()]})
    new = copy.deepcopy(old)
    new['updated_utc'] = now
    new['latest_stage'] = HERE.name
    new['research_activity'] = 'Latest A7C II HEVC 25/29.97 original author and six camera/player/menu photos verified; no original MP4 or FX3 patch acquired'
    new['progress_audit']['previous_goal_turn_classification'] = 'progress'
    new['progress_audit']['classification'] = 'progress'
    new['progress_audit']['basis'].extend([
        '阶段151按用户新线索核实10月24日一手A7CII HEVC演示；X官方oEmbed与syndication交叉确认作者、日期、正文，六张原帖图片留存哈希。',
        '两组机内回放及电脑播放器信息显示4K25和29.97、HVC1/hevc；不是本轮原始MP4独立解析。422/10bit来自机内标示，播放器NV12不充原始码流格式。作者称420未测；HD、约16M与FX3仍未证明。',
        '固定camera-tools与service-preload提交共146文本；FL23全仓超32MiB有界停止，只读两份固定README。不把FL23工具认作未取得的H265补丁，未执行其脚本/驱动/模块。',
        '150资源线程离线工作原样保留但未封存、不冒充新实验。原16要求及所有设备权限、原型哈希不变，无新增USB/Windows/UU操作。'])
    new['latest_stage_evidence']['stage151_A7CII_HEVC_original_public_demo'] = {
        'readme': REL + '/README.md', 'review': REL + '/evidence-review.json', 'media_receipt': REL + '/demo-media-capture.json',
        'primary_post': 'https://x.com/liulingyue/status/2113872045637279779',
        'primary_followup': 'https://x.com/liulingyue/status/2114013688042524892',
        'photos': 6, 'author_player_screenshots_show_HEVC_4K25_and_29_97': True,
        'independently_parsed_original_MP4': False, 'HEVC_specific_patch_obtained': False,
        'FX3_HD_or_recovery_acceptance': False, 'new_device_operations': 0}
    new['prepared_first_device_trial']['A7CII_HEVC_author_demo_review'] = REL + '/evidence-review.json'
    new['next_safe_offline_actions'].append('优先追A7CII 4K25/29.97 HEVC演示的实际补丁、源固件与原片；对照FX3原7.02格式映射/编码参数/菜单联动。不套用A7CII包或偏移，不把422的4K140M外推成FX3 HD42016M。原片核查codec/SPS/帧率分数/PTS/DTS/音轨后再论实机；备份恢复与独立救援不省略。')
    allowed = {'updated_utc', 'latest_stage', 'research_activity', 'progress_audit', 'latest_stage_evidence', 'prepared_first_device_trial', 'next_safe_offline_actions'}
    for key in old:
        if key not in allowed:
            assert new[key] == old[key], key
    for section in ('prepared_first_device_trial', 'latest_stage_evidence'):
        for key, value in old[section].items():
            assert new[section][key] == value
    encoded = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    (HERE / 'goal-status-after.json').write_bytes(encoded)
    marker = '## 相机与固件研究\n'
    entry = '- [2026-10-27 A7C II HEVC 25／29.97最新演示核查](<' + REL + '/README.md>)：一手原帖及六张机内/播放器/菜单图，4K HEVC有作者实机证据；420、HD、原片独立解析及FX3可刷补丁仍待证，无新增设备操作。'
    text = index_before.decode()
    assert text.count(marker) == 1 and entry not in text
    index_after = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
    (HERE / 'readme-after.md').write_bytes(index_after)
    helper.volume()
    assert canonical.read_bytes() == before and index.read_bytes() == index_before, 'Concurrent head change; CAS refused'
    assert helper.pins(old) == fixed
    for target, data, name in [(canonical, encoded, '.goal-final.tmp'), (index, index_after, '.index-final.tmp')]:
        temp = HERE / name
        with temp.open('xb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    assert canonical.read_bytes() == encoded and index.read_bytes() == index_after
    helper.check_previous()
    put('completed-evidence-review.json', {
        'status': 'PASS_PRIMARY_AUTHOR_DEMO_CAPTURE_NOT_ORIGINAL_MP4_OR_FX3_ACCEPTANCE', 'created_utc': now,
        'previous_manifest_members_verified': count, 'primary_photos_reviewed': 6, 'selected_public_source_text_files_verified': 148,
        'all16_requirements_authorization_user_constraints_and_old_prepared_values_preserved': True,
        'fixed_guest_backend_frontend_pins': fixed, 'goal_complete': False, 'persistent_write_release': False,
        'new_device_operations': 0, 'same_agent_local_review_only': True})
    files = [helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json', {
        'schema': 'fx3-stage151-latest-A7CII-HEVC-demo/1', 'created_utc': now, 'volume_uuid': helper.UUID,
        'files': files, 'member_count': len(files), 'previous_manifest_sha256': PRIOR_SHA,
        'allowed_goal_keys_changed': sorted(allowed), 'mutable_project_heads_not_manifest_members': True,
        'mutable_progress': {'before_sha256': sha256(before).hexdigest(), 'after_sha256': sha256(encoded).hexdigest(),
            'readme_before_sha256': sha256(index_before).hexdigest(), 'readme_after_sha256': sha256(index_after).hexdigest()}})
    print(json.dumps({'manifest_sha256': helper.digest(HERE / 'final-receipt.json'), 'members': len(files),
        'canonical_sha256': helper.digest(canonical), 'goal_complete': False, 'persistent_write_release': False}))


if __name__ == '__main__':
    main()
