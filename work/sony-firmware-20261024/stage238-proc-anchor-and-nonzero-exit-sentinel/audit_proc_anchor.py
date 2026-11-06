"""Static saved-Image/proc reference audit; never run original instructions."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage146-original-kernel-symbol-and-vendor-route/kernel_symbols.py'
assert sha256(P.read_bytes()).hexdigest()=='db8a1ebba52e8bfb85367e3d8450e1ef89224d0bb9e768bf656c6370600614a1'
s=importlib.util.spec_from_file_location('kernel238',P);S=importlib.util.module_from_spec(s);s.loader.exec_module(S);k=S.KernelSymbols();K=S.K;md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);checks=[]
def ck(n,x):assert x,n;checks.append(n)
def inst(a,m,o):
 i=list(md.disasm(k.raw[a:a+4],K+a));ck(hex(a)+' '+m+' '+o,len(i)==1 and i[0].mnemonic==m and i[0].op_str==o)
def bl(a,name):
 w=k.u32(a);imm=w&0x3ffffff
 if imm&(1<<25):imm-=1<<26
 ck(hex(a)+' raw BL '+name,w>>26==0b100101 and a+4*imm==k.unique(name)['file_offset']);inst(a,'bl','#'+hex(k.unique(name)['address']))
for a,m,o in [(0x163204,'mov','w1, #0'),(0x163214,'stur','x0, [x19, #-0x48]'),
 (0x16392c,'mov','w1, #0'),(0x163934,'ldur','x0, [x0, #-0x48]'),
 (0x160600,'ldur','x22, [x20, #-0x48]'),(0x160608,'mov','x0, x22'),(0x160614,'cbz','x0, #0xffffff80081e0680'),
 (0x15fd58,'ldur','x0, [x19, #-0x48]'),(0x165a58,'mov','w1, #0xd'),(0x165a64,'uxtb','w22, w0'),
 (0x16619c,'cbnz','w22, #0xffffff80081e6078'),(0x166078,'ldrsw','x2, [x20, #0x328]'),
 (0x1661ac,'bl','#0xffffff80081b1b38'),(0x23390,'mov','w0, #0x20'),(0x23394,'str','w0, [x19, #0x324]'),
 (0x23638,'mov','w0, #0x10'),(0x2363c,'str','w0, [x19, #0x324]')]:inst(a,m,o)
for a,n in [(0x163210,'get_task_pid'),(0x163938,'get_pid_task'),(0x160610,'get_pid_task'),(0x15fd5c,'put_pid'),
             (0x165a60,'ptrace_may_access'),(0x166084,'seq_put_decimal_ll'),(0x1661ac,'seq_puts'),(0x166edc,'do_task_stat')]:bl(a,n)
ck('filtered exit-code fallback string is exact zero',k.raw[0x533ad8:0x533adb]==b' 0\0')
ck('fixed success sentinel cannot equal filtered zero',42<<8==10752 and 10752!=0)
spans=[]
for n in ['proc_pid_make_inode','proc_pident_lookup','proc_single_show','proc_evict_inode','do_task_stat','proc_tgid_stat','do_exit']:
 a,z=k.span(n);raw=k.raw[a:z];ins=list(md.disasm(raw,K+a));ck('complete next-symbol decode '+n,len(ins)*4==len(raw))
 spans.append(dict(name=n,start=a,end=z,bytes=len(raw),sha256=sha256(raw).hexdigest(),bounds='next distinct symbol, not ELF function size',instructions=[dict(offset=i.address-K,word=k.raw[i.address-K:i.address-K+4].hex(),mnemonic=i.mnemonic,operands=i.op_str) for i in ins]))
(H/'original-proc-object-spans.json').open('x').write(json.dumps(spans,indent=2)+'\n')
refs=H/'source-reference';array=B/'stage237-isolated-collector-child-domain/source-reference/fs__proc__array.c';old=B/'stage236-kernel-unique-exit-interface-audit/source-reference'
specs=[(refs/'fs__proc__base.c',1679,1705,['ei->pid = get_task_pid(task, PIDTYPE_PID)']),
 (refs/'fs__proc__base.c',2431,2449,['get_proc_task(dir)','error = -ENOENT','if (!task)']),
 (refs/'fs__proc__base.c',770,790,['get_pid_task(pid, PIDTYPE_PID)','return -ESRCH','put_task_struct(task)']),
 (refs/'fs__proc__inode.c',31,41,['put_pid(PROC_I(inode)->pid)']),
 (refs/'fs__proc__internal.h',90,100,['return PROC_I(inode)->pid','get_pid_task(proc_pid(inode), PIDTYPE_PID)']),
 (refs/'fs__proc__self.c',9,19,['task_tgid_nr_ns(current, ns)','sprintf(tmp, "%d", tgid)']),
 (array,118,145,['Z (zombie)','tsk->state | tsk->exit_state']),
 (array,432,440,['state = *get_task_state(task)','ptrace_may_access(task, PTRACE_MODE_READ_FSCREDS | PTRACE_MODE_NOAUDIT)']),
 (array,592,604,['if (permitted)','task->exit_code','seq_puts(m, " 0")']),
 (old/'pid.c',250,299,['free_pidmap','call_rcu','put_pid(pid)']),
 (old/'exit.c',686,703,['do_notify_parent','autoreap ? EXIT_DEAD : EXIT_ZOMBIE']),
 (old/'exit.c',810,848,['tsk->exit_code = code','exit_files(tsk)','exit_notify(tsk, group_dead)'])]
ranges=[]
for p,a,z,t in specs:
 piece=''.join(p.read_text().splitlines(keepends=True)[a-1:z]);ck('source range '+p.name+':'+str(a),all(x in piece for x in t));ranges.append(dict(path=str(p.relative_to(R)),sha256=sha256(p.read_bytes()).hexdigest(),first_line=a,last_line=z,range_sha256=sha256(piece.encode()).hexdigest(),required_tokens=t))
capture=json.loads((H/'source-capture.json').read_text())+[json.loads((H/'self-source-capture.json').read_text())]
for x in capture:ck('captured '+x['path'],x['status']=='CAPTURED' and sha256((H/x['path']).read_bytes()).hexdigest()==x['sha256'])
r=dict(status='SAVED_PROC_OBJECT_AND_NONZERO_FILTER_CONTRACT_FIXED_NOT_TARGET_ACCEPTANCE',checks=len(checks),check_names=checks,
 original_kernel=str(S.KERNEL.relative_to(R)),original_kernel_sha256=S.KERNEL_SHA256,parser_sha256=sha256(P.read_bytes()).hexdigest(),source_ranges=ranges,
 raw_filtered_exit_status_zero_can_look_like_normal0=True,nonzero_sentinel=10752,proc_inode_holds_struct_pid_reference=True,
 proc_lookup_and_read_use_that_object_not_fresh_numeric_pid=True,reference='Linux v4.9.337, not full rebuilt Sony source',
 native_EXIT_ZOMBIE_value=32,native_EXIT_DEAD_value=16,reference_exit_files_precedes_exit_notify=True,
 complete_native_all_path_exit_files_dominance_proven=False,proc_PID_detachment_is_all_kernel_post_exit_cleanup_complete=False,
 native_parent_SCM_receiver_and_authentic_entry_binding_proven=False,original_code_executed=False,new_device_operations=0)
(H/'proc-anchor-contract.json').open('x').write(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(status=r['status'],checks=len(checks),spans=len(spans),source_ranges=len(ranges))))
