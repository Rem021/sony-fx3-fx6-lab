"""Conditional FIFO receiver interleavings against the existing OWN ARM64.
No original driver/kernel executes. Only in-memory modeled processes exist.
"""
from pathlib import Path
from hashlib import sha256
from collections import deque
import importlib.util,json,sys
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage231-constructor-noexec-child-and-reload-observer'
for name,digest in [('model_entry.py','c1787e53acdc812ef9202007d03b6a4b0bf9e58b8ec8e720e36f26f01583f48a'),('entry_build.py','d9edd74d7016476e9493587f00a9df53931d91913fcb4434b8aaa595e769ee20')]:assert sha256((P/name).read_bytes()).hexdigest()==digest
spec=importlib.util.spec_from_file_location('stage231_sealed_model',P/'model_entry.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
binary=P/'runs-bounded-verified/built/parent-module.so';raw=binary.read_bytes();assert sha256(raw).hexdigest()=='c711f6ab13666c45249cc255d2ab09ec283496214d8941d11b9f1569124c47ec'
im=B/'stage218-fixed-shell-process-filter/originals/im.elf';imraw=im.read_bytes();assert sha256(imraw).hexdigest()=='5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91'
audit=json.loads((H/'kernel-assignment-audit.json').read_text());assert audit['worker_slots']['count']==4 and audit['normalized_index']==13
cases=[]
for first in range(4):
 for second in range(4):
  pending=deque();trace=[];slots={n:777+n for n in range(4)}
  def append(command):pending.append(command);trace.append(dict(event='append',command=command,wake_slots=list(slots)))
  def receive(slot):
   command=pending.popleft();trace.append(dict(event='receive_head',slot=slot,synthetic_tid=slots[slot],command=command));return slots[slot]
  append('START');k=M.Kernel(raw,imraw);k.parent.tid=receive(first);g=M.Guest(raw,k.parent);start=g.initialize();assert start==(1,0);g.unload();assert k.child
  k.child.guest.drop_original_file_backing();child_exit=k.child.guest.run_child();assert child_exit==0
  append('OBSERVE');k.parent.tid=receive(second);k.plan(2);observer=M.Guest(raw,k.parent,base=0x40000000);result=observer.initialize();observer.unload()
  if first==second:assert result==(3,0) and len(k.waits)==1 and k.waits[0]['status']==0
  else:assert result==(2,48) and k.waits==[]
  k.summary()  # Also verifies borrowed parent FDs stayed unchanged.
  assert not k.exec_attempts and not k.source_accesses and not pending
  cases.append(dict(first_slot=first,second_slot=second,synthetic_trace=trace,start=list(start),own_child_exit=child_exit,observation=list(result),waits=k.waits,other_thread_rejected=first!=second,child_original_file_mappings_removed=True))
out=dict(schema='fx3-stage233-conditional-receiver-interleavings-own-ARM64-v1',status='PASS',schedules=16,same_slot_observed=4,different_slot_HELD48=12,source_audit_sha256=sha256((H/'kernel-assignment-audit.json').read_bytes()).hexdigest(),own_binary=dict(path=str(binary.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()),own_model=dict(path=str((P/'model_entry.py').relative_to(R)),sha256=sha256((P/'model_entry.py').read_bytes()).hexdigest()),script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),cases=cases,all_four_slots_active_on_camera_assumed_for_conditional_example_only=True,actual_active_count_or_scheduler_measured=False,whole_kernel_or_ioctl_or_driver_simulated=False,original_im_bytes_only_used_for_fake_profile_file_never_executed=True,only_own_ARM64_executed=True,actual_Linux_processes_or_threads_created=False,new_device_operations=0,complete_boot_backup_or_recovery_verified=False,existing231_thread_guard_removed=False,goal_complete=False,first_flash_released=False)
(H/'receiver-schedule-results.json').open('x').write(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['status','schedules','same_slot_observed','different_slot_HELD48','actual_active_count_or_scheduler_measured','first_flash_released']}))
