"""Read-only original Image inspection; no original instructions are executed.

The stable source is reference material, not a reconstructed Sony build.
Each decoded span ends at the next DISTINCT kallsyms address, not an ELF size.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util, json, struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

H=Path(__file__).resolve().parent; B=H.parent; R=H.parents[2]
P=B/'stage146-original-kernel-symbol-and-vendor-route/kernel_symbols.py'
assert sha256(P.read_bytes()).hexdigest()=='db8a1ebba52e8bfb85367e3d8450e1ef89224d0bb9e768bf656c6370600614a1'
sp=importlib.util.spec_from_file_location('kernel236',P); S=importlib.util.module_from_spec(sp);sp.loader.exec_module(S)
k=S.KernelSymbols(); K=S.K; md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
checks=[]
def ck(name,ok):
    assert ok,name
    checks.append(name)
def dump(name,obj):
    data=json.dumps(obj,ensure_ascii=False,indent=2)+'\n';p=H/name
    if p.exists():assert p.read_text()==data,'existing artifact differs: '+name
    else:p.open('x').write(data)
def ins(off):
    a=list(md.disasm(k.raw[off:off+4],K+off)); assert len(a)==1
    return a[0]
def inst(off,mnemonic,operands=None):
    x=ins(off);ck(hex(off)+' '+mnemonic,x.mnemonic==mnemonic and (operands is None or x.op_str==operands));return x
def bl(off,name):
    w=k.u32(off);ck(hex(off)+' raw BL encoding',w>>26==0b100101)
    imm=w&0x3ffffff
    if imm&(1<<25):imm-=1<<26
    target=off+4*imm;expected=k.unique(name)['file_offset']
    ck(hex(off)+' BL '+name,target==expected)
    inst(off,'bl',hex(K+expected).join(['#','']))
    return dict(offset=off,raw_word=hex(w),target=name,target_offset=target)

saved=json.loads((P.parent/'work/kernel-symbol-catalog.json').read_text())
ck('all decoded symbols equal sealed146 catalog',k.rows==saved)
ck('symbol count',len(k.rows)==41269)
ck('official Image SHA',sha256(k.raw).hexdigest()==S.KERNEL_SHA256)
names=['sys_wait4','sys_waitid','find_get_pid','put_pid','do_wait','wait_consider_task',
       'sys_set_tid_address','sys_set_robust_list','sys_get_robust_list','sys_futex',
       'mm_release','exit_mm_release','exec_mm_release','futex_cleanup',
       'futex_exit_release','futex_exec_release','handle_futex_death','do_exit']
spans=[]
for name in names:
    a,z=k.span(name);raw=k.raw[a:z]
    spans.append(dict(name=name,start=a,end=z,bytes=len(raw),sha256=sha256(raw).hexdigest(),
                      bound='next distinct kallsyms address, not ELF function-size metadata',
                      instructions=[dict(offset=x.address-K,word=k.raw[x.address-K:x.address-K+4].hex(),
                                         mnemonic=x.mnemonic,operands=x.op_str) for x in md.disasm(raw,K+a)]))
dump('original-selected-spans.json',spans)

# Native dispatch: the table has padding after its valid entries. Do not infer
# the syscall count from the next symbol's address or from a generic header.
inst(0x2740,'adrp','x27, #0xffffff80084b2000')
inst(0x2744,'mov','w26, w8');inst(0x2748,'mov','x25, #0x123')
inst(0x2760,'cmp','x26, x25');inst(0x2764,'b.hs','#0xffffff80080827a8')
inst(0x2790,'ldr','x16, [x27, x26, lsl #3]');inst(0x2794,'blr','x16')
ck('sys_call_table address',k.unique('sys_call_table')['file_offset']==0x432000)
ck('normal pidfd_open number434 exceeds native291',434>=291)
ck('no pidfd names in entire saved catalog',not [r for r in k.rows if 'pidfd' in r['name']])
table=[]
for n,name in [(93,'sys_exit'),(94,'sys_exit_group'),(95,'sys_waitid'),(96,'sys_set_tid_address'),
               (98,'sys_futex'),(99,'sys_set_robust_list'),(100,'sys_get_robust_list'),
               (220,'sys_clone'),(260,'sys_wait4')]:
    ptr=k.u64(0x432000+n*8);ck('syscall '+str(n)+' '+name,ptr==k.unique(name)['address'])
    table.append(dict(number=n,name=name,pointer=hex(ptr),offset=ptr-K))
# waitid selector3 follows the native EINVAL branch; unrelated argument failures
# can of course reject earlier. No system call is made here.
for a,m,o in [(0x24964,'cmp','w0, #1'),(0x24974,'b.eq','#0xffffff80080a4c18'),
              (0x24978,'cmp','w0, #2'),(0x2497c,'b.eq','#0xffffff80080a49a0'),
              (0x24980,'cbz','w0, #0xffffff80080a4a00'),(0x24984,'mov','x19, #-0x16')]:inst(a,m,o)

calls=[bl(0x24c74,'find_get_pid'),bl(0x24c94,'do_wait'),bl(0x24ca0,'put_pid')]
inst(0x24c78,'mov','x22, x0');inst(0x24c8c,'stp','x22, xzr, [x29, #0x40]')
inst(0x24c9c,'mov','x0, x22')
for a,m,o in [(0x3a518,'ldxr','w0, [x19]'),(0x3a51c,'add','w0, w0, #1'),
              (0x3a520,'stxr','w1, w0, [x19]'),(0x3a524,'cbnz','w1, #0xffffff80080ba518')]:inst(a,m,o)
for a,m,o in [(0x2396c,'ldr','x3, [x20, #8]'),(0x23978,'ldr','x0, [x0, #0x3f8]'),
              (0x2397c,'cmp','x0, x3'),(0x23980,'b.eq','#0xffffff80080a39a8'),
              (0x23984,'mov','w21, #0')]:inst(a,m,o)
for a,name in [(0x1e02c,'futex_exit_release'),(0x1e038,'mm_release'),
               (0x1e05c,'futex_exec_release'),(0x1e068,'mm_release'),
               (0x8ea28,'futex_cleanup'),(0x8e9c8,'futex_cleanup'),
               (0x2301c,'exit_mm_release'),(0x23528,'exit_mm_release'),
               (0x23188,'exit_files'),(0x23544,'exit_files'),(0x2357c,'exit_files')]:calls.append(bl(a,name))
inst(0x8e7c8,'cmp','x1, #0x18')

# Bind exact downloaded source bytes and selected explanatory ranges.
captures=json.loads((H/'stable-source-capture.json').read_text())+[json.loads((H/'pid-source-capture.json').read_text())]
for row in captures:
    p=H/row['path'];ck('source pin '+p.name,len(p.read_bytes())==row['bytes'] and sha256(p.read_bytes()).hexdigest()==row['sha256'])
source_specs=[
 ('exit.c',955,966,['task->pids[type].pid','task_pid_type(p, wo->wo_type) == wo->wo_pid']),
 ('exit.c',1510,1565,['WNOHANG','schedule();','__WNOTHREAD']),
 ('exit.c',1631,1670,['find_get_pid(upid)','ret = do_wait(&wo)','put_pid(pid)']),
 ('exit.c',803,828,['tsk->exit_code = code','exit_mm(tsk)','exit_files(tsk)']),
 ('fork.c',1085,1130,['mm_users) > 1','futex_exit_release(tsk)','futex_exec_release(tsk)']),
 ('futex.c',3590,3655,['FUTEX_OWNER_DIED','task_pid_vnr(curr)','cmpxchg_futex_value_locked']),
 ('futex.c',3827,3851,['futex_exec_release','futex_exit_release','futex_cleanup(tsk)']),
 ('pid.h',76,85,['atomic_inc(&pid->count)','put_pid']),
 ('pid.c',250,299,['free_pid','free_pidmap','call_rcu']),
 ('pid.c',486,501,['find_get_pid','get_pid(find_vpid(nr))'])]
ranges=[]
for name,a,z,tokens in source_specs:
    p=H/'source-reference'/name;piece=''.join(p.read_text().splitlines(keepends=True)[a-1:z])
    ck('source range '+name+':'+str(a),all(t in piece for t in tokens))
    ranges.append(dict(path=str(p.relative_to(R)),sha256=sha256(p.read_bytes()).hexdigest(),first_line=a,last_line=z,
                       range_sha256=sha256(piece.encode()).hexdigest(),required_tokens=tokens))
dump('kernel-interface-audit.json',dict(status='STATIC_CHECKS_PASS_NOT_RUNTIME_ACCEPTANCE',checks=len(checks),check_names=checks,
    original_kernel=str(S.KERNEL.relative_to(R)),original_kernel_sha256=S.KERNEL_SHA256,
    parser=str(P.relative_to(R)),parser_sha256=sha256(P.read_bytes()).hexdigest(),catalog_symbols=len(k.rows),
    syscall_table=table,native_syscall_count=291,standard_pidfd_open_434_is_out_of_dispatch_range=True,
    waitid_selector3_rejected_by_saved_native_code=True,absence_of_all_vendor_custom_equivalents_proven=False,
    blocking_wait_holds_one_struct_pid_reference_only_until_that_call_returns=True,
    repeated_WNOHANG_calls_do_not_keep_that_reference=True,
    selected_native_calls=calls,source_ranges=ranges,
    stable_reference='Linux v4.9.337; not proof of exact Sony source/configuration or live loaded Image',
    early_futex_cleanup_is_exact_exit_status_or_all_FDs_closed=False,
    clear_child_tid_not_guaranteed_for_private_single_user_mm=True,
    kernel_wait_entry_before_worker_release_barrier_implemented=False,
    pre_lookup_external_child_death_and_reaping_still_requires_solution=True,
    source_reads_only=True,original_kernel_or_Sony_code_executed=False,new_device_operations=0))
print(json.dumps(dict(status='STATIC_CHECKS_PASS',checks=len(checks),spans=len(spans),source_ranges=len(ranges))))
