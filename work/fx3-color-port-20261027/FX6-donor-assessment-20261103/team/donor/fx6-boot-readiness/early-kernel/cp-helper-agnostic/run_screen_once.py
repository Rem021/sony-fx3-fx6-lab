#!/usr/bin/env python3
import argparse,json,os,plistlib,socket,subprocess,sys,time,uuid,fcntl,signal,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent));import fixed_runner as fr
MANIFEST=HERE/'vm-candidate-screen.json';SHA=HERE/'VM-CANDIDATE-SCREEN-SHA256.txt'
def sha(p):
 h=hashlib.sha256();h.update(Path(p).read_bytes());return h.hexdigest()
def check():
 v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
 if v.get('VolumeUUID')!=fr.UUID:raise RuntimeError('volume')
 if sha(MANIFEST)!=SHA.read_text().strip():raise RuntimeError('manifest')
 s=json.loads(MANIFEST.read_text())
 if s.get('status')!='APPROVED_THIRTIETH_SCREEN_PENDING_RUN':raise RuntimeError('status')
 for k in ('kernel','initrd','dtb','backup'):
  if sha(s[k]['path'])!=s[k]['sha256']:raise RuntimeError(k)
 return s
def run(s,seconds):
 held=fr.acquire();rd=HERE/'runs'/('screen-'+uuid.uuid4().hex[:8]);rd.mkdir(parents=True,mode=0o700)
 args=s['candidate_argv_before_observer_serial_retarget'].copy();args[args.index('-serial')+1]='file:'+str(rd/'serial.log')
 qemu=None;qmp=None
 try:
  with (rd/'host-stderr.log').open('wb') as err:
   qemu=subprocess.Popen(args,cwd=rd,stdout=subprocess.DEVNULL,stderr=err,start_new_session=True,preexec_fn=fr.limits)
   deadline=time.monotonic()+seconds
   while not (rd/'q').exists() and qemu.poll() is None and time.monotonic()<deadline:time.sleep(.05)
   if qemu.poll() is not None:raise RuntimeError('qemu early')
   qmp=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);qmp.settimeout(3);fr.connect_relative(qmp,rd)
   qr=qmp.makefile('rb');json.loads(qr.readline());fr.qmp_send(qmp,qr,'qmp_capabilities',1);fr.qmp_send(qmp,qr,'cont',2)
   time.sleep(max(5,seconds-5))
   shot=rd/'screen.ppm';fr.qmp_send(qmp,qr,'screendump',3,{'filename':str(shot)})
   time.sleep(1)
   json.dump({'run':str(rd),'shot':str(shot),'shot_bytes':shot.stat().st_size if shot.exists() else 0,'serial_bytes':(rd/'serial.log').stat().st_size if (rd/'serial.log').exists() else 0},open(rd/'screen-receipt.json','w'),indent=2)
 finally:
  if qmp is not None:
   try:fr.qmp_send(qmp,qr,'quit',9)
   except Exception:pass
   qmp.close()
  if qemu is not None:
   try:qemu.wait(timeout=5)
   except subprocess.TimeoutExpired:
    if qemu.poll() is None:os.killpg(qemu.pid,signal.SIGTERM)
    try:qemu.wait(timeout=3)
    except subprocess.TimeoutExpired:
     if qemu.poll() is None:os.killpg(qemu.pid,signal.SIGKILL)
     qemu.wait(timeout=3)
  for st in reversed(held):fcntl.flock(st,fcntl.LOCK_UN);st.close()
 return rd
def main():
 ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True);g.add_argument('--check',action='store_true');g.add_argument('--run',action='store_true');ap.add_argument('--seconds',type=int,default=50);ns=ap.parse_args()
 s=check()
 if ns.check:print(json.dumps({'status':'PASS_SCREEN_CANDIDATE','manifest':sha(MANIFEST)},indent=2))
 else:print(run(s,ns.seconds))
if __name__=='__main__':main()
