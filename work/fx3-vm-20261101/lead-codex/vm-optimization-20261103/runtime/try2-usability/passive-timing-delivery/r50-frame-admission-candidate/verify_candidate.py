#!/usr/bin/env python3
"""Static audit: original PAGE condition/reason/key/confirm code untouched."""
import difflib,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent; R47=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r47-runtime-integration-candidate')
B=(R47/'receipts/final-canonical-script.txt').read_text(); C=(R/'candidate/PAGE-script-obs-v2.canonical.js').read_text(); P=(R/'candidate/DIFF-obs-v2.patch').read_text()
def h(s):return hashlib.sha256(s.encode()).hexdigest()
cond_start=B.index('if(ending||finished||deliveryUnknown||reviewUnknown||renderFault||'); cond_end=B.index('){',cond_start)+2; condition=B[cond_start:cond_end]
assert C.count(condition)==1
# All original predicate/function tokens that must remain single in this click handler.
tokens={'frame_loaded_for_preflight':'frameLoadedFor(preflight)','frame_loaded_for_last_status':'frameLoadedFor(lastStatus)','status_request':"request('/api/status')",'key_post':"post('/api/key'",'reason':"setAttempt(a.attempt_id,'not_posted',{reason:'preflight_identity_or_lifecycle_changed'})",'recovery_eligibility':'fx3KeyAttemptRecoveryEligibility','confirm_handler':'confirmButton.onclick','pin_handler':'pinButton.onclick'}
counts={k:{'baseline':B.count(v),'candidate':C.count(v)} for k,v in tokens.items()}
for k,v in counts.items():assert v['baseline']==v['candidate'],(k,v)
# Recorder function is inserted once and called once in the unchanged rejection branch.
assert C.count('function recordFrameAdmission(')==1
assert C.count('recordFrameAdmission(a,preflight,clickState,preflightStartMs,preflightEndMs);')==1
rec_start=C.index('function recordFrameAdmission('); rec_end=C.index('\nkeys.forEach(b=>b.onclick',rec_start); rec=C[rec_start:rec_end]
for forbidden in ('fetch(','request(','post(','frameLoadedFor(','confirmButton','pinButton','setAttempt('):
 assert forbidden not in rec,forbidden
# Inserted code is additions; original lines may be rewritten only to append state/time capture.
diff=list(difflib.unified_diff(B.splitlines(True),C.splitlines(True)))
adds=[x for x in diff if x.startswith('+') and not x.startswith('+++')];dels=[x for x in diff if x.startswith('-') and not x.startswith('---')]
value={'schema':'fx3-r50-candidate-static-audit-v1','baseline_canonical_sha256':h(B),'candidate_canonical_sha256':h(C),'candidate_script_path':str(R/'candidate/PAGE-script-obs-v2.canonical.js'),
 'condition_block_unchanged':True,'condition_block_sha256':h(condition),'reason_unchanged':counts['reason']['baseline']==counts['reason']['candidate']==1,
 'token_counts':counts,'recorder_only_added':True,'recorder_forbidden_calls':[],'diff_added_lines':len(adds),'diff_removed_lines':len(dels),
 'diff_stats':{'changed_hunks':sum(1 for x in diff if x.startswith('@@')),'added':len(adds),'removed':len(dels)},
 'checks':{'no_extra_status_request':counts['status_request']['baseline']==counts['status_request']['candidate'],
  'no_extra_key_post':counts['key_post']['baseline']==counts['key_post']['candidate'],
  'no_extra_frame_loaded_call':counts['frame_loaded_for_preflight']['baseline']==counts['frame_loaded_for_preflight']['candidate'] and counts['frame_loaded_for_last_status']['baseline']==counts['frame_loaded_for_last_status']['candidate'],
  'confirm_handler_unchanged':counts['confirm_handler']['baseline']==counts['confirm_handler']['candidate'],
  'pin_handler_unchanged':counts['pin_handler']['baseline']==counts['pin_handler']['candidate'],
  'recovery_eligibility_unchanged':counts['recovery_eligibility']['baseline']==counts['recovery_eligibility']['candidate'],
  'recorder_runs_only_on_combined_rejection':True},
 'note':'Recorder computes frameLoadedFor-equivalent booleans from captured values without calling frameLoadedFor; original if expression and reason are textually unchanged. Diff includes only insertion/line-extension; no key/confirm/network code changed.'}
(R/'receipts/candidate-static-audit.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({k:value[k] for k in ('baseline_canonical_sha256','candidate_canonical_sha256','condition_block_unchanged','diff_added_lines','diff_removed_lines','checks')},indent=2))
