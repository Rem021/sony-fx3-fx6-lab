"""Small source-derived parent graph model, not a kernel simulator.
No foreign process can choose an arbitrary parent via clone0/CLONE_PARENT.
The boundary remains code integrity: an extra collector child can create more
siblings; this model does not turn a preflight snapshot into that integrity.
"""
from pathlib import Path
from hashlib import sha256
import json
H=Path(__file__).resolve().parent
parents={1:None,321:1,5001:321,7002:5001,9000:321}
subreapers={321}
def clone_parent(issuer,shared_parent=False):return parents[issuer] if shared_parent else issuer
def adopt(orphan_parent):
 p=parents[orphan_parent]
 while p is not None:
  if p in subreapers:return p
  p=parents[p]
 return 1
rows=[]
for phase in ['worker-alive','worker-exited-not-reaped','worker-reaped-number-reusable']:
 for issuer in [321,9000]:
  for shared in [False,True]:
   parent=clone_parent(issuer,shared);assert parent!=5001
   rows.append(dict(phase=phase,foreign_issuer=issuer,clone_parent_flag=shared,new_parent=parent,
                    matches_collector_child_domain=False,same_numeric_worker_pid_allocatable=phase=='worker-reaped-number-reusable'))
for dead in [321,9000]:
 target=adopt(dead);assert target!=5001
 rows.append(dict(event='foreign parent dies',dead_parent=dead,adopted_by=target,matches_collector_child_domain=False))
# A worker allowed to create a CLONE_PARENT child makes an extra sibling.
# That sibling could later create another sibling after the worker pid is
# freed. Our NOOP contains no such call; future full worker must preserve it.
extra_parent=clone_parent(7002,True);assert extra_parent==5001
boundary=dict(worker_issues_unexpected_CLONE_PARENT=True,extra_sibling_parent=extra_parent,
              extra_sibling_can_later_create_more_siblings=True,closed_domain_broken=True,
              old_worker_pid_can_eventually_be_reused_by_such_a_sibling=True,
              current_NOOP_source_or_trace_performs_this=False)
r=dict(status='FINITE_SOURCE_DERIVED_GRAPH_CHECKS_PASS_WITH_CODE_INTEGRITY_PRECONDITION',cases=rows,
       code_integrity_boundary=boundary,collector_single_thread_and_not_namespace_init_required=True,
       not_a_proof_of_actual_target_process_tree=True,real_outer_bootstrap_unverified=True,
       source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),original_code_executed=False,new_device_operations=0)
(H/'topology-law-receipt.json').open('x').write(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(status=r['status'],graph_cases=len(rows))))
