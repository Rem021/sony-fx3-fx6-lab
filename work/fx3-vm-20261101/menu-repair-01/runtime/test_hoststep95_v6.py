from pathlib import Path
import importlib.util,json,struct,tempfile,hashlib
R=Path(__file__).resolve().parent;sp=importlib.util.spec_from_file_location('g95',R/'gate_input95.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
class Fake(m.InputGate):
 def __init__(self,run):super().__init__(run,delete_key=0x1f8);self.memory=bytearray(64);struct.pack_into('<Q',self.memory,0,m.MAGIC);self.writes=[]
 def connect(self):pass
 def packet(self,p):
  if p.startswith('m'):
   a,n=p[1:].split(',');a=int(a,16)-m.PHYS;n=int(n,16);assert 0<=a<=64 and a+n<=64;return self.memory[a:a+n].hex()
  if p.startswith('M'):
   prefix,data=p[1:].split(':');a,n=prefix.split(',');assert int(a,16)==m.PHYS+8 and int(n,16)==12;raw=bytes.fromhex(data);assert len(raw)==12;self.memory[8:20]=raw;self.writes.append(raw);return 'OK'
  raise AssertionError(p)
 def done(self):
  step,key,hold=struct.unpack_from('<III',self.memory,8);struct.pack_into('<IIQQIIQ',self.memory,24,step,key,1000000,1000000+hold*1000000,hold,0,step*2)
def rejects(f,typ):
 before=len(g.writes)
 try:f()
 except typ:pass
 else:raise AssertionError('expected rejection')
 assert len(g.writes)==before
D=R/'ap95-v6-hoststep-fixture';assert not D.exists();D.mkdir();g=Fake(D);assert not g.writes and not g.history
for args in [(1,0x99,100),(2,3,100),(1,3,49),(1,3,201)]:rejects(lambda a=args:g.command(*a,'page','reason'),ValueError)
rejects(lambda:g.command(1,3,100,'','reason'),ValueError)
g.command(1,3,100,'Language page','select English');assert len(g.writes)==1 and g.writes[0]==struct.pack('<III',1,3,100)
rejects(lambda:g.command(2,0x1ac,100,'Language','confirm'),RuntimeError);rejects(lambda:g.command(1,3,100,'Language','duplicate'),ValueError)
g.done()
for step in range(2,31):
 key=list(sorted(m.BASE_KEYS|{0x1f8}))[(step-2)%7];g.command(step,key,50 if step%2 else 200,'actual viewed page','audited white key');g.done()
assert len(g.writes)==30 and len(g.history)==30;rejects(lambda:g.command(31,3,100,'page','too many'),ValueError)
assert not m.valid_command(1,0x1f8,100,0,0);assert m.valid_command(1,0x1f8,100,0,0x1f8) # generic extension math only, not runtime authorization
out={'host_mock_commands':30,'max_step31_reject':True,'approved_delete_enabled':True,'unknown_hold_order_visual_missing_reject_before_write':True,'requires_guest_done_before_next_step':True,'each_only12B_in_new_control_area':True,'no_autonomous_initial_UP':True,'no_real_QEMU_or_guest_write':True,'delete_authority': 'RUNTIME-HANDOFF AP95'};(R/'ap95-v6-hoststep-host-test.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS AP95 mocked local-GDB command gate 30steps/strictdone/zero-write reject/12B only')
