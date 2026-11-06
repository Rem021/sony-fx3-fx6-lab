"""MOVK-aware static address candidates. Not an execution/reachability proof."""
from pathlib import Path
from hashlib import sha256
import json
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from capstone.arm64 import ARM64_OP_IMM,ARM64_OP_REG,ARM64_OP_MEM
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;VA=0xfe049000
SRC=BASE/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin'
d=SRC.read_bytes();assert sha256(d).hexdigest()=='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
c=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);c.detail=True
def reg(r):
 s=c.reg_name(r);return 'x'+s[1:] if s.startswith('w') else s
known={};refs=[];last=None
targets={'ready_byte':0xfe06216a,'partition_word':0xfe0620f8,'external_word':0xfe170028}
for off in range(0,len(d)-3,4):
 items=list(c.disasm(d[off:off+4],VA+off,count=1))
 if not items:known.clear();continue
 i=items[0];ops=i.operands;old=known.copy();new={}
 def val(o):
  if o.type==ARM64_OP_IMM:return o.imm
  if o.type==ARM64_OP_REG:
   if c.reg_name(o.reg) in ('xzr','wzr'):return 0
   return old.get(reg(o.reg))
  return None
 for m in [o for o in ops if o.type==ARM64_OP_MEM]:
  if reg(m.mem.base) not in old or m.mem.index:continue
  address=old[reg(m.mem.base)]+m.mem.disp
  width=1 if i.mnemonic.endswith(('b','sb')) else 2 if i.mnemonic.endswith(('h','sh')) else 4 if c.reg_name(ops[0].reg).startswith('w') else 8
  if i.mnemonic in ('stp','ldp'):width*=2
  for name,target in targets.items():
   if address<=target<address+width:
    refs.append({'site':hex(i.address),'target':name,'access_start':hex(address),'bytes':width,'instruction':i.mnemonic+' '+i.op_str,
      'kind':'store_candidate' if i.mnemonic.startswith(('st','str')) else 'load_candidate','value':hex(val(ops[0])) if val(ops[0]) is not None else None})
 if ops and ops[0].type==ARM64_OP_REG:
  key=reg(ops[0].reg);width=32 if c.reg_name(ops[0].reg).startswith('w') else 64;mask=(1<<width)-1
  if i.mnemonic in ('adr','adrp') and len(ops)==2:new[key]=ops[1].imm
  elif i.mnemonic=='mov' and len(ops)==2 and val(ops[1]) is not None:new[key]=val(ops[1])&mask
  elif i.mnemonic=='movk' and key in old:
   shift=ops[1].shift.value;new[key]=((old[key]&~(65535<<shift))|(ops[1].imm<<shift))&mask
  elif i.mnemonic in ('add','sub') and len(ops)==3 and val(ops[1]) is not None and ops[2].type==ARM64_OP_IMM:
   n=ops[2].imm<<ops[2].shift.value;new[key]=(val(ops[1])+(n if i.mnemonic=='add' else -n))&mask
 for r in i.regs_access()[1]:known.pop(reg(r),None)
 known.update(new)
 if i.mnemonic=='bl':
  for n in range(19):known.pop('x'+str(n),None)
 elif i.mnemonic in ('ret','br','b'):known.clear()
with (HERE/'word-reference-candidates.json').open('x') as f:json.dump({'source':str(SRC),'sha256':sha256(d).hexdigest(),'scope':'static local candidates including data; no full CFG/alias or reachability completeness claim','targets':{k:hex(v) for k,v in targets.items()},'refs':refs},f,indent=2);f.write('\n')
print(json.dumps(refs))
