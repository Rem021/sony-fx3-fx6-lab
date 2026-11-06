"""Own finite scheduling model, NOT Linux execution or an FX3 measurement.

Assume two distinct kernel pid objects A/B can have the same numeric pid.
B is explicitly eligible under the same parent, as in stage235's residual
counterexample. Each modeled wait status is genuine for its pinned object.
"""
from itertools import permutations
from pathlib import Path
from hashlib import sha256
import json
H=Path(__file__).resolve().parent

EVENTS=('wait_enter','release_A','exit_A_68','external_reap_A','create_B_0','wait_return')
EDGES=(('release_A','exit_A_68'),('exit_A_68','external_reap_A'),
       ('external_reap_A','create_B_0'),('wait_enter','wait_return'),('exit_A_68','wait_return'))
def schedules(edges):
    return [s for s in permutations(EVENTS) if all(s.index(a)<s.index(b) for a,b in edges)]
def run(s):
    a='alive';b=False;ref=None;result=None;trace=[]
    for e in s:
        if e=='wait_enter':ref='A' if a in ('alive','zombie') else ('B' if b else None)
        elif e=='exit_A_68':assert a=='alive';a='zombie'
        elif e=='external_reap_A':
            if a=='zombie':a='gone'
        elif e=='create_B_0':assert a=='gone';b=True
        elif e=='wait_return':
            if ref=='A' and a=='zombie':result=dict(object='A',kind='normal',code=68);a='gone'
            elif ref=='B' and b:result=dict(object='B',kind='normal',code=0);b=False
            else:result=dict(object=None,kind='ECHILD',code=None)
        trace.append(dict(event=e,pinned_object=ref,A=a,B_zombie=b,result=result))
    return dict(order=list(s),result=result,false_complete=result['object']=='B' and result['code']==0,trace=trace)

all_ungated=[run(s) for s in schedules(EDGES)]
all_gated=[run(s) for s in schedules(EDGES+(('wait_enter','release_A'),))]
assert all_ungated and all_gated
bad=[r for r in all_ungated if r['false_complete']]
assert bad and not any(r['false_complete'] for r in all_gated)
assert {r['result']['kind'] for r in all_gated}=={'normal','ECHILD'}
assert all(r['result']['code'] in (68,None) for r in all_gated)

counterexamples=[]
def counter(name,events,explanation):
    counterexamples.append(dict(name=name,events=events,old_A_actual_exit='normal68 or signal9 as stated',
                                falsely_observed_normal0=True,explanation=explanation))
counter('WNOHANG pre-poll drops the reference',
        ['wait4_A_WNOHANG_pin_A','returns0_put_pid_A','release_A','A_exit68','external_reap_A',
         'eligible_B_same_number_exit0','new_wait4_resolves_B','observed_B_normal0'],
        'An earlier successful lookup is not retained by a later syscall.')
counter('userspace wait-entering flag is not kernel wait entry',
        ['collector_stores_entering_flag','worker_sees_flag_and_runs','A_exit68','external_reap_A',
         'eligible_B_same_number_exit0','collector_syscall_resolves_B','observed_B_normal0'],
        'Storing a userspace flag before SVC does not prove find_get_pid has completed.')
counter('pre-release external kill defeats a mere release gate',
        ['A_waits_for_release','external_SIGKILL_A','external_reap_A','eligible_B_same_number_exit0',
         'collector_syscall_resolves_B','release_attempt_after_kernel_wait_entry','observed_B_normal0'],
        'The ordinary exit gate cannot prevent SIGKILL/reaping before the initial kernel lookup.')
counter('interrupted blocking wait loses its old reference',
        ['wait4_pins_A','signal_interrupt_returns_EINTR_put_pid_A','A_exit68','external_reap_A',
         'eligible_B_same_number_exit0','userspace_retry_resolves_B','observed_B_normal0'],
        'A new or restarted numeric wait requires a new identity argument; the first reference is gone.')

# Robust cleanup carries no exit code and happens before all descriptor cleanup.
# This is a declared lifecycle model linked to the separate static source audit.
robust=[]
for path,kind,code in [('SYS_exit0','normal',0),('SIGKILL_after_planned0','signal',9),('exec_new_image','still_alive',None)]:
    row=dict(path=path,own_shared_planned_exit=0,private_DONE_already_sent=True,owner_died_at_mm_release=True,
             descriptors_may_still_be_open_at_marker=True,kernel_final_kind=kind,kernel_final_code=code,
             naive_DONE_and_planned0_and_owner_died_accepts=True,
             exact_normal0_exit_proven_by_marker=False)
    robust.append(row)
assert robust[1]['naive_DONE_and_planned0_and_owner_died_accepts'] and robust[1]['kernel_final_kind']=='signal'
assert robust[2]['kernel_final_kind']=='still_alive'
clear_tid=[dict(mm_users=n,clear_child_tid_configured=True,not_core_dump=True,kernel_zeroes_word=n>1) for n in (1,2)]
assert not clear_tid[0]['kernel_zeroes_word'] and clear_tid[1]['kernel_zeroes_word']

receipt=dict(status='MODEL_PROPERTIES_PASS_WITH_EXPLICIT_REMAINING_COUNTEREXAMPLES',
    model_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
    object_identity='A and B are different simulated kernel objects with the same numeric pid',
    eligible_foreign_B_is_explicit_input_not_measured_camera_context=True,
    ungated_blocking_schedules=len(all_ungated),ungated_false_complete_count=len(bad),
    gated_ordinary_exit_schedules=len(all_gated),gated_ordinary_exit_false_complete_count=0,
    ungated_witness=bad[0],gated_ordinary_traces=all_gated,
    other_identity_counterexamples=counterexamples,robust_lifecycle_cases=robust,clear_child_tid_cases=clear_tid,
    finite_model_claims_only=True,proof_for_arbitrary_kernel_interleavings=False,
    prelookup_SIGKILL_or_interruption_solution_implemented=False,
    own_candidate_or_original_Linux_executed=False,actual_processes_or_threads_created=False,new_device_operations=0,
    stage235_candidate_changed_or_admission_failure_cleared=False,deployable=False,first_flash_released=False)
(H/'wait-reference-model-receipt.json').open('x').write(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status=receipt['status'],ungated_schedules=len(all_ungated),ungated_false_complete=len(bad),
                      gated_schedules=len(all_gated),additional_identity_counterexamples=len(counterexamples),
                      robust_lifecycle_cases=len(robust),clear_child_tid_cases=len(clear_tid))))
