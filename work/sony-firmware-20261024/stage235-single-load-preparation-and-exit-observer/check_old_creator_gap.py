"""Own231 binary only: a retained creator inode does not pin its child PID."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json
H=Path(__file__).resolve().parent;B=H.parent;P=B/'stage231-constructor-noexec-child-and-reload-observer'
spec=importlib.util.spec_from_file_location('sealed231_gap',P/'model_entry.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
assert sha256((P/'model_entry.py').read_bytes()).hexdigest()=='c1787e53acdc812ef9202007d03b6a4b0bf9e58b8ec8e720e36f26f01583f48a'
raw=(P/'runs-bounded-verified/built/parent-module.so').read_bytes();assert sha256(raw).hexdigest()=='c711f6ab13666c45249cc255d2ab09ec283496214d8941d11b9f1569124c47ec'
im=(B/'stage218-fixed-shell-process-filter/originals/im.elf').read_bytes();cases=[]
for replacement in ['none','other-creator','same-live-creator']:
 k=M.Kernel(raw,im,'child-control-close');g=M.Guest(raw,k.parent);assert g.initialize()==(1,0);g.unload();old=k.child;old.guest.drop_original_file_backing();assert old.guest.run_child()==68
 if replacement!='none':
  k.im_reap(all_children=True);assert old.reaped
  new=M.Process(k,7001,7001);new.ppid=321;new.alive=False;new.exit_status=0;new.exit_signal=0;new.creator_node=k.parent.thread_node() if replacement=='same-live-creator' else M.Node('different creator',0o40555);new.guest=old.guest;k.child=new
 k.plan(2);observer=M.Guest(raw,k.parent,base=0x40000000);result=observer.initialize();observer.unload()
 if replacement=='same-live-creator':assert result==(3,0) and k.waits[-1]['status']==0
 else:assert result[0]==2
 cases.append(dict(replacement=replacement,original_child_exit=68,private_DONE_from_original_child=True,creator_thread_still_live=True,synthetic_foreign_child_exit=0 if replacement!='none' else None,old_result=list(result),waits=k.waits,old_parent_mask_after_START=k.parent.mask))
out=dict(schema='fx3-same-creator-between-loads-PID-reuse-counterexample-v1',status='COUNTEREXAMPLE_REPRODUCED',old_binary_path=str((P/'runs-bounded-verified/built/parent-module.so').relative_to(H.parents[2])),old_binary_sha256=sha256(raw).hexdigest(),old_model_sha256=sha256((P/'model_entry.py').read_bytes()).hexdigest(),script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),cases=cases,old_same_thread_guard_is_complete_child_identity_proof=False,old_WNOTHREAD_rejects_other_thread_replacement_only=True,foreign_child_and_reaping_are_explicit_fake_kernel_inputs=True,original_Sony_Linux_or_glibc_executed=False,new_device_operations=0,first_flash_released=False)
(H/'old-creator-gap-counterexample.json').open('x').write(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(status=out['status'],cases=len(cases),old_same_live_creator_misattribution=True,original_child_exit=68,wrongly_accepted_exit=0,actual_camera_operations=0)))
