from pathlib import Path
from hashlib import sha256
import json
H=Path(__file__).resolve().parent;R=H.parents[2];P=H.parent/'stage222-parent-arbiter-core-and-paired-ARM64'
changes=[
(' * process context. Does not fork, exec, install, authenticate or upload.',' * process context. Own clone/exec candidate; no install/auth/upload backend.'),
('#include "output_validate.inc"','#include "output_validate.inc"\n#include "launch_support.inc"'),
('if(fd!=199||!identity()||!im_profile()||!binding(hand,req,child)||owner.jobs>=1024){held(72);goto done;}','if(child!=0||fd!=-1||!identity()||!im_profile()||!launch_template(hand,req)||owner.jobs>=1024){held(72);goto done;}'),
('if(!reserve_session(hand)){held(73);goto done;}\n    copy(owner.gate.hand,hand,256);','if(!reserve_session(hand)){held(73);goto done;}\n    u8 final_hand[256];copy(final_hand,hand,256);\n    if(!launch_job(final_hand,req,&child,&fd)){held(86);goto done;}hand=final_hand;\n    if(!binding(hand,req,child)){held(87);goto done;}\n    copy(owner.gate.hand,hand,256);')]
s=(P/'parent_module.c').read_text()
for before,after in changes:assert s.count(before)==1;s=s.replace(before,after)
assert s==(H/'parent_module.c').read_text()
failed=[]
for folder in ['runs-first','runs-template-fixed','runs-model-fixed','runs-ABI-fixed']:
 d=json.loads((H/folder/'receipt/results.json').read_text());matching={}
 for n,digest in d['source_hashes'].items():
  choices=[H/folder/'source-snapshot'/n,H/folder/n,H/'runs-template-fixed/source-snapshot'/n,H/'runs-model-fixed/source-snapshot'/n,H/'runs-ABI-fixed/source-snapshot'/n,H/n]
  match=next(x for x in choices if x.is_file() and sha256(x.read_bytes()).hexdigest()==digest);matching[n]=dict(path=str(match.relative_to(R)),sha256=digest)
 failed.append(dict(receipt=str((H/folder/'receipt/results.json').relative_to(R)),status=d['status'],failures=d['failures'],errors=d['errors'],matching_sources=matching))
derived=dict(schema='fx3-stage224-launcher-source-derivation-v1',parent_source=str((P/'parent_module.c').relative_to(R)),parent_source_sha256=sha256((P/'parent_module.c').read_bytes()).hexdigest(),ordered_changes=[dict(before=a,after=b) for a,b in changes],parent_derived_sha256=sha256((H/'parent_module.c').read_bytes()).hexdigest(),unchanged_support={n:sha256((P/n).read_bytes()).hexdigest() for n in ['core_support.inc','parent_ipc.inc','output_validate.inc']},child_static_unchanged_sha256='e40d068d43123f8f86eba5c46a1428e02e5e16c84df2211174c578d4cd273d7d',failed_runs_preserved=failed,formal_release_modified=False)
(H/'source-derivation.json').open('x').write(json.dumps(derived,ensure_ascii=False,indent=2)+'\n')
u=H.parent/'stage221-private-IPC-entry-gate/kernel-reference/unistd.h';ul=u.read_text().splitlines();expected={61:196,68:213,199:555,220:605,221:607}
for n,line in expected.items():assert ul[line-1].startswith('#define __NR_') and ul[line-1].endswith(' '+str(n))
abi=dict(schema='fx3-stage224-own-launcher-ABI-reference-v1',unistd_source=str(u.relative_to(R)),unistd_sha256=sha256(u.read_bytes()).hexdigest(),syscall_number_lines={str(k):v for k,v in expected.items()},clone_flags=17,clone_VM_FILES_THREAD_flags=False,child_stack=0,exec_arguments=3,exec_unused_x3_x4_x5_are_not_validity_conditions=True,child_FD_table_changes_not_parent_FD_flags=True,real_kernel_clone_exec_credentials_signals_ELF_or_noexec_policy_verified=False,primary_manual_pages='web-source-capture.json')
(H/'kernel-and-link-ABI-review.json').open('x').write(json.dumps(abi,ensure_ascii=False,indent=2)+'\n')
print('Source derivation and four failed snapshots bound; five syscall constants checked.')
