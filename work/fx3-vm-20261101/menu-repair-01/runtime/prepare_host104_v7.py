from pathlib import Path
import ast
R=Path(__file__).resolve().parent
def save(n,s):p=R/n;assert not p.exists();ast.parse(s);p.write_text(s)
s=(R/'gdb_native104_v2.py').read_text().replace('import re,select,time','import re,select,time,json')
s=s.replace('    def _stop(self,response):\n', '''    def _journal(self,kind,payload):
        with (self.run/'gdb104-execution.jsonl').open('a')as f:f.write(json.dumps({'host_monotonic':time.monotonic(),'kind':kind,'payload':payload})+'\\n')
    def _stop(self,response):
        self._journal('native_stop',response)
''')
s=s.replace('    def _send(self,payload):\n', "    def _send(self,payload):\n        if payload.startswith('vCont;')or payload=='?':self._journal('execution_command',payload)\n")
s=s.replace("            if r.startswith(('T','S')):\n                self._stop(r)", """            if r.startswith(('T','S')):
                if payload=='?'and re.fullmatch(r'T05core:[0-9a-fA-F]+;',r):
                    # QEMU gdb_build_stop_packet: cleanup query identifies core,
                    # not thread. Never promote this reply to observation CPU.
                    self._journal('cleanup_core_reply',r);self.debug_stops.append(r);return r
                self._stop(r)""")
save('gdb_native104_v3.py',s)
s=(R/'check_native104_v2.py').read_text().replace('gdb_native104_v2','gdb_native104_v3')
s=s.replace(' a.close();b.close()', ''' b.sendall(frame('T05core:03;'));assert g.packet('?')=='T05core:03;';b.recv(4096)
 b.sendall(frame('T05core:03;'))
 try:g.packet('g');raise AssertionError('Observation accepted a CPU without native thread identity')
 except RuntimeError as e:assert 'lacks CPU thread identity'in str(e)
 a.close();b.close()''')
save('check_native104_v3.py',s)
s=(R/'gate_input104_v5.py').read_text().replace('from gdb_native104_v2 import InputGate','from gdb_native104_v3 import InputGate')
s=s.replace('    def poll(self):\n', '''    def poll(self):
        try:return self._poll_native()
        except Exception as exc:
            self.observer_error=repr(exc)
            # Persist BEFORE cleanup, including partial failing record and
            # actual post-step PC. Failure evidence must not depend on close.
            (self.run/'ap104-error-records.json').write_text(json.dumps({'observer_error':repr(exc),'records':self.records,'first_unfetched':self.first_unfetched,'guest_resume_after_error':False},indent=2)+'\\n')
            self.save(force=True)
            raise
    def _poll_native(self):
''')
s=s.replace("'records_count':len(self.records),", "'records_count':len(self.records),'observer_error':getattr(self,'observer_error',None),")
save('gate_input104_v6.py',s)
s=(R/'check_gate104_v5.py').read_text().replace('gate_input104_v5','gate_input104_v6')
s=s.replace(" o.close();assert o.removed", " o.close();assert o.removed",1)
# Exercise the real poll error wrapper with a deliberately wrong post-PC and
# inspect durable failing record even before close is invoked.
s=s.replace("print('AP104_NATIVE_STOP_CPU_OWNER", '''with tempfile.TemporaryDirectory(prefix='fx3-gate104-fault-')as td:
 root=Path(td);(root/'ap104-observer-original-proof-v1.json').write_text(json.dumps(proof));run=root/'runs'/'fault';run.mkdir(parents=True);(run/'serial.log').write_text('');g=Gate();qmp=QMP();o=KernelObserver(run,g,qmp,{'kernel_points':[]});o.sysregs=Sys();base=0xffffff80004be000
 for p in proof['uipc_points']:g.mem[base+p['offset']]=bytes.fromhex(p['raw'])
 o.install_uipc(base);p=next(x for x in proof['uipc_points']if x['label']=='dynamic_owner_claim');g.label='dynamic_owner_claim';g.regs=[0]*33;g.regs[0]=0x8261c0;g.regs[3]=Q;g.regs[29]=FP;g.regs[32]=base+p['offset'];old=g.packet
 def wrong_step(payload):
  r=old(payload)
  if payload=='s':g.regs[32]+=4
  return r
 g.packet=wrong_step
 try:o.poll();raise AssertionError('Expected strict PC guard')
 except RuntimeError as e:assert 'PC mismatch'in str(e)
 failed=json.loads((run/'ap104-error-records.json').read_text());last=failed['records'][-1];assert last['post_step_PC']!=last['expected_post_step_PC']and last['step_stop']=='T05thread:03;'and not failed['guest_resume_after_error']
print('AP104_NATIVE_STOP_CPU_OWNER''')
save('check_gate104_v6.py',s)
s=(R/'run_candidate104_v6.py').read_text().replace('gate_input104_v5','gate_input104_v6').replace('gdb_native104_v2','gdb_native104_v3');save('run_candidate104_v7.py',s)
print('HOST104_V7_ERROR_DURABILITY_CLEANUP_CORE_REPLY_CREATED')
