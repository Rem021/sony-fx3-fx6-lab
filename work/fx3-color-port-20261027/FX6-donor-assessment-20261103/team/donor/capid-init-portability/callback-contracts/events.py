from pathlib import Path
import json,re,struct,subprocess
H=Path(__file__).resolve().parent;B=H.parent
ns={'__file__':str(B/'analyze.py')};exec((B/'analyze.py').read_text().split('E={k:ELF')[0],ns)
e=ns['ELF'](ns['P']['fx3_mpr']);rows=json.loads((H/'matrix.json').read_text());fs=json.loads((B/'callback-fields.json').read_text());got={int(f['got_va'],16):f['destination_symbol'] for f in fs['loads']['fx3_mpr']}
t=subprocess.check_output(['xcrun','llvm-objdump','-d',str(ns['P']['fx3_mpr'])],text=True)
lines=t.splitlines();ins={int(m[1],16):(m[2],m[3],l) for l in lines if (m:=re.match(r'\s*([0-9a-f]+):\s+[0-9a-f]{8}\s+(\S+)\s*(.*)',l))}
(H/'fx3-dispatch.txt').write_text('\n'.join(ins[v][2] for v in sorted(ins) if 0xb442c<=v<0xb4e74)+'\n')
events=[]
for i in range(57):
 m=e.mapping(0x2cb3f8+i*2,2);delta=struct.unpack('<h',bytes.fromhex(m['bytes_le']))[0];a=0xb4460+delta*4;regs={};sym=None;window=[];guard=[];call=None;size=None
 for v in range(a,a+100,4):
  if v not in ins:break
  op,args,line=ins[v];window.append(line)
  q=re.match(r'(x\d+), (0x[0-9a-f]+)',args)
  if op=='adrp' and q:regs[q[1]]=int(q[2],16)
  q=re.match(r'(x\d+), \[(x\d+), #(0x[0-9a-f]+)\]',args)
  if op=='ldr' and q and q[2] in regs:
   addr=regs[q[2]]+int(q[3],16)
   if addr in got:sym=got[addr]
  if op=='cbz':guard.append({'instruction':e.mapping(v),'args':args})
  if op=='mov' and (q:=re.match(r'w1, #(0x[0-9a-f]+)',args)):size=int(q[1],16)
  if op=='blr':call=e.mapping(v);break
  if op=='b':break
 events.append({'event':hex(0x1000+i),'jump_entry':m,'block':hex(a),'symbol':sym,'null_guard':guard,'call':call,'copy_length_to_0xb3a78':size,'window':'\n'.join(window),'scope':'exact jump-table selected straight-line block; full argument producer allocation unresolved'})
for r in rows:
 r['event_dispatch']=[x for x in events if x['symbol']==r['symbol']]
 if r['event_dispatch']:r['consumer_observation']='SendIssueEvent x1 saved in x19 at b4440; callback x0=x19; callback result ignored; common free(x19) tail at b4488..b4494; original allocation/provenance unknown'
 else:r['consumer_observation']='unknown: not located in this dispatcher map'
(H/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n');(H/'events.json').write_text(json.dumps(events,indent=2)+'\n')
# Call windows, deliberately not ownership claims.
cs=[]
for i,l in enumerate(lines):
 if re.search(r'\bbl\s+.*<_ZN3mpr14SendIssueEventENS_5EVTIDEm(?:@plt)?>',l):cs.append('\n'.join(lines[max(0,i-18):i+6]))
(H/'dispatch-callers.txt').write_text('\n\n'.join(cs)+'\n')
print({'mapped_event_symbols':len({x['symbol'] for x in events if x['symbol']}),'null_slots':[(r['symbol'],[(x['event'],bool(x['null_guard'])) for x in r['event_dispatch']]) for r in rows if not r['callbacks']['fx6_ap']],'caller_windows':len(cs)})
