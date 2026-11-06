from pathlib import Path
R=Path(__file__).resolve().parent
def save(n,s):
 p=R/n;assert not p.exists(),p;p.write_text(s)
s=(R/'gdb_native104_v1.py').read_text().replace("if step:\n                    if not r.startswith", "if payload=='?':return r\n                if step:\n                    if not r.startswith")
save('gdb_native104_v2.py',s)
s=(R/'check_native104_v1.py').read_text().replace('gdb_native104_v1','gdb_native104_v2')
s=s.replace("a.close();b.close()", "b.sendall(frame('T02thread:04;'));assert g.packet('?')=='T02thread:04;';b.recv(4096)\n a.close();b.close()")
save('check_native104_v2.py',s)
s=(R/'gate_input104_v3.py').read_text().replace('from gate_input102_v4 import InputGate,valid_command,KernelObserver as BackupObserver','from gate_input102_v4 import valid_command,KernelObserver as BackupObserver\nfrom gdb_native104_v2 import InputGate')
start=s.index("        if self.qmp('query-status')")
end=s.index("        if pc not in self.points",start)
s=s[:start]+'''        if self.qmp('query-status').get('return',{}).get('status')!='debug':
            if not self.gate.wait_native_stop(.25):return False
            if self.qmp('query-status').get('return',{}).get('status')!='debug':return False
        if self.gate.native_stop is None and not self.gate.wait_native_stop(3):
            raise RuntimeError('AP104 debug stop lacks native T05 identity')
        self.gate.bind_native_stop()
        native_stop=self.gate.native_stop;native_thread=self.gate.native_thread
        started=time.monotonic();raw=bytes.fromhex(self.gate.packet('g'));regs=struct.unpack_from('<33Q',raw);pc=regs[32]
'''+s[end:]
s=s.replace("'thread':thread,'read_only", "'thread':thread,'native_stop_reply':native_stop,'native_cpu_thread':native_thread,'read_only")
s=s.replace("        if not stepped.startswith(('T05','S05')):raise RuntimeError('AP104 original instruction step failed')", """        record['step_stop']=stepped
        if not stepped.startswith('T05'):raise RuntimeError('AP104 original instruction step failed')
        self.gate.bind_native_stop()
        after=bytes.fromhex(self.gate.packet('g'));after_regs=struct.unpack_from('<33Q',after)
        expected_pc=regs[30] if module=='gpe'and label.endswith('_return')else pc+4
        record['step_native_cpu_thread']=self.gate.native_thread
        record['post_step_PC']=hex(after_regs[32]);record['expected_post_step_PC']=hex(expected_pc)
        if after_regs[32]!=expected_pc:raise RuntimeError('AP104 original single-vCPU instruction PC mismatch')""")
s=s.replace("after=bytes.fromhex(self.gate.packet('g'));record['actual_original_error_w0']", "record['actual_original_error_w0']")
s=s.replace("native GDB socket readiness; no fixed250ms service sleep after breakpoints armed", "native T05 identity; Hg/Hc only actual stopped CPU; vCont;s:thread holds other CPUs; asynchronous vCont;c resume")
save('gate_input104_v4.py',s)
s=(R/'run_candidate104_v3.py').read_text().replace('gate_input104_v3','gate_input104_v4').replace('restore_api103_v1','restore_api103_v2')
s=s.replace("'gate_input104_v4.py','gdb_sysregs104_v2.py'", "'gate_input104_v4.py','gdb_sysregs104_v2.py','gdb_native104_v2.py'")
needle='            phaseA_capture=None\n';assert s.count(needle)==1
s=s.replace(needle,"""            raw_qmp=qmp
            def controlled_qmp(cmd,arguments=None):
                if cmd=='cont' and kernel_observer.points and not kernel_observer.removed:
                    input_gate.continue_all()
                    return {'return':{}}
                return raw_qmp(cmd,arguments)
            qmp=controlled_qmp
            kernel_observer.qmp=qmp;ring_reader.qmp=qmp
"""+needle)
s=s.replace("'FX3_LDEC103_INIT_FAILED','FX3_LDEC103_SELFTEST_FAILED'", "'FX3_LDEC103_INIT_FAILED','FX3_LDEC103_SELFTEST_FAILED','FX3_FILE103_READY_FAILED'")
save('run_candidate104_v4.py',s)
s=(R/'check_gate104_v3.py').read_text().replace('gate_input104_v3','gate_input104_v4')
s=s.replace(" def connect(self):pass", " def connect(self):pass\n native_stop='T05thread:03;';native_thread='03'\n def wait_native_stop(self,timeout):return True\n def bind_native_stop(self):assert self.native_thread=='03'")
s=s.replace("self.regs[32]+=4;return 'T05thread:03;'", "self.regs[32]=self.regs[30] if self.label.endswith('_return')and not self.label.startswith('first_unfetched')else self.regs[32]+4;return 'T05thread:03;'")
save('check_gate104_v4.py',s)
print('HOST104_V4_CREATED')
