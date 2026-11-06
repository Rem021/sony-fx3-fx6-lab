"""Own ARM64/fake-kernel child. Strictly fixture-only, no camera backend."""
from pathlib import Path
from hashlib import sha256
import argparse,importlib.util,json,os,socket,sys,threading
from live_arbiter import H,OLD,R,MODULE_SHA,fixture_inputs,wire,receive,Denied
p=argparse.ArgumentParser();p.add_argument('--fixture-only',action='store_true',required=True);p.add_argument('--fd',type=int,required=True);p.add_argument('--run',required=True);p.add_argument('--shared',required=True);a=p.parse_args()
sock=socket.socket(fileno=a.fd);sock.settimeout(45);init=receive(sock)
assert set(init)=={'kind','binding','request','mode','capacity'} and init['kind']=='RUN'
binding=init['binding'];request=bytes.fromhex(init['request']);mode=init['mode'];run=Path(a.run)
assert binding['request_sha256']==sha256(request).hexdigest() and binding['module_sha256']==MODULE_SHA
module,source=fixture_inputs()
sys.argv=[sys.argv[0],str(run)];sp=importlib.util.spec_from_file_location('model_types220',OLD/'test_handoff.py');M=importlib.util.module_from_spec(sp);sys.modules[sp.name]=M;sp.loader.exec_module(M)
B=M.B;profiles={}
for path,size,digest in B.FILE_PROFILE:
    raw=M.read_file(R/'work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'/path.lstrip('/'),size)
    assert sha256(raw).hexdigest()==digest;profiles[path]=raw
old=OLD.parent/'stage218-fixed-shell-process-filter'
busy=M.read_file(old/'originals/busybox',423000);parent=M.read_file(old/'originals/im.elf',40920)
total=init['capacity'];B.shape(total,int.from_bytes(request[40:44],'little'))
k=M.Kernel('kernel',source,profiles,busy,parent,Path(a.shared),request,binding['nonce'],fault='block' if mode=='block' else None,total=total,pid=os.getpid())
g=M.M.Guest(M.read_file(module,M.D.L.MAX_OBJECT),k,0x10000000);g.init();assert g.trace==[]
def send(kind,**extra):sock.sendall(wire(dict(kind=kind,binding=binding,pid=os.getpid(),**extra)))
send('READY');result=[];errors=[]
def run_guest():
    try:result.append(g.run_worker())
    except BaseException as e:errors.append(repr(e))
thread=threading.Thread(target=run_guest);thread.start()
if mode=='block':
    assert k.entered.wait(timeout=10) and thread.is_alive();send('ENTERED')
    assert receive(sock)=={'kind':'RELEASE_OWN_FIXTURE'};k.release.set()
thread.join(timeout=30);assert not thread.is_alive()
assert not errors and not g.errors and not k.errors and set(k.fds)==set(k.closed)
if mode=='crash-before-done':
    (run/'public-completion.json').write_text(json.dumps({'result':0,'complete':True,'pid':os.getpid()}))
    os._exit(22)  # owned fixture's deliberate exit; no external kill
if mode=='bad-nonce':binding={**binding,'nonce':'0'*64}
if mode=='bad-module':binding={**binding,'module_sha256':'0'*64}
send('DONE',result=result[0],source_reads=len(k.source_reads),fds_closed=True,errors=[],output=str(k.output))
if mode=='extra-frame':send('DONE',result=0,source_reads=2,fds_closed=True,errors=[],output=str(k.output))
if mode=='post-done-wait':assert receive(sock)=={'kind':'RELEASE_OWN_FIXTURE'}
sock.close()
