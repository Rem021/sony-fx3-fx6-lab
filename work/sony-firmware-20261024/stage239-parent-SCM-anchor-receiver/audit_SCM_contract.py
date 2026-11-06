"""Read-only native SCM checks plus pinned v4.9.337 reference ranges."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage146-original-kernel-symbol-and-vendor-route/kernel_symbols.py'
assert sha256(P.read_bytes()).hexdigest()=='db8a1ebba52e8bfb85367e3d8450e1ef89224d0bb9e768bf656c6370600614a1'
s=importlib.util.spec_from_file_location('kernel239',P);S=importlib.util.module_from_spec(s);s.loader.exec_module(S);k=S.KernelSymbols();K=S.K;md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);checks=[]
def ck(n,x):assert x,n;checks.append(n)
def inst(a,m,o):
 i=list(md.disasm(k.raw[a:a+4],K+a));ck(hex(a)+' '+m+' '+o,len(i)==1 and i[0].mnemonic==m and i[0].op_str==o)
def bl(a,name):
 w=k.u32(a);imm=w&0x3ffffff
 if imm&(1<<25):imm-=1<<26
 ck(hex(a)+' raw BL '+name,w>>26==0b100101 and a+4*imm==k.unique(name)['file_offset']);inst(a,'bl','#'+hex(k.unique(name)['address']))
for number,name in [(25,'sys_fcntl'),(204,'sys_getsockname'),(209,'sys_getsockopt'),(211,'sys_sendmsg'),(212,'sys_recvmsg')]:ck('syscall '+str(number)+' '+name,k.u64(0x432000+8*number)==k.unique(name)['address'])
for a,m,o in [(0x330a60,'cmp','w0, #0xfd'),(0x330928,'mov','w1, #0x15'),
 (0x330d2c,'mov','w24, #0x80000'),(0x330d38,'ands','w0, w0, #0x40000000'),(0x330d3c,'csel','w0, w0, w24, eq'),
 (0x330f28,'add','x0, x0, #1'),(0x330f38,'add','w21, w21, #1'),(0x330f44,'cmp','w21, w23'),(0x330f4c,'b','#0xffffff80083b0d88'),
 (0x330dd0,'str','w4, [x2]'),(0x330e70,'str','x1, [x4]'),(0x330eac,'cmp','w25, w21'),(0x330eb0,'b.le','#0xffffff80083b0ec0'),(0x330eb8,'orr','w0, w0, #8')]:inst(a,m,o)
for a,n in [(0x330d40,'get_unused_fd_flags'),(0x330f40,'fd_install'),(0x330ec4,'__scm_destroy'),(0x330920,'task_active_pid_ns'),(0x33092c,'ns_capable'),(0x330aa4,'fget_raw')]:bl(a,n)
spans=[]
for n in ['scm_detach_fds','__scm_send','unix_dgram_recvmsg']:
 a,z=k.span(n);p=k.raw[a:z];ins=list(md.disasm(p,K+a));ck('complete next-symbol decode '+n,len(ins)*4==len(p))
 spans.append(dict(name=n,start=a,end=z,bytes=len(p),sha256=sha256(p).hexdigest(),bounds='next distinct kallsyms address, not ELF size',instructions=[dict(offset=i.address-K,word=k.raw[i.address-K:i.address-K+4].hex(),mnemonic=i.mnemonic,operands=i.op_str) for i in ins]))
(H/'original-SCM-spans.json').open('x').write(json.dumps(spans,indent=2)+'\n')
refs=H/'source-reference';specs=[(refs/'include__net__scm.h',10,26,['SCM_MAX_FD\t253','struct file']),
 (refs/'net__core__scm.c',47,65,['scm_check_creds','CAP_SYS_ADMIN','CAP_SETUID','CAP_SETGID']),
 (refs/'net__core__scm.c',72,95,['SCM_MAX_FD','count','max']),
 (refs/'net__core__scm.c',254,302,['MSG_CMSG_CLOEXEC','O_CLOEXEC','fd_install(new_fd, get_file(fp[i]))']),
 (refs/'net__core__scm.c',304,327,['put_user(SOL_SOCKET','put_user(cmlen','i < fdnum','MSG_CTRUNC','__scm_destroy']),
 (refs/'include__net__scm.h',112,138,['SOCK_PASSCRED','SCM_CREDENTIALS','scm_detach_fds'])]
ranges=[]
for p,a,z,t in specs:
 piece=''.join(p.read_text().splitlines(keepends=True)[a-1:z]);ck('source '+p.name+':'+str(a),all(x in piece for x in t));ranges.append(dict(path=str(p.relative_to(R)),sha256=sha256(p.read_bytes()).hexdigest(),first_line=a,last_line=z,range_sha256=sha256(piece.encode()).hexdigest(),required_tokens=t))
for x in json.loads((H/'source-capture.json').read_text()):ck('captured '+x['path'],x['status']=='CAPTURED' and sha256((H/x['path']).read_bytes()).hexdigest()==x['sha256'])
example=dict(fdnum=1,fdmax=1,installed_i=1,cmsg_header_copy_failed=True,CTRUNC_condition=(1<1 or (1 and 1<=0)),unidentified_installed_FDs_can_remain=True)
ck('all-installed/header-fault does not require CTRUNC in reference',not example['CTRUNC_condition'])
r=dict(status='SAVED_SCM_NATIVE_AND_REFERENCE_CONTRACT_PASS_NOT_RUNTIME_ACCEPTANCE',checks=len(checks),check_names=checks,
 original_kernel=str(S.KERNEL.relative_to(R)),original_kernel_sha256=S.KERNEL_SHA256,parser_sha256=sha256(P.read_bytes()).hexdigest(),source_ranges=ranges,
 reference='Linux v4.9.337, not rebuilt exact Sony source',rights_max=253,SCM_RIGHTS_references_same_file=True,CLOEXEC_flag_path_bound=True,
 header_fault_without_CTRUNC_arithmetic_example=example,partial_delivery_error_is_not_proven_all_FDs_closed=True,
 CAP_SYS_ADMIN_sender_can_supply_other_PID_in_reference=True,SCM_credentials_alone_are_not_authentic_child_creation_proof=True,
 observed_target_capabilities_or_copy_faults=False,original_code_executed=False,new_device_operations=0)
(H/'SCM-contract.json').open('x').write(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(status=r['status'],checks=len(checks),spans=len(spans),source_ranges=len(ranges))))
