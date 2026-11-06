"""Read saved native process/PRCTL paths and bind stable reference ranges."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,struct
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage146-original-kernel-symbol-and-vendor-route/kernel_symbols.py'
assert sha256(P.read_bytes()).hexdigest()=='db8a1ebba52e8bfb85367e3d8450e1ef89224d0bb9e768bf656c6370600614a1'
s=importlib.util.spec_from_file_location('kernel237',P);S=importlib.util.module_from_spec(s);s.loader.exec_module(S);k=S.KernelSymbols();K=S.K;md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);checks=[]
def ck(name,condition):assert condition,name;checks.append(name)
def inst(a,m,o):
 i=list(md.disasm(k.raw[a:a+4],K+a));ck(hex(a)+' '+m+' '+o,len(i)==1 and i[0].mnemonic==m and i[0].op_str==o)
def bl(a,name):
 w=k.u32(a);imm=w&0x3ffffff
 if imm&(1<<25):imm-=1<<26
 ck(hex(a)+' raw call '+name,w>>26==0b100101 and a+4*imm==k.unique(name)['file_offset'])
 inst(a,'bl','#'+hex(k.unique(name)['address']))

ck('prctl number167 points to saved native implementation',k.u64(0x432000+8*167)==k.unique('sys_prctl')['address'])
inst(0x32ea0,'sub','w19, w19, #1');inst(0x32ec0,'adrp','x0, #0xffffff80084b7000');inst(0x32ec4,'add','x0, x0, #0xd04');inst(0x32ec8,'ldrh','w0, [x0, w19, uxtw #1]');inst(0x32ecc,'adr','x3, #0xffffff80080b2ed8');inst(0x32ed0,'add','x0, x3, w0, sxth #2')
branches=[]
for option,pc in [(37,0x330fc),(36,0x33200)]:
 off=0x437d04+2*(option-1);signed=struct.unpack_from('<h',k.raw,off)[0];ck('prctl option '+str(option)+' branch',0x32ed8+4*signed==pc);branches.append(dict(option=option,table_offset=off,signed_entry=signed,target=pc))
for a,m,o in [(0x33138,'ldr','x1, [x24, #0x580]'),(0x33140,'ldrb','w1, [x1, #0x70]'),(0x33144,'and','w1, w1, #1'),(0x33148,'str','w1, [x2]'),
              (0x1e404,'add','x0, x25, #0x3a0'),(0x1e408,'str','x0, [x25, #0x3a0]'),(0x1e40c,'str','x0, [x0, #8]'),
              (0x1e86c,'mov','w1, #0x80c0'),(0x1e870,'movk','w1, #0x240, lsl #16'),(0x1e880,'str','x0, [x25, #0x580]'),
              (0x1e88c,'mov','w4, #1'),(0x1e89c,'str','w4, [x26, #4]'),(0x1e9e0,'ldrb','w0, [x26, #0x70]'),(0x1e9f0,'bfi','w0, w3, #1, #1'),(0x1e9f8,'strb','w0, [x26, #0x70]'),
              (0x103bb0,'and','w20, w1, w3'),(0x103bf8,'tbnz','w20, #0xf, #0xffffff8008183c38'),(0x103c44,'mov','w1, #0'),
              (0x1f12c,'tst','x28, #0x18000'),(0x1f130,'b.eq','#0xffffff800809f4e8'),(0x1f138,'ldr','x0, [x0, #0x390]'),(0x1f13c,'str','x0, [x25, #0x390]'),(0x1f4ec,'str','x0, [x25, #0x390]')]:inst(a,m,o)
bl(0x1e87c,'kmem_cache_alloc');bl(0x103c48,'memset')
spans=[]
for name in ['copy_process.isra.9.part.10','sys_prctl','kmem_cache_alloc']:
 a,z=k.span(name);p=k.raw[a:z];ins=list(md.disasm(p,K+a));ck('complete next-symbol decode '+name,len(ins)*4==len(p))
 spans.append(dict(name=name,start=a,end=z,bytes=len(p),sha256=sha256(p).hexdigest(),bounds='next distinct kallsyms symbol, not ELF size',
                   instructions=[dict(offset=i.address-K,word=k.raw[i.address-K:i.address-K+4].hex(),mnemonic=i.mnemonic,operands=i.op_str) for i in ins]))
(H/'original-process-domain-spans.json').open('x').write(json.dumps(spans,indent=2)+'\n')
refs=H/'source-reference';old=B/'stage236-kernel-unique-exit-interface-audit/source-reference'
specs=[(old/'fork.c',1341,1390,['CLONE_THREAD','kmem_cache_zalloc','sig->nr_threads = 1','has_child_subreaper']),
       (old/'fork.c',1569,1583,['INIT_LIST_HEAD(&p->children)','INIT_LIST_HEAD(&p->sibling)']),
       (old/'fork.c',1771,1784,['CLONE_PARENT|CLONE_THREAD','p->real_parent = current->real_parent','p->real_parent = current;']),
       (old/'exit.c',579,615,['find_alive_thread','is_child_subreaper','return child_reaper']),
       (refs/'kernel__sys.c',2228,2235,['PR_GET_CHILD_SUBREAPER','put_user(me->signal->is_child_subreaper']),
       (refs/'include__uapi__linux__prctl.h',157,158,['PR_SET_CHILD_SUBREAPER\t36','PR_GET_CHILD_SUBREAPER\t37']),
       (refs/'include__linux__sched.h',703,714,['is_child_subreaper:1','has_child_subreaper:1']),
       (refs/'fs__proc__array.c',180,201,['TracerPid:','Pid:','PPid:']),
       (refs/'fs__proc__array.c',280,304,['num_threads = get_nr_threads(p)','Threads:']),
       (refs/'include__linux__sched.h',3064,3068,['get_nr_threads','signal->nr_threads'])]
ranges=[]
for p,a,z,t in specs:
 piece=''.join(p.read_text().splitlines(keepends=True)[a-1:z]);ck('source range '+p.name+':'+str(a),all(x in piece for x in t))
 ranges.append(dict(path=str(p.relative_to(R)),sha256=sha256(p.read_bytes()).hexdigest(),first_line=a,last_line=z,range_sha256=sha256(piece.encode()).hexdigest(),required_tokens=t))
for row in json.loads((H/'source-capture.json').read_text()):
 p=H/row['path'];ck('captured source '+p.name,row['status']=='CAPTURED' and sha256(p.read_bytes()).hexdigest()==row['sha256'])
r=dict(status='SAVED_NATIVE_AND_REFERENCE_CONTRACT_PASS_NOT_RUNTIME_ACCEPTANCE',checks=len(checks),check_names=checks,
    original_kernel=str(S.KERNEL.relative_to(R)),original_kernel_sha256=S.KERNEL_SHA256,parser_sha256=sha256(P.read_bytes()).hexdigest(),
    prctl_dispatch_branches=branches,source_ranges=ranges,reference='Linux v4.9.337, not reconstructed exact Sony build',
    clone0_private_child_list_new_signal_and_non_subreaper_contract_supported=True,
    allocator_zeroing_path_identified_but_live_allowed_GFP_mask_unmeasured=True,
    own_core_also_queries_non_subreaper_and_rejects_failure=True,
    real_entry_creation_and_signal_mask_precondition_proven=False,
    collector_exit_binding_to_outer_service_parent_proven=False,
    original_kernel_or_Sony_code_executed=False,new_device_operations=0)
(H/'private-domain-contract.json').open('x').write(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(status=r['status'],checks=len(checks),spans=len(spans),source_ranges=len(ranges))))
