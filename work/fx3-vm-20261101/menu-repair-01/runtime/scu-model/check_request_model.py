from pathlib import Path
import subprocess,os,json,socket,time,uuid
O=Path(__file__).resolve().parent;v=json.loads((O/'build-result.json').read_text());assert v['exit']==0 and v['old_timer_binary_restored'];d=O/('qtest-'+uuid.uuid4().hex[:8]);d.mkdir();env=os.environ.copy();env['FX3_VM_SCU_REQUEST']='1';args=[v['binary']['path'],'-machine','virt,gic-version=2,secure=off','-accel','tcg','-cpu','cortex-a35','-m','64','-display','none','-nodefaults','-nic','none','-serial','none','-monitor','none','-qtest','unix:t,server=on,wait=off','-qmp','unix:q,server=on,wait=off','-S'];events=[];p=None
old=Path.cwd()
try:
 p=subprocess.Popen(args,cwd=d,env=env,stdout=(d/'stdout.log').open('wb'),stderr=(d/'stderr.log').open('wb'))
 for _ in range(100):
  if (d/'t').exists() and (d/'q').exists():break
  assert p.poll() is None;time.sleep(.02)
 os.chdir(d);t=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);t.settimeout(3);t.connect('t');q=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);q.settimeout(3);q.connect('q');os.chdir(old);tf=t.makefile('rb');qf=q.makefile('rb');json.loads(qf.readline());q.sendall(b'{"execute":"qmp_capabilities"}\n');json.loads(qf.readline())
 def call(cmd):
  t.sendall((cmd+'\n').encode());a=tf.readline().decode().strip();events.append({'command':cmd,'response':a});assert a.startswith('OK'),a;return a
 def status(expected):
  value=int(call('readl 0xf1388f60').split()[1],16);assert value==expected;assert not value&0x100
 status(0);call('writel 0xf1388f50 0x101');call('writel 0xf1388f54 0x101');status(0);call('writel 0xf1388f58 1');status(1);call('writel 0xf1388f5c 1');status(0);call('writel 0xf1388f58 0x100');status(0);call('writel 0xf1388f58 2');status(0)
 q.sendall(b'{"execute":"quit"}\n');p.wait(timeout=5);assert p.returncode==0
finally:
 os.chdir(old)
 if p is not None and p.poll() is None:p.terminate();p.wait(timeout=5)
(d/'receipt.json').write_text(json.dumps({'args':args,'events':events,'exit':p.returncode,'peer_ack_invariant_verified':True,'scope':'isolated register model qtest only, no firmware or CP execution'},indent=2)+'\n');print(d)
