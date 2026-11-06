"""Generate address candidates only; linear scan is not a control-flow proof."""
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN,CS_OP_REG,CS_OP_IMM,CS_OP_MEM
import json
H=Path(__file__).resolve().parent;B=H.parent;P=B/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin';d=P.read_bytes();BASE=0xfe049000
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.detail=True
known={};origins={};hits=[]
def key(name):return 'x'+name[1:] if name.startswith('w') else name
def val(reg):
 name=md.reg_name(reg)
 if name in ['wzr','xzr']:return 0
 v=known.get(key(name));return None if v is None else (v&0xffffffff if name.startswith('w') else v)
for off in range(0,len(d)-4,4):
 seq=list(md.disasm(d[off:off+4],BASE+off))
 if not seq:known.clear();continue
 i=seq[0];ops=i.operands;m=i.mnemonic
 if m.startswith(('str','stur','stp')):
  for op in ops:
   if op.type!=CS_OP_MEM:continue
   address=val(op.mem.base)
   if address is None:continue
   address+=op.mem.disp
   if op.mem.index:
    index=val(op.mem.index)
    if index is None:continue
    address+=index
   if 0xfe0625b0<=address<0xfe062600:
    hits.append(dict(kind='store',instruction=hex(i.address),mnemonic=m,operands=i.op_str,address=hex(address),source_register_values=[val(o.reg) for o in ops if o.type==CS_OP_REG],base_origin=origins.get(key(md.reg_name(op.mem.base)))))
 if m=='bl':
  args={f'x{n}':known.get(f'x{n}') for n in range(4)}
  if any(v is not None and 0xfe0625b0<=v<0xfe062600 for v in args.values()):hits.append(dict(kind='call_with_target_pointer',instruction=hex(i.address),target=i.op_str,args={n:(hex(v) if v is not None else None) for n,v in args.items()}))
 new=None;dst=None
 if ops and ops[0].type==CS_OP_REG:
  dst=key(md.reg_name(ops[0].reg))
  if m in ['adrp','adr'] and len(ops)==2 and ops[1].type==CS_OP_IMM:new=ops[1].imm
  elif m=='mov' and len(ops)==2:new=ops[1].imm if ops[1].type==CS_OP_IMM else (val(ops[1].reg) if ops[1].type==CS_OP_REG else None)
  elif m=='movk' and len(ops)>=2 and dst in known:
   shift=ops[1].shift.value;new=(known[dst]&~(65535<<shift))|((ops[1].imm&65535)<<shift)
  elif m in ['add','sub'] and len(ops)>=3 and ops[1].type==CS_OP_REG:
   a=val(ops[1].reg);b=ops[2].imm if ops[2].type==CS_OP_IMM else (val(ops[2].reg) if ops[2].type==CS_OP_REG else None)
   if a is not None and b is not None:new=a+((-b if m=='sub' else b)<<ops[2].shift.value)
 reads,writes=i.regs_access()
 for reg in writes:known.pop(key(md.reg_name(reg)),None);origins.pop(key(md.reg_name(reg)),None)
 if dst and new is not None:
  name=md.reg_name(ops[0].reg);known[dst]=new&((1<<32)-1 if name.startswith('w') else (1<<64)-1);origins[dst]=hex(i.address)
 if m=='bl':
  for n in range(19):known.pop(f'x{n}',None);origins.pop(f'x{n}',None)
(H/'configuration-writer-candidates.json').open('x').write(json.dumps(dict(source=str(P),candidate_only=True,normal_ABI_call_clobber_assumption=True,not_a_complete_control_flow_or_alias_proof=True,hits=hits),indent=2)+'\n')
print(json.dumps(hits,indent=2))
