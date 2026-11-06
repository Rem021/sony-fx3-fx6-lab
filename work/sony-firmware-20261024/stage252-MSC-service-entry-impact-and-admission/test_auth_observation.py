"""Consume archived original counterexamples; no rerun of guest or camera."""
from pathlib import Path
from dataclasses import asdict
from hashlib import sha256
import json
import auth_observation as A

H=Path(__file__).resolve().parent;B=H.parent
p=B/'stage149-normal-cooperator-and-NIN-checkpoint/run-original-checkpoint/results.json'
data=p.read_bytes();archive=json.loads(data);rows=[]
for case in archive['cases']:
    out=A.classify_observed_codes(case['public_response_codes'],case['final_reply_first_byte'])
    assert out.protocol_state=='EXCHANGE_FINISHED_AUTHENTICATION_UNVERIFIED'
    assert not any((out.authentication_verified,out.mode_transition_verified,out.camera_thread_exit_verified,out.persistent_effects_excluded,out.live_operation_authorized))
    rows.append(dict(digest_style=case['digest_style'],pattern=case['pattern'],native_comparisons=case['native_comparisons'],observation=asdict(out),archived_CPU_fixture_only=True))
assert any(not any(x['native_comparisons'])for x in rows) and any(all(x['native_comparisons'])for x in rows)
assert len({x['observation']['protocol_state']for x in rows})==1
def frame(code,data=b''):
    return ((~code)&0xffff).to_bytes(2,'big')+b'\0\0'+data.ljust(512,b'\0')
good=[frame(x,b'\1'if x==6 else b'')for x in [8,4,8,4,8,4,6]]
assert A.classify_frames(good).protocol_state=='EXCHANGE_FINISHED_AUTHENTICATION_UNVERIFIED'
assert A.classify_frames(good[:1]).protocol_state=='CHALLENGE_OBSERVED'
assert A.classify_frames([]).protocol_state=='NO_PROTOCOL_REPLY'
invalid=[[b'\0'*515],[b'\0'*517],[frame(8),frame(2)],good+[frame(6,b'\1')],good[:-1]+[frame(6)], [frame(5)]]
for frames in invalid:
    try:A.classify_frames(frames)
    except A.InvalidTranscript:pass
    else:raise AssertionError('bad transcript accepted')
result=dict(status='PASS_ARCHIVED_COUNTEREXAMPLE_CLASSIFICATION',archived_cases=len(rows),rows=rows,
 original_archive_sha256=sha256(data).hexdigest(),synthetic_frame_format_cases=3,malformed_transcript_rejections=len(invalid),
 old_original_guest_tests_repeated=False,original_or_downloaded_code_executed=False,USB_cache_admin_or_camera_operations=0,authentication_acceptance_not_inferred=True)
with(H/'auth-observation-test-receipt.json').open('x')as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status=result['status'],archived_cases=len(rows),malformed_rejections=len(invalid),new_guest_or_live_operations=0)))
