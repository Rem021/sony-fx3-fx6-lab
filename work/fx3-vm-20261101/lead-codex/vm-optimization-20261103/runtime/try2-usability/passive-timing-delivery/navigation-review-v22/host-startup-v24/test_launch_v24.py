import ast,fcntl,json,tempfile,urllib.request,urllib.error
from pathlib import Path
from trial_web_v22_navigation_review import TrialState,start_server

HERE=Path(__file__).resolve().parent
source=(HERE/'run_trial_v22_navigation_review.py').read_text()
tree=ast.parse(source)
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
body=source[source.index('with (run / \'host-stdout.log\')'):]
assert body.index('start_server(trial, ns.port)')<body.index('trial.launch_event.is_set()')<body.index('fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)')<body.index('subprocess.Popen(args')
assert "ap.error('v24 浏览器就绪门不允许内部逐键模式绕过')" in source

def endpoint(state,path,body):
    req=urllib.request.Request(state.url+path,json.dumps(body).encode(),{'Content-Type':'application/json','X-Trial-Token':state.token,'Origin':state.url})
    try:r=urllib.request.urlopen(req,timeout=2)
    except urllib.error.HTTPError as e:r=e
    with r:return r.status,json.loads(r.read())

checks=[]
s=TrialState('HOST_ONLY',30,4096);s.update(phase='awaiting_launch')
server,thread=start_server(s,0)
try:
    ident='a'*32+'-abc'
    assert endpoint(s,'/api/start',{'request_id':ident})[0]==409
    assert not s.launch_event.is_set()
    assert endpoint(s,'/api/browser-ready',{})==(200,{'browser_ready':True})
    assert endpoint(s,'/api/start',{'request_id':ident})[0]==202
    assert s.launch_event.is_set() and s.launch_request_id==ident
    assert endpoint(s,'/api/start',{'request_id':ident})[0]==200
    assert endpoint(s,'/api/start',{'request_id':'b'*32+'-abc'})[0]==409
    assert s.request_stop()[0]==202
    assert endpoint(s,'/api/start',{'request_id':ident})[0]==409
    checks.append('real HTTP browser-ready then one idempotent accepted launch; other ID rejected')
    assert s.snapshot()['launch_request_id']==ident and s.snapshot()['launch_status']=='accepted'
    checks.append('lost start ACK can reconcile exact ID from read-only status without retry')
finally:
    server.shutdown();server.server_close();thread.join(timeout=2)
assert not thread.is_alive()

cancel=TrialState('CANCEL',30,4096);cancel.update(phase='awaiting_launch')
assert cancel.request_stop()[0]==202 and not cancel.launch_event.is_set()
assert cancel.request_launch({'request_id':ident})[0]==409
checks.append('cancel before launch leaves spawn request count zero')

timeout=TrialState('TIMEOUT',30,4096);timeout.update(phase='awaiting_launch')
assert not timeout.launch_event.wait(.01) and not timeout.launch_request_id
checks.append('bounded missing-browser handshake has no launch request')

with tempfile.TemporaryDirectory(dir=HERE) as d:
    path=Path(d)/'.run.lock';path.touch()
    first=path.open('rb');second=path.open('rb')
    try:
        fcntl.flock(first,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:fcntl.flock(second,fcntl.LOCK_EX|fcntl.LOCK_NB);raise AssertionError('lock should conflict')
        except BlockingIOError:pass
        checks.append('existing owner lock is not stolen; fake spawn count zero')
    finally:first.close();second.close()
print(json.dumps({'status':'PASS','checks':checks,'production_order_AST':True,'real_guest_spawned':False},ensure_ascii=False,indent=2))
