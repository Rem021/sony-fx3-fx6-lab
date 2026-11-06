#!/usr/bin/env python3
"""One explicit operator-approved click of the original PAGE confirm button.

This tool never sends a guest key, arm, direct HTTP request, or retry.
"""
from __future__ import annotations
import argparse, json, re, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

HERE=Path(__file__).resolve().parent
UUID_RE=re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
SHA_RE=re.compile(r'[0-9a-f]{64}')
SESSION_RE=re.compile(r'fx3-deadline-[A-Za-z0-9_-]+')

def utc():return datetime.now(timezone.utc).isoformat()

def browser(session,args,source=None,timeout=15):
    p=subprocess.run(['agent-browser','--session',session,*args],input=source,
                     text=True,capture_output=True,timeout=timeout)
    if p.returncode:raise RuntimeError(f'agent-browser {args[0]} failed: {p.stdout} {p.stderr}')
    return p.stdout

def validate(session,url,launch_id,nonce,step,png_sha,target):
    if not SESSION_RE.fullmatch(session):raise ValueError('dedicated fx3-deadline-* session required')
    parsed=urlsplit(url)
    if (parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or not parsed.port or
        parsed.path!='/' or parsed.query or parsed.fragment or parsed.username or parsed.password or
        url!=f'http://127.0.0.1:{parsed.port}/'):
        raise ValueError('exact loopback URL with trailing slash required')
    if not UUID_RE.fullmatch(launch_id) or not UUID_RE.fullmatch(nonce):raise ValueError('launch id / alarm nonce UUID required')
    if type(step) is not int or not 1<=step<=4096:raise ValueError('actual review step 1..4096 required')
    if not SHA_RE.fullmatch(png_sha):raise ValueError('reviewed PNG SHA256 required')
    if not isinstance(target,str) or not target.strip() or len(target)>500:raise ValueError('nonempty bounded operator target description required')

def operate(session,url,launch_id,nonce,step,png_sha,target,receipt,*,source=None):
    """A call is one attempt. A tool failure after eval begins is delivery-unknown."""
    validate(session,url,launch_id,nonce,step,png_sha,target)
    receipt=Path(receipt)
    if not receipt.parent.is_dir():raise ValueError('existing receipt directory required')
    record={'status':'pending_preflight','session':session,'url':url,'launch_id':launch_id,
            'alarm_nonce':nonce,'step':step,'reviewed_png_sha256':png_sha,'target':target.strip(),
            'host_invoked_UTC':utc(),'host_monotonic_invoked':time.monotonic(),
            'eval_may_have_started':False,'retries':0,'guest_keys_sent_by_helper':0}
    # An interrupted process leaves a warning rather than a false no-click claim.
    with receipt.open('x') as out:out.write(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    try:
        tabs=json.loads(browser(session,['tab','--json']))['data']['tabs']
        if len(tabs)!=1 or tabs[0]['url']!=url:raise ValueError('exactly one owned tab at the exact URL required')
        record['tab_id']=tabs[0].get('id');record['host_preflight_UTC']=utc()
        config={'url':url,'launch_id':launch_id,'nonce':nonce,'step':step,
                'png_sha':png_sha,'target':target.strip()}
        script=(source if source is not None else (HERE/'explicit_confirm.js').read_text())
        record['eval_may_have_started']=True
        receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
        raw=browser(session,['eval','--stdin'],script+'('+json.dumps(config,ensure_ascii=False)+')',timeout=15)
        result=json.loads(raw)
        if not isinstance(result,dict) or result.get('status') not in ('confirmed_and_cancelled','refused','unknown'):
            raise ValueError('browser result shape unknown after eval')
        record['browser_result']=result;record['status']=result['status']
    except BaseException as exc:
        record['status']='unknown' if record['eval_may_have_started'] else 'refused'
        record['error']=repr(exc)
    record['host_return_UTC']=utc();record['host_monotonic_return']=time.monotonic()
    receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('session','url','launch-id','nonce','step','png-sha','target','receipt'):
        p.add_argument('--'+name,required=True,type=int if name=='step' else str)
    a=p.parse_args()
    r=operate(a.session,a.url,a.launch_id,a.nonce,a.step,a.png_sha,a.target,a.receipt)
    print(json.dumps(r,ensure_ascii=False,indent=2))
    raise SystemExit(0 if r['status']=='confirmed_and_cancelled' else 2)
