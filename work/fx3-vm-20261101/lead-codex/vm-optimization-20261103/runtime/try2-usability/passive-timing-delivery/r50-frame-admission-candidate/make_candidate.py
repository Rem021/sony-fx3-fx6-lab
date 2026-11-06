#!/usr/bin/env python3
"""Build obs_v2 candidate from the actual r47 PAGE; no integration/runtime."""
import difflib,hashlib,importlib.util,json
from pathlib import Path
DEL=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery')
R=Path(__file__).resolve().parent; R47=DEL/'r47-runtime-integration-candidate'; C=R/'candidate'; C.mkdir(parents=True,exist_ok=True)
def h(s):return hashlib.sha256(s.encode() if isinstance(s,str) else s).hexdigest()
def replace_once(s,old,new):
 assert s.count(old)==1,(s.count(old),old[:80])
 return s.replace(old,new,1)
spec=importlib.util.spec_from_file_location('r24_review_snapshot',R47/'trial_web_r24_review_snapshot.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
FULL=m.PAGE; BASE=FULL.split('<script>')[1].split('</script>')[0]
assert h(FULL)=='551cbd919f61858ba8542a3a46d7eab3894162c915038d92d5a16317bc3c719b'
assert h(BASE)=='f9a4287834015ab1f82dc0e9719437b755d7643b5f96f4cc9548199f06725caf'
assert (R47/'receipts/final-canonical-script.txt').read_text()==BASE
OBS_FUNCTION=r'''
function recordFrameAdmission(a,preflight,clickState,preflightStartMs,preflightEndMs){
 try{
  const preflightFrame=preflight&&preflight.frame;
  const lastFrame=lastStatus&&lastStatus.frame;
  const preflightLoaded=!!preflightFrame&&displayed>0&&shownSHA===preflightFrame.PNG_sha256&&displayedGeneration===preflightFrame.content_generation&&preflight.render_valid&&!renderFault;
  const lastLoaded=!!lastFrame&&displayed>0&&shownSHA===lastFrame.PNG_sha256&&displayedGeneration===lastFrame.content_generation&&lastStatus.render_valid&&!renderFault;
  const terms=[
   ['ending',!!ending],['finished',!!finished],['delivery_unknown',!!deliveryUnknown],['review_unknown',!!reviewUnknown],
   ['render_fault',!!renderFault],['awaiting_step',awaitingStep!==null],['review_awaiting',!!reviewAwaiting],
   ['preflight_phase_not_ready',!preflight||preflight.phase!=='ready'],['preflight_not_ready',!preflight||!preflight.ready],
   ['preflight_busy',!preflight||!!preflight.busy],['preflight_review_required',!preflight||!!preflight.review_required],
   ['preflight_steps_changed',!preflight||preflight.steps!==a.base_step],['not_frame_loaded_for_preflight',!preflightLoaded],
   ['preflight_sha_ne_clicked',!preflightFrame||preflightFrame.PNG_sha256!==a.frame.PNG_sha256],
   ['preflight_generation_ne_clicked',!preflightFrame||preflightFrame.content_generation!==a.frame.content_generation],
   ['shown_sha_ne_clicked',shownSHA!==a.frame.PNG_sha256],['displayed_generation_ne_clicked',displayedGeneration!==a.frame.content_generation],
   ['last_status_missing',!lastStatus],['not_frame_loaded_for_last_status',!lastLoaded],
   ['last_status_steps_changed',!lastStatus||lastStatus.steps!==a.base_step],
   ['last_status_sha_ne_clicked',!lastFrame||lastFrame.PNG_sha256!==a.frame.PNG_sha256],
   ['last_status_generation_ne_clicked',!lastFrame||lastFrame.content_generation!==a.frame.content_generation]
  ];
  let first=-1;for(let i=0;i<terms.length;i++){if(terms[i][1]){first=i;break;}}
  const evaluated=terms.slice(0,first<0?terms.length:first+1).map(x=>x[0]);
  const rec={schema:'fx3-frame-admission-obs-v2',version:1,attempt_id:a.attempt_id,
   clicked:{PNG_sha256:a.frame.PNG_sha256,content_generation:a.frame.content_generation,sequence:a.frame.sequence,monotonic_ms:a.created_monotonic_ms},
   displayed_at_click:clickState.displayed,last_status_at_click:clickState.lastStatus,
   preflight:{PNG_sha256:preflightFrame?preflightFrame.PNG_sha256:null,content_generation:preflightFrame?preflightFrame.content_generation:null,sequence:preflightFrame?preflightFrame.sequence:null,
    request_start_ms:preflightStartMs,request_end_ms:preflightEndMs,response_ms:preflightEndMs==null?null:preflightEndMs-preflightStartMs},
   displayed_at_decision:{sequence:displayed,PNG_sha256:shownSHA,content_generation:displayedGeneration,monotonic_ms:displayedAtMs},
   last_status_at_decision:lastStatus?{steps:lastStatus.steps,phase:lastStatus.phase,ready:lastStatus.ready,busy:lastStatus.busy,review_required:lastStatus.review_required,
    frame:lastFrame?{sequence:lastFrame.sequence,PNG_sha256:lastFrame.PNG_sha256,content_generation:lastFrame.content_generation}:null,monotonic_ms:lastStatusAtMs}:null,
   predicates:Object.fromEntries(terms),condition_order:terms.map(x=>x[0]),evaluated_terms:evaluated,
   first_true_term:first<0?null:terms[first][0],first_true_index:first,
   reason:'preflight_identity_or_lifecycle_changed',sequence_in_gate:false,
   sequence_observed:{clicked:a.frame.sequence,displayed_at_click:clickState.displayed.sequence,preflight:preflightFrame?preflightFrame.sequence:null,displayed_at_decision:displayed,last_status_at_decision:lastFrame?lastFrame.sequence:null},
   monotonic_ms:{click:a.created_monotonic_ms,last_status_at_click:clickState.lastStatusAtMs,displayed_at_click:clickState.displayedAtMs,
    preflight_start:preflightStartMs,preflight_end:preflightEndMs,last_status_at_decision:lastStatusAtMs,displayed_at_decision:displayedAtMs,decision:performance.now()},
   network:'no additional request; preflight status request is the original one',key_semantics:'unchanged; reason string unchanged'};
  const box=window.__fx3FrameAdmissionObsV2||(window.__fx3FrameAdmissionObsV2={schema:'fx3-frame-admission-obs-v2',version:1,records:[],last:null});
  box.records.push(rec);if(box.records.length>8)box.records.shift();box.last=rec;
 }catch(_){}
}
'''
# 1) timestamp state
CJS=replace_once(BASE,"let displayed=0,shown=0,shownSHA='',displayedGeneration=0,busy=false,ending=false,finished=false;",
 "let displayed=0,shown=0,shownSHA='',displayedGeneration=0,busy=false,ending=false,finished=false;\nlet lastStatusAtMs=0,displayedAtMs=0;")
# 2) showFrame timestamp
CJS=replace_once(CJS,"displayed=shown=seq;shownSHA=sha;displayedGeneration=generation;",
 "displayed=shown=seq;shownSHA=sha;displayedGeneration=generation;displayedAtMs=performance.now();")
# 3) tick timestamp
CJS=replace_once(CJS,"const s=(await request('/api/status')).body;if(reviewTerminated&&!['stopping','finished'].includes(s.phase)){disableKeys();return;}lastStatus=s;",
 "const s=(await request('/api/status')).body;if(reviewTerminated&&!['stopping','finished'].includes(s.phase)){disableKeys();return;}lastStatus=s;lastStatusAtMs=performance.now();")
# 4) click-time state capture
CJS=replace_once(CJS," const clickedStep=a.base_step,clickedSHA=a.frame.PNG_sha256,clickedGeneration=a.frame.content_generation;\n let preflight;",
 " const clickedStep=a.base_step,clickedSHA=a.frame.PNG_sha256,clickedGeneration=a.frame.content_generation;\n const clickState={lastStatusAtMs,displayedAtMs,displayed:{sequence:displayed,PNG_sha256:shownSHA,content_generation:displayedGeneration,monotonic_ms:displayedAtMs},\n  lastStatus:lastStatus?{steps:lastStatus.steps,phase:lastStatus.phase,ready:lastStatus.ready,busy:lastStatus.busy,review_required:lastStatus.review_required,\n   frame:lastStatus.frame?{sequence:lastStatus.frame.sequence,PNG_sha256:lastStatus.frame.PNG_sha256,content_generation:lastStatus.frame.content_generation}:null}:null};\n let preflight;let preflightStartMs=performance.now(),preflightEndMs=null;")
# 5) preflight end timestamp
CJS=replace_once(CJS," try{preflight=(await request('/api/status')).body;",
 " try{preflight=(await request('/api/status')).body;preflightEndMs=performance.now();")
# 6) insert recorder function before keys click wiring
CJS=replace_once(CJS,"keys.forEach(b=>b.onclick=async()=>{",OBS_FUNCTION+"\nkeys.forEach(b=>b.onclick=async()=>{")
# 7) record before the unchanged reason in combined rejection
CJS=replace_once(CJS,"   setAttempt(a.attempt_id,'not_posted',{reason:'preflight_identity_or_lifecycle_changed'});",
 "   recordFrameAdmission(a,preflight,clickState,preflightStartMs,preflightEndMs);\n   setAttempt(a.attempt_id,'not_posted',{reason:'preflight_identity_or_lifecycle_changed'});")
assert CJS.count('recordFrameAdmission(a,preflight')==2 # definition + call
TOKEN='r50-offline-token';SERVED=CJS.replace('__TOKEN__',json.dumps(TOKEN))
assert '__TOKEN__' not in SERVED
FULL_C=FULL.replace(BASE,CJS,1)
FULL_S=FULL_C.replace('__TOKEN__',json.dumps(TOKEN))
(C/'PAGE-script-obs-v2.canonical.js').write_text(CJS)
(C/'PAGE-script-obs-v2.served.js').write_text(SERVED)
(C/'PAGE-full-obs-v2.canonical.html').write_text(FULL_C)
(C/'PAGE-full-obs-v2.served.html').write_text(FULL_S)
diff=''.join(difflib.unified_diff(BASE.splitlines(True),CJS.splitlines(True),fromfile='a/PAGE-script.txt',tofile='b/PAGE-script-obs-v2.txt'))
(C/'DIFF-obs-v2.patch').write_text(diff)
ident={'schema':'fx3-r50-page-identity-candidate-v1','baseline_full_PAGE_sha256':h(FULL),'candidate_full_PAGE_sha256':h(FULL_C),
 'baseline_canonical_script_sha256':h(BASE),'candidate_canonical_script_sha256':h(CJS),
 'baseline_served_script_sha256':h(BASE.replace('__TOKEN__',json.dumps(TOKEN))),'candidate_served_script_sha256':h(SERVED),
 'token_used_for_served_replay':TOKEN,'diff_path':'candidate/DIFF-obs-v2.patch','diff_sha256':h(diff),
 'changed_script_lines':len(diff.splitlines()),'not_integrated':True,'actual_page_source':str(R47/'receipts/final-canonical-script.txt'),
 'future_integration':'patch base PAGE source/assembly and re-bind canonical/full PAGE hashes; no r47 source/runner changed here',
 'observation_schema':'fx3-frame-admission-obs-v2','records_cap':8}
(C/'PAGE-IDENTITY-CANDIDATE.json').write_text(json.dumps(ident,indent=2)+'\n')
build={'schema':'fx3-r50-candidate-build-v1','baseline':ident['baseline_canonical_script_sha256'],'candidate':ident['candidate_canonical_script_sha256'],
 'full_baseline':ident['baseline_full_PAGE_sha256'],'full_candidate':ident['candidate_full_PAGE_sha256'],'served_candidate':ident['candidate_served_script_sha256'],
 'diff_sha256':ident['diff_sha256'],'changed_lines':ident['changed_script_lines'],'anchors_all_once':True,'not_integrated':True}
(R/'receipts/candidate-build.json').write_text(json.dumps(build,indent=2)+'\n')
print(json.dumps(ident,indent=2))
