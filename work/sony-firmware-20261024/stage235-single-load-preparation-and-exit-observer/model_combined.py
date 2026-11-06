"""Explicit fake kernel/scheduler. Only own combined ARM64 executes."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,struct,sys
H=Path(__file__).resolve().parent;B=H.parent
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
P=module('sealed234_for_single',B/'stage234-fixed-RAM-plan-preparer/model_prepare.py');M=P.M
D=module('single235_builder',H/'combined_build.py');U=M.U;A=M.A
OWNER='/tmp_wbshd/fx3-singleload-owner-v1';OUT=OWNER+'/entry.single-result'
class Kernel(P.Kernel):
 def __init__(self,raw,im,fault=None):
  super().__init__(raw,im,fault);self.combined_fault=fault;self.worker_started=False;self.parent_sleeps=0;self.mask_events=[];self.own_child=None;self.own_exit=None;self.wait_subjects=[];self.deferred_creator_signal=False;self.creator_signal_events=[];self.plan_mutated=False
 def clone(self,guest,args):
  assert args==[0,0,0,0,0,0] and self.child is None;parent=guest.process
  child=M.Process(self,7001,7001);child.ppid=parent.pid;child.creator_node=parent.thread_node();child.fds={fd:dict(row) for fd,row in parent.fds.items()};child.nextfd=parent.nextfd;child.mask=parent.mask;child.actions=dict(parent.actions);child.exit_signal=0;child.role='own'
  cg=Guest(self.raw,child,base=guest.base,copy_from=guest);child.guest=cg;cg.u.reg_write(A.UC_ARM64_REG_X0,0);self.child=self.own_child=child
  # Remove old file mappings BEFORE the own child gets its first instruction.
  cg.drop_original_file_backing()
  self.clone_events.append(dict(flags=0,shared_VM=False,shared_FD_table=False,shared_sighand=False,parent_mask=parent.mask,child_mask=child.mask,child_pid=child.pid));return child.pid
 def replace_same_creator(self):
  old=self.child;assert old and not old.alive and old.reaped
  new=M.Process(self,7001,7001);new.ppid=321;new.alive=False;new.exit_status=0;new.exit_signal=0;new.creator_node=self.parent.thread_node();new.guest=old.guest;new.role='foreign';self.child=new
  self.creator_signal_events.append(dict(event='signal_callback_created_same_PID_child',after_original_reaped=True,original_exit=self.own_exit))
 def syscall(self,g,n,args):
  p=g.process;u=g.u;a,b,c,d,e,f=args;fault=self.combined_fault
  if n==56 and fault=='mutate-plan-between' and self.clock_calls>=3 and not self.plan_mutated:
   name=bytes(u.mem_read(b,96)).split(b'\0')[0].decode('ascii');path=(p.fds[a]['desc']['node'].path+'/'+name) if a!=-100 else name
   if path==P.PLAN:
    import zlib
    node=self.nodes[path];node.data[32]^=1;struct.pack_into('<I',node.data,252,zlib.crc32(node.data[:252]));node.gen+=1;self.plan_mutated=True
  if n==34:
   name=bytearray()
   for i in range(80):
    value=u.mem_read(b+i,1)[0]
    if not value:break
    name.append(value)
   if bytes(name)==b'fx3-singleload-owner-v1':
    self.worker_started=True;self.allow_worker=True
    self.fault='child-control-close' if fault in ['child-control-close','same-creator-after-nonzero','foreign-parent-sharing'] else fault
  if n==209 and self.worker_started and fault=='socket-profile' and p.pid==321 and c==3:
   u.mem_write(d,struct.pack('<I',1));u.mem_write(e,struct.pack('<I',4));return 0
  if n==101 and p.pid==321:
   assert self.worker_started and (b,c,d)==(0,0,0) and struct.unpack('<qq',u.mem_read(a,16))==(0,10000000);self.parent_sleeps+=1
   if fault!='stall-child' and self.child and self.child.alive:
    self.own_exit=self.child.guest.run_child();assert self.own_exit is not None
   self.clock+=10_000_000;return 0
  if n==260:
   if fault in ['same-creator-after-nonzero','same-creator-after-zero'] and not self.creator_signal_events:
    assert p.mask&(1<<9);self.deferred_creator_signal=True;self.creator_signal_events.append(dict(event='SIGUSR1_callback_deferred_by_continuous_mask'))
   if fault=='foreign-other-thread' and self.child and not self.child.alive and not self.pid_reused:
    old=self.child;old.reaped=True;new=M.Process(self,7001,7001);new.ppid=321;new.alive=False;new.exit_status=0;new.exit_signal=0;new.creator_node=M.Node('foreign creator888',0o40555);new.guest=old.guest;new.role='foreign';self.child=new;self.pid_reused=True
   if fault=='foreign-parent-sharing' and self.child and not self.child.alive and not self.pid_reused:
    # Explicit conditional model input: a parent-sharing/adopted child can
    # become eligible without a user callback running in the blocked creator.
    old=self.child;old.reaped=True;new=M.Process(self,7001,7001);new.ppid=321;new.alive=False;new.exit_status=0;new.exit_signal=0;new.creator_node=self.parent.thread_node();new.guest=old.guest;new.role='foreign-parent-sharing';self.child=new;self.pid_reused=True
   self.wait_subjects.append(dict(role=getattr(self.child,'role','none'),mask=p.mask,tid=p.tid))
  before=p.mask
  result=super().syscall(g,n,args)
  if n==135 and p.pid==321:
   self.mask_events.append(dict(before=before,after=p.mask,result=result))
   if b and result==0 and not p.mask&(1<<9) and self.deferred_creator_signal:
    self.deferred_creator_signal=False
    if self.own_child and self.own_child.reaped:self.replace_same_creator()
  return result
 def combined_summary(self):
  summary=self.prepare_summary();summary.update(plan_mutated=self.plan_mutated,worker_started=self.worker_started,clones=self.clone_events,waits=self.waits,wait_subjects=self.wait_subjects,mask_events=self.mask_events,final_parent_mask=self.parent.mask,creator_signal_events=self.creator_signal_events,own_child_exit=self.own_exit,own_child_alive=self.own_child.alive if self.own_child else False,parent_sleeps=self.parent_sleeps,source_accesses=self.source_accesses,exec_attempts=self.exec_attempts,child_original_mapping_removed=bool(self.own_child),single_result=bytes(self.nodes[OUT].data).hex() if OUT in self.nodes else None);return summary
class Guest(M.Guest):
 def __init__(self,raw,process,base=0x30000000,copy_from=None):
  self.raw=raw;self.process=process;self.kernel=process.kernel;self.base=base;self.report=D.inspect_layout(raw);self.errors=[];self.trace=[];self.exitcode=None;self.blocked=False;self.unloaded=False;self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM);self.stop=0x71000000
  if copy_from:
   for a,z,perms in copy_from.u.mem_regions():self.u.mem_map(a,z-a+1,perms);self.u.mem_write(a,bytes(copy_from.u.mem_read(a,z-a+1)))
   self.u.context_restore(copy_from.u.context_save())
  else:
   for seg in self.report['segments']:
    flags=seg['flags'];perms=(U.UC_PROT_READ if flags&4 else 0)|(U.UC_PROT_WRITE if flags&2 else 0)|(U.UC_PROT_EXEC if flags&1 else 0);self.u.mem_map(base+seg['va'],D.align(seg['memsz'],D.PAGE),perms)
    if seg['filesz']:self.u.mem_write(base+seg['va'],raw[seg['offset']:seg['offset']+seg['filesz']])
   for rel in self.report['runtime_relocations']:self.u.mem_write(base+rel['offset'],struct.pack('<Q',base+rel['addend']))
   self.u.mem_protect(base+3*D.PAGE,D.PAGE,U.UC_PROT_READ);self.u.mem_map(0x70000000,0x20000,U.UC_PROT_READ|U.UC_PROT_WRITE);self.u.mem_map(self.stop,4096,U.UC_PROT_READ|U.UC_PROT_EXEC);self.u.reg_write(A.UC_ARM64_REG_CPACR_EL1,3<<20)
  self.u.hook_add(U.UC_HOOK_INTR,self.interrupt)
 def status(self):return (self.call(self.report['exports']['fx3_single_state']['va']),self.call(self.report['exports']['fx3_single_reason']['va']))
