from pathlib import Path
import json,re,subprocess,struct,hashlib
H=Path(__file__).resolve().parent;B=H.parent
ns={'__file__':str(B/'analyze.py')};exec((B/'analyze.py').read_text().split('E={k:ELF')[0],ns)
E={k:ns['ELF'](p) for k,p in ns['P'].items()}
rows=json.loads((H/'matrix.json').read_text())
def excerpt(k,a,z,name):
 t=subprocess.check_output(['xcrun','llvm-objdump','-d',f'--start-address={a}',f'--stop-address={z}',str(ns['P'][k])],text=True);(H/name).write_text(t);return t
extra={}
for k,a,z,n in [('fx3_mpr',0xb442c,0xb4b40,'fx3-dispatch'),('fx3_mpr',0xb3a78,0xb3b10,'fx3-event-diagnostic'),('fx3_mpr',0x11975c,0x119a00,'fx3-u16-next-consumer')]:
 excerpt(k,a,z,n+'.txt');extra[n]={'entry':E[k].mapping(a),'end':hex(z)}
for r in rows:
 for k,p in r['callbacks'].items():
  if not p:continue
  t=(H/p['excerpt']).read_text().splitlines();nexts=[c['callbacks'][k]['target'] for c in rows if c['callbacks'][k] and c['callbacks'][k]['target']>p['target']];end=min(nexts,default=p['target']+384)
  out=[]
  for line in t:
   m=re.match(r'\s*([0-9a-f]+):',line)
   if m and int(m[1],16)>=end:break
   out.append(line)
   if re.search(r'\bret\b',line):break
   if re.search(r'\bb\s+0x',line) and any('ldp\tx29, x30' in x for x in out[-4:]):break
  (H/p['excerpt']).write_text('\n'.join(out)+'\n')
  p['extent_note']='bounded excerpt stops at RET, restored-frame tail branch, next known callback, or 384 bytes; not whole-function proof'
  # Conservative register alias observations within first basic block; saved input aliases survive calls.
  aliases={'x0':0};reads=[];writes=[]
  for line in out:
   m=re.match(r'\s*([0-9a-f]+):\s+[0-9a-f]+\s+(\S+)\s*(.*)',line)
   if not m:continue
   va=int(m[1],16);op=m[2];args=m[3].split('//')[0].strip()
   if op in ('bl','blr'):
    aliases={k:v for k,v in aliases.items() if int(k[1:])>=19};continue
   if op in ('b','br','ret') or op.startswith('b.') or op in ('cbz','cbnz','tbz','tbnz'):break
   q=re.match(r'(x\d+), (x\d+)$',args)
   if op=='mov' and q:
    if q[2] in aliases:aliases[q[1]]=aliases[q[2]]
    else:aliases.pop(q[1],None)
    continue
   q=re.search(r'\[(x\d+)(?:, #(0x[0-9a-f]+))?\]',args)
   if q and q[1] in aliases and op.startswith(('ldr','ldur','str','stur')):
    item={'offset':hex(aliases[q[1]]+int(q[2] or '0',16)),'instruction':E[k].mapping(va),'text':line};(reads if op.startswith('ld') else writes).append(item)
   dest=args.split(',')[0]
   if op.startswith(('ldr','ldur','adr','add','sub','mov')) and dest.startswith('x'):aliases.pop(dest,None)
  p['entry_basic_block_argument_reads']=reads;p['entry_basic_block_argument_writes']=writes
 r['non_init_reachable_windows']=[x for x in r['reachable_candidate_windows'] if x['owner']['depth']>0]
 if r['callbacks']['fx6_ap'] is None:r['status']='UNKNOWN; producer slot remains zero for bounded valid input, not automatically compatible'
 else:
  c=r['callbacks']['fx6_ap'];t=(H/c['excerpt']).read_text()
  if len(t.splitlines())==1 and 'ret' in t:r['status']='LEAF_NO_MEMORY_ACCESS; full consumer contract UNKNOWN'
 r['consumer_evidence_note']='194 GOT windows include stores and nearby unrelated calls; inspect actual register chain, not near_indirect list alone'
(H/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n')
lines=['# 57项覆盖矩阵','', '所有行的完整调用约定/枚举/间接被调者/所有权仍未通过；条目链接是原码证据，不是适配许可。','', '| symbol | FX3→FX6 offset | FX6入口/零槽 | FX3 GOT窗口数 | FX6首基本块输入读取offset | 状态 |','|---|---|---|---|---|---|']
for r in rows:
 c=r['callbacks']['fx6_ap'];target=f"[{hex(c['target'])}]({c['excerpt']})" if c else 'zero (bounded input)';rd=', '.join(x['offset'] for x in c['entry_basic_block_argument_reads']) if c else 'n/a'
 lines.append(f"| {r['symbol']} | {r['fx3_offset']}→{r['fx6_offset']} | {target} | {len(r['fx3_consumer_windows'])} | {rd or '未见/见分支后unknown'} | {r['status']} |")
(H/'COVERAGE.md').write_text('\n'.join(lines)+'\n')
(H/'extra-evidence.json').write_text(json.dumps(extra,indent=2)+'\n')
print({'rows':len(rows),'non_init_reachable_windows':sum(len(r['non_init_reachable_windows']) for r in rows),'ret_leaves':sum(r['status'].startswith('LEAF') for r in rows)})
