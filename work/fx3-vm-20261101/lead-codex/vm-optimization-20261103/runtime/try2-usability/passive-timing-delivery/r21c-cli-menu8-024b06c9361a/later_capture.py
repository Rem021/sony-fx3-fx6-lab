"""Read-only derived capture for steps 2-8, current r21 attempt binding."""
import sys
from common import *
def current_guard(c):
 return r'''(async()=>{const c=CONFIG,s=[...document.scripts];const d=async t=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(t)))].map(x=>x.toString(16).padStart(2,'0')).join('');const a=fx3KeyAttemptOutcome();if(s.length!==1||s[0].src||await d(s[0].textContent.replace(/^const token=[^\r\n]*;$/m,'const token=__TOKEN__;'))!=='f1eb5a54e36b8395a419fee107b87a22fae86dc7eb3c32debfbf6e783e930eab'||location.href!==c.url||lastStatus.launch_request_id!==c.launch_id||a?.attempt_id!==c.attempt_id||a.alarm_nonce!==c.nonce||a.expected_step!==c.step||a.outcome!=='accepted')throw Error('r21_current_attempt_identity');return a;})()'''.replace('CONFIG',json.dumps(c))
def main():
 c=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]);out.mkdir()
 ev(c['prefix']+'-identity-before',current_guard(c))
 before=ev(c['prefix']+'-capture-before',(HERE/'capture_review.js').read_text()+'('+json.dumps(c)+')');(out/'before.json').write_text(json.dumps(before,indent=2)+'\n')
 assert before.get('status')=='ready_for_screenshot',before
 shot=out/'menu-reference-page.png';browser(c['prefix']+'-screenshot',['screenshot',str(shot)],timeout=8)
 after=ev(c['prefix']+'-capture-after',(HERE/'capture_after.js').read_text()+'('+json.dumps({**c,'before':before['before']})+')');(out/'after.json').write_text(json.dumps(after,indent=2)+'\n')
 assert after.get('qualified'),after
 ev(c['prefix']+'-identity-after',current_guard(c))
 r={'status':'qualified_screenshot_for_operator_review','screenshot_path':str(shot),'screenshot_file_sha256':sha(shot),'before_eval':before,'after_eval':after,'attempt_id':c['attempt_id'],'scope':'read_only_current_loaded_review; semantic judgement by operator only'}
 (out/'capture-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
