from pathlib import Path
import subprocess,json,socket,time,os,resource,hashlib,datetime,plistlib,signal
root=Path(__file__).resolve().parent
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
qemu=root/'build/qemu-system-aarch64'
assets=root.parent/'fx3-audit'
kernel=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin')
dtb=assets/'virt-probe01.dtb';initrd=assets/'fx3-minimal-original-userspace-v2.cpio.gz'
run=root/'runs/p02';run.mkdir()
checks=[(kernel,'da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'),(dtb,'a8cd5a3ec6d43d8769fbe76eb4db14d18ff0df689af2388bcaf8e631d4c067e3'),(initrd,'c704d71d6e6618b087d21c3a2a1a2bb562cb19085032a69f7ec43314302c4f4f')]
for p,h in checks:assert hashlib.sha256(p.read_bytes()).hexdigest()==h
args=[str(qemu),'-machine','virt,gic-version=2,secure=off','-accel','tcg','-cpu','cortex-a35','-smp','1','-m','2048','-display','none','-nodefaults','-nic','none','-no-reboot','-monitor','none','-serial','file:'+str(run/'serial.log'),'-qmp','unix:'+str(run/'qmp.sock')+',server=on,wait=off','-d','in_asm','-D',str(run/'instruction.log'),'-S','-kernel',str(kernel),'-initrd',str(initrd),'-device','loader,file='+str(dtb)+',addr=0x40002000,force-raw=on']
(run/'command.json').write_text(json.dumps(args,indent=2)+'\n')
def limits():resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024*1024,16*1024*1024))
started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
with (run/'host-stdout.log').open('wb') as stdout,(run/'host-stderr.log').open('wb') as stderr:
 p=subprocess.Popen(args,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=limits)
 samples=[];responses=[]
 try:
  for _ in range(50):
   if (run/'qmp.sock').exists() or p.poll() is not None:break
   time.sleep(.1)
  s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.settimeout(2);s.connect(str(run/'qmp.sock'));f=s.makefile('rb');responses.append({'greeting':json.loads(f.readline())})
  seq=0
  def qmp(cmd,arguments=None):
   global seq
   seq+=1;obj={'execute':cmd,'id':seq}
   if arguments is not None:obj['arguments']=arguments
   s.sendall((json.dumps(obj)+'\n').encode())
   while True:
    res=json.loads(f.readline());responses.append(res)
    if res.get('id')==seq:return res
  qmp('qmp_capabilities');qmp('human-monitor-command',{'command-line':'info registers'});qmp('cont')
  deadline=time.monotonic()+3
  while time.monotonic()<deadline and p.poll() is None:
   st=subprocess.run(['ps','-o','rss=,vsz=','-p',str(p.pid)],capture_output=True,text=True)
   samples.append({'elapsed_seconds':time.monotonic()-t,'rss_vsz_kib':st.stdout.strip()})
   time.sleep(.25)
  if p.poll() is None:
   qmp('stop');qmp('query-status');qmp('human-monitor-command',{'command-line':'info registers'});qmp('query-cpus-fast');qmp('quit')
  p.wait(timeout=5)
 except Exception as e:
  responses.append({'host_observer_error':repr(e)})
 finally:
  if p.poll() is None:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=3)
(run/'qmp.json').write_text(json.dumps(responses,indent=2)+'\n')
receipt={'created_utc':started,'duration_seconds':time.monotonic()-t,'qemu_sha256':hashlib.sha256(qemu.read_bytes()).hexdigest(),'input_checks':[{'path':str(p),'sha256':h} for p,h in checks],'qemu_exit':p.returncode,'pid':p.pid,'memory_samples':samples,'guest_seconds_requested':3,'trace_limit_bytes':16*1024*1024,'physical_devices_disks_network_or_firmware_writes':0,'original_kernel_modified':False,'receipt_scope':'Stock virt model baseline executing original FX3 Image; no Sony hardware compatibility claim'}
(run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
print('SERIAL', (run/'serial.log').read_text(errors='replace')[-1500:])
print('QMP',json.dumps(responses[-5:],indent=2)[:3500])
print('TRACE_BYTES',(run/'instruction.log').stat().st_size)
