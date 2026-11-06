"""Record the CURRENT own binary's unresolved parent-sharing counterexample.
This is a fake-kernel conditional input, not an observed camera event.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util,json
H=Path(__file__).resolve().parent;B=H.parent
spec=importlib.util.spec_from_file_location('current_single_model',H/'model_combined.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
binary=H/'runs-integrated-verified/built/parent-module.so';raw=binary.read_bytes();im=(B/'stage218-fixed-shell-process-filter/originals/im.elf').read_bytes();k=M.Kernel(raw,im,'foreign-parent-sharing');g=M.Guest(raw,k.parent);result=g.initialize();g.unload()
assert result==(3,0) and k.own_exit==68 and k.waits[-1]['status']==0 and k.wait_subjects[-1]['role']=='foreign-parent-sharing' and k.wait_subjects[-1]['mask']&(1<<9)
out=dict(schema='fx3-single-load-unresolved-parent-sharing-identity-v1',status='CURRENT_COUNTEREXAMPLE_REPRODUCED_DO_NOT_RELEASE',current_binary_path=str(binary.relative_to(H.parents[2])),current_binary_sha256=sha256(raw).hexdigest(),model_sha256=sha256((H/'model_combined.py').read_bytes()).hexdigest(),script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),result=list(result),original_own_child_exit=68,reused_PID_foreign_exit=0,current_false_complete=True,creator_signal_mask_still_blocked=True,requires_unverified_parent_sharing_or_thread_death_adoption_context=True,original_exit_reaped_by_explicit_external_WALL_model_input=True,current_camera_context_supporting_this_interleaving_measured=False,summary=k.combined_summary(),original_Sony_Linux_or_glibc_executed=False,new_device_operations=0,must_not_release_this_candidate=True,first_flash_released=False)
(H/'remaining-parent-identity-counterexample.json').open('x').write(json.dumps(out,indent=2)+'\n');print(json.dumps({x:out[x] for x in ['status','result','original_own_child_exit','reused_PID_foreign_exit','current_false_complete','first_flash_released']}))
