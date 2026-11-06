from pathlib import Path
import subprocess,os,json,socket,time,uuid
O=Path(__file__).resolve().parent;v=json.loads((O/'build-result.json').read_text());assert v['exit']==0 and v['old_timer_binary_restored'];d=O/('qtest-'+uuid.uuid4().hex[:8]);d.mkdir();env=os.environ.copy();env['FX3_VM_GPIO_BANK5']='1';args=[v['binary']['path'],'-machine','virt,gic-version=2,secure=off','-accel','tcg','-cpu','cortex-a35','-m','64','-display','none','-nodefaults','-nic','none','-serial','none','-monitor','none','-qtest','unix:t,server=on,wait=off','-qmp','unix:q,server=on,wait=off','-S'];events=[];p=None
old=Path.cwd()
try:
 p=subprocess.Popen(args,cwd=d,env=env,stdout=(d/'stdout.log').open('wb'),stderr=(d/'stderr.log').open('wb'))
 for _ in range(100):
  if (d/'t').exists() and (d/'q').exists():break
  assert p.poll() is None;time.sleep(.02)
 os.chdir(d);t=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);t.settimeout(3);t.connect('t');q=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);q.settimeout(3);q.connect('q');os.chdir(old);tf=t.makefile('rb');qf=q.makefile('rb');json.loads(qf.readline());q.sendall(b'{"execute":"qmp_capabilities"}\n');json.loads(qf.readline())
 def call(cmd):
  t.sendall((cmd+'\n').encode());a=tf.readline().decode().strip();events.append({'command':cmd,'response':a});assert a.startswith('OK'),a;return a
 def value(off,n):assert int(call('readl '+hex(0xf1022000+off)).split()[1],16)==n
 for base in [0,0x20,0x30,0x40]:
  value(base,0);call('writel '+hex(0xf1022000+base)+' 0x10');value(base,0x10);call('writel '+hex(0xf1022000+base+4)+' 0x80');value(base,0x90);call('writel '+hex(0xf1022000+base+8)+' 0x10');value(base,0x80)
 q.sendall(b'{"execute":"quit"}\n');p.wait(timeout=5);assert p.returncode==0
finally:
 os.chdir(old)
 if p is not None and p.poll() is None:p.terminate();p.wait(timeout=5)
(d/'receipt.json').write_text(json.dumps({'args':args,'events':events,'exit':p.returncode,'register_set_clear_readback_verified':True,'scope':'isolated register model qtest only, no firmware or CP execution'},indent=2)+'\n');print(d)
