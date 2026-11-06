(async function recoveryReadOnly(c){
 'use strict';
 const PAGE_SHA='852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b';
 const hash=async s=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)))].map(x=>x.toString(16).padStart(2,'0')).join('');
 const fail=reason=>({qualified:false,reason,performance_ms:performance.now()});
 if(!c||location.href!==c.url||window.top!==window||document.title!=='FX3 固件菜单试用')return fail('document_url');
 const scripts=[...document.scripts];if(scripts.length!==1||scripts[0].src)return fail('script_shape');
 const canonical=scripts[0].textContent.replace(/^const token=[^\r\n]*;$/m,'const token=__TOKEN__;');
 if(await hash(canonical)!==PAGE_SHA)return fail('PAGE_fingerprint');
 const a=window.fx3KeyAttemptOutcome?.(),h=window.__fx3InteractionDeadlineV1?.status?.(),s=lastStatus;
 if(!a||!h||!s||!c.binding||a.attempt_id!==c.binding.attempt_id||
    a.alarm_nonce!==c.nonce||h.current?.nonce!==c.nonce||h.current.state!=='armed'||
    h.expectedLaunchId!==c.launch_id||h.expectedURL!==c.url||h.documentTimeOrigin!==performance.timeOrigin||
    !Number.isFinite(h.current.due_ms)||performance.now()>=h.current.due_ms)return fail('attempt_alarm_identity');
 const eligibility=window.fx3KeyAttemptRecoveryEligibility?.(c.binding);
 if(!eligibility?.eligible)return fail('not_proven_unqueued_or_not_ready:'+eligibility?.reason);
 if(!s.frame||!frameLoadedFor(s)||!image.complete||image.naturalWidth<=0||
    s.frame.PNG_sha256!==shownSHA||s.frame.content_generation!==displayedGeneration)return fail('current_loaded_frame');
 return {qualified:true,attempt_id:a.attempt_id,nonce:c.nonce,launch_id:c.launch_id,
   document_time_origin:performance.timeOrigin,alarm_due_ms:h.current.due_ms,
   sequence:displayed,PNG_sha256:shownSHA,content_generation:displayedGeneration,
   performance_ms:performance.now(),server_atomic_permission:false};
})
