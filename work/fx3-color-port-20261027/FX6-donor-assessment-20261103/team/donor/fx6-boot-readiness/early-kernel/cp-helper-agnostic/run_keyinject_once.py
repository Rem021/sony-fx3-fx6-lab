#!/usr/bin/env python3
import argparse,json,os,plistlib,socket,subprocess,sys,time,uuid,fcntl,signal,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent));import fixed_runner as fr
sys.path.insert(0,'/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime')
from gate_input96 import InputGate
MANIFEST=HERE/'vm-candidate-keyinject.json';SHA=HERE/'VM-CANDIDATE-KEYINJECT-SHA256.txt'
def sha(p):
 h=hashlib.sha256();h.update(Path(p).read_bytes());return h.hexdigest()
def check():
 v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
 if v.get('VolumeUUID')!=fr.UUID:raise RuntimeError('volume')
 if sha(MANIFEST)!=SHA.read_text().strip():raise RuntimeError('manifest')
 s=json.loads(MANIFEST.read_text())
 if s.get('status')!='APPROVED_SIXTYFIFTH_ONE_VM_PENDING_RUN':raise RuntimeError('status')
 for k in ('kernel','initrd','dtb','backup'):
  if sha(s[k]['path'])!=s[k]['sha256']:raise RuntimeError(k)
 return s
def run(s):
 held=fr.acquire();rd=HERE/'runs'/('keyinject-'+uuid.uuid4().hex[:8]);rd.mkdir(parents=True,mode=0o700)
 args=s['candidate_argv_before_observer_serial_retarget'].copy();args[args.index('-serial')+1]='file:'+str(rd/'serial.log')
 qemu=None;qmp=None;qr=None;receipt={}
 try:
  with (rd/'host-stderr.log').open('wb') as err:
   qemu=subprocess.Popen(args,cwd=rd,stdout=subprocess.DEVNULL,stderr=err,start_new_session=True,preexec_fn=fr.limits)
   deadline=time.monotonic()+15
   while not (rd/'q').exists() and qemu.poll() is None and time.monotonic()<deadline:time.sleep(.05)
   if qemu.poll() is not None:raise RuntimeError('qemu early')
   qmp=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);qmp.settimeout(3);fr.connect_relative(qmp,rd);qr=qmp.makefile('rb');json.loads(qr.readline());fr.qmp_send(qmp,qr,'qmp_capabilities',1);fr.qmp_send(qmp,qr,'cont',2)
   time.sleep(35)
   try:
    gate=InputGate(rd);receipt['key']=gate.command(1,0x1ab,100,'fx6-media-start','inject MENU key after media start');receipt['key_ok']=True
   except Exception as e:receipt['key_error']=repr(e);receipt['key_ok']=False
   time.sleep(20)
   fr.qmp_send(qmp,qr,'stop',40);fr.qmp_send(qmp,qr,'quit',41)
 finally:
  if qmp is not None:
   try:qmp.close()
   except Exception:pass
  if qemu is not None:
   try:qemu.wait(timeout=5)
   except subprocess.TimeoutExpired:
    if qemu.poll() is None:os.killpg(qemu.pid,signal.SIGTERM)
    try:qemu.wait(timeout=3)
    except subprocess.TimeoutExpired:
     if qemu.poll() is None:os.killpg(qemu.pid,signal.SIGKILL)
     qemu.wait(timeout=3)
  for st in reversed(held):fcntl.flock(st,fcntl.LOCK_UN);st.close()
  receipt['run']=str(rd);receipt['serial_bytes']=(rd/'serial.log').stat().st_size if (rd/'serial.log').exists() else 0
  (rd/'keyinject-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 return rd,receipt
def main():
 ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True);g.add_argument('--check',action='store_true');g.add_argument('--run',action='store_true');ns=ap.parse_args();s=check()
 if ns.check:print(json.dumps({'status':'PASS_KEYINJECT_CANDIDATE','manifest':sha(MANIFEST)},indent=2))
 else:print(json.dumps(run(s),indent=2))
if __name__=='__main__':main()
