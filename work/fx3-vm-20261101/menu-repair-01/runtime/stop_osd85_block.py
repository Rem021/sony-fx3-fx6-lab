from pathlib import Path
import json,socket,os,time
R=Path(__file__).resolve().parent;s0=json.loads((R/'STATE.json').read_text());run=Path(s0['current_run']);os.chdir(run);s=socket.socket(socket.AF_UNIX);s.settimeout(5);s.connect('q');f=s.makefile('rb');journal=[{'greeting':json.loads(f.readline())}];seq=0
def q(cmd,args=None):
 global seq
 seq+=1;r={'execute':cmd,'id':seq}
 if args is not None:r['arguments']=args
 s.sendall((json.dumps(r)+'\n').encode());journal.append({'request':r})
 while True:
  z=json.loads(f.readline());journal.append({'response':z})
  if z.get('id')==seq:return z
q('qmp_capabilities');q('stop')
cmds=['info registers','memsave 0xffffff80086994d8 0x10 "'+str(run/'printk-pointers.bin')+'"','memsave 0xffffff80086e47a0 0x20 "'+str(run/'printk-indices.bin')+'"','memsave 0xffffff80086e7538 0x20000 "'+str(run/'printk-ring.bin')+'"']
for c in cmds:q('human-monitor-command',{'command-line':c})
for a in json.loads((run/'command.json').read_text())['read_only_guest_memory_snapshots']:q('human-monitor-command',{'command-line':f'pmemsave {hex(a["address"])} {hex(a["size"])} "{run/a["name"]}"'})
q('query-cpus-fast');q('query-status');q('quit');(run/'blocked-stop-qmp.json').write_text(json.dumps({'reason':'Stop early for confirmed preload caller-identity regression; preserve original capid outermost gate in next candidate','commands':journal,'host_write_to_guest':False},indent=2)+'\n');print(run)
