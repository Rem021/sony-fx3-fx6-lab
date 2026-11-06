#!/usr/bin/env python3
"""Explicit ONE step capture or operator-approved confirmation. No automatic keys/confirm."""
import argparse,datetime,hashlib,json,subprocess,time
from pathlib import Path
from capture_validation import validate_capture
H=Path(__file__).resolve().parent
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def br(c,args,code=None,timeout=15):
    p=subprocess.run(['agent-browser','--session',c['session'],*args],input=code,capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout
def command(argv,timeout=20):
    p=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['capture','confirm']);p.add_argument('step',type=int);p.add_argument('--target');a=p.parse_args()
    c=json.loads((H/'OPERATOR-CONFIG.json').read_text());D=Path(c['DEL']);n=a.step
    assert 1<=n<=8
    row=c['steps'][n-1];directory=H/('operator-step-%02d'%n)
    if a.action=='confirm':
        assert a.target
        cap=json.loads((directory/'validated-image-return.json').read_text())
        assert cap['validated_new_screenshot'] and cap['status']=='qualified_screenshot_for_operator_review'
        record={'UTC_enter':utc(),'host_monotonic_enter':time.monotonic(),'operator_target':a.target,'model_image_receive_UTC':None,'model_review_complete_UTC':None}
        path=directory/'manual-confirm-invocation.json'
        with path.open('x') as f:json.dump(record,f,ensure_ascii=False,indent=2)
        argv=['python3','-B',str(D/'v25-r18-frame-admission/operator-helpers/explicit_confirm_cli.py'),'--session',c['session'],'--url',c['url'],'--launch-id',c['launch_id'],'--nonce',row['nonce'],'--step',str(n),'--png-sha',cap['firmware_png_sha256'],'--target',a.target,'--receipt',str(directory/'explicit-confirm-receipt.json')]
        result=subprocess.run(argv,capture_output=True,text=True,timeout=20)
        record.update(argv=argv,UTC_return=utc(),host_monotonic_return=time.monotonic(),exit_code=result.returncode,stderr=result.stderr)
        path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
        print(result.stdout,flush=True);return result.returncode
    directory.mkdir() # Exclusive; a second call cannot arm or send the same key again.
    timeline=[]
    def stamp(stage):
        timeline.append({'stage':stage,'UTC':utc(),'host_monotonic':time.monotonic()});(directory/'timeline.json').write_text(json.dumps(timeline,indent=2)+'\n')
    stamp('capture_tool_command_enter')
    # Require previous operator confirmation/cancel proof before another actual key.
    if n>1:
        prev=json.loads((H/('operator-step-%02d'%(n-1))/'explicit-confirm-receipt.json').read_text())
        assert prev['status']=='confirmed_and_cancelled'
    stamp('arm_enter')
    arm=json.loads(command(['python3','-B',str(D/'v25-r18-frame-admission/operator-helpers/deadline_cli.py'),'arm','--session',c['session'],'--url',c['url'],'--launch-id',c['launch_id'],'--nonce',row['nonce']]))
    (directory/'arm.json').write_text(json.dumps(arm,indent=2)+'\n')
    assert arm['deadline_ms']==20000 and arm['current']['nonce']==row['nonce'] and arm['current']['state']=='armed'
    stamp('arm_return_verified');stamp('single_key_click_enter')
    (directory/'key-click.txt').write_text(br(c,['click','button[data-key="%d"]'%row['key']]))
    stamp('single_key_click_return')
    out=directory/'capture'
    if n==1:
        stamp('bounded_capture_CLI_enter')
        result=subprocess.run(['python3','-B',str(D/'v25-r18-frame-admission/operator-helpers/bounded_capture_cli.py'),'--session',c['session'],'--url',c['url'],'--launch-id',c['launch_id'],'--nonce',row['nonce'],'--evidence-dir',str(out)],capture_output=True,text=True,timeout=20)
        stamp('bounded_capture_CLI_return')
        (directory/'capture-process.json').write_text(json.dumps({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr},indent=2)+'\n')
        valid=validate_capture(result.returncode,result.stdout,out)
    else:
        out.mkdir()
        cfg={'url':c['url'],'launch_id':c['launch_id'],'nonce':row['nonce'],'step':n}
        stamp('review_and_current_loaded_wait_enter')
        raw=br(c,['eval','--stdin'],(H/'capture_review.js').read_text()+'('+json.dumps(cfg)+')',timeout=12)
        stamp('review_and_current_loaded_wait_return')
        before=json.loads(raw);(out/'before.json').write_text(json.dumps(before,indent=2)+'\n')
        if before.get('status')!='ready_for_screenshot':raise RuntimeError('read_only_capture_refused:'+json.dumps(before))
        stamp('screenshot_enter')
        shot=out/'menu-reference-page.png';br(c,['screenshot',str(shot)])
        stamp('screenshot_return')
        post={**cfg,'before':before['before']}
        after=json.loads(br(c,['eval','--stdin'],(H/'capture_after.js').read_text()+'('+json.dumps(post)+')'))
        (out/'after.json').write_text(json.dumps(after,indent=2)+'\n')
        if not after.get('qualified'):raise RuntimeError('post_capture_identity_or_margin_refused:'+json.dumps(after))
        receipt={'status':'qualified_screenshot_for_operator_review','screenshot_path':str(shot),'screenshot_file_sha256':hashlib.sha256(shot.read_bytes()).hexdigest(),'before_eval':before,'after_eval':after,'scope':'read_only_current_loaded_review; semantic target judged only by operator'}
        (out/'capture-result.json').write_text(json.dumps(receipt,indent=2)+'\n')
        valid=validate_capture(0,json.dumps(receipt),out)
    stamp('validated_image_return_preparation_boundary')
    (directory/'validated-image-return.json').write_text(json.dumps({**valid,'return_boundary':timeline[-1]},indent=2)+'\n')
    print(json.dumps(valid),flush=True);return 0
if __name__=='__main__':
    try:code=main()
    except Exception as e:
        print(json.dumps({'status':'operator_refused_or_unknown','error':str(e),'UTC':utc(),'host_monotonic':time.monotonic(),'validated_new_screenshot':False}),flush=True);code=2
    raise SystemExit(code)
