from pathlib import Path
import json,re,subprocess,struct,hashlib
H=Path(__file__).resolve().parent;B=H.parent
ns={'__file__':str(B/'analyze.py')};exec((B/'analyze.py').read_text().split('E={k:ELF')[0],ns)
P=ns['P'];ELF=ns['ELF'];E={k:ELF(p) for k,p in P.items()};sha=lambda b:hashlib.sha256(b).hexdigest()
old=json.loads((B/'receipt.json').read_text());assert all(sha(e.b)==old['hashes'][k] for k,e in E.items())
fields=json.loads((B/'callback-fields.json').read_text())
def dis(k,a=None,z=None):
 args=['xcrun','llvm-objdump','-d']
 if a is not None:args +=[f'--start-address={a}',f'--stop-address={z}']
 return subprocess.check_output(args+[str(P[k])],text=True)
def inst(t):
 return [(int(m[1],16),m[2],m[3],m[4].split(' //')[0].strip(),line) for line in t.splitlines() if (m:=re.match(r'\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(\S+)\s*(.*)',line))]
def syms(k):
 e=E[k];out={}
 for s in e.sections:
  if s[1]!=11:continue
  ss=e.sections[s[6]];st=e.b[ss[4]:ss[4]+ss[5]]
  for off in range(s[4],s[4]+s[5],24):
   n,info,oth,sh,v,sz=struct.unpack_from('<IBBHQQ',e.b,off)
   name=st[n:].split(b'\0')[0].decode()
   if sh and info&15==2 and sz:out[name]=(v,sz)
 return out
S={k:syms(k) for k in ['fx3_mpr','fx6_mpr']}
# Reuse prior producer excerpts; only decode ADRP/ADD/STR address chains.
prod={}
for k,base in [('fx3_ap',0x38),('fx6_ap',0x20)]:
 reg={};out={}
 for va,w,op,args,line in inst((B/(k+'-mpr-param-producer.txt')).read_text()):
  m=re.match(r'(x\d+), (0x[0-9a-f]+)',args)
  if op=='adrp' and m:reg[m[1]]=int(m[2],16)
  elif op=='add' and (m:=re.match(r'(x\d+), (x\d+), #(0x[0-9a-f]+)',args)):
   if m[2] in reg:reg[m[1]]=reg[m[2]]+int(m[3],16)
   else:reg.pop(m[1],None)
  elif op=='str' and (m:=re.match(r'(x\d+), \[x29, #(0x[0-9a-f]+)\]',args)) and m[1] in reg:out[int(m[2],16)-base]={'target':reg[m[1]],'store':E[k].mapping(va)}
  elif op in ('bl','blr'):reg.clear()
 prod[k]=out
D={};I={}
for k in ['fx3_mpr','fx6_mpr']:
 D[k]=dis(k);I[k]=inst(D[k])
# GOT-use windows are candidate cross-references only; aliases/clobbers require manual verification.
got={int(x['got_va'],16):x['destination_symbol'] for x in fields['loads']['fx3_mpr']}
refs={s:[] for s in got.values()};ins=I['fx3_mpr'];pages={}
for i,(va,w,op,args,line) in enumerate(ins):
 if op=='adrp' and (m:=re.match(r'(x\d+), (0x[0-9a-f]+)',args)):pages[m[1]]=(int(m[2],16),i)
 elif op=='ldr' and (m:=re.match(r'(x\d+), \[(x\d+), #(0x[0-9a-f]+)\]',args)):
  pg=pages.get(m[2]);addr=pg[0]+int(m[3],16) if pg and i-pg[1]<=12 else None
  if addr in got:
   win=ins[max(0,i-6):i+22];near=[hex(v) for v,_,o,_,_ in win if o in ('blr','br')]
   refs[got[addr]].append({'got_load':E['fx3_mpr'].mapping(va),'near_indirect':near,'window':'\n'.join(x[4] for x in win),'status':'candidate window, not a proven def-use edge'})
 elif op in ('bl','blr','ret','b'):pages.clear()
# Resolve direct synchronous call graph only through exact exported function entries and PLT names.
byva={v[0]:(name,*v) for name,v in S['fx3_mpr'].items()};start=S['fx3_mpr']['_ZN3mpr4InitERKNS_11initInParamE'][0]
visited={};todo=[(start,0,[])];edges=[];frontier=[]
while todo:
 a,depth,path=todo.pop(0)
 if a in visited:continue
 name,_,size=byva[a];body=[x for x in ins if a<=x[0]<a+size];visited[a]={'symbol':name,'depth':depth,'path':path,'size':size}
 for v,w,op,args,line in body:
  if op not in ('bl','b'):continue
  m=re.match(r'0x([0-9a-f]+) <([^>]+)>',args)
  if not m:continue
  target=int(m[1],16);label=m[2];dest=target if target in byva else S['fx3_mpr'].get(label.removesuffix('@plt'),(None,))[0]
  if dest is not None:
   edges.append({'caller':hex(a),'call':hex(v),'callee':hex(dest),'symbol':byva[dest][0]})
   if depth<5:todo.append((dest,depth+1,path+[hex(v)]))
   else:frontier.append({'call':hex(v),'reason':'depth limit'})
  elif op=='bl':frontier.append({'call':hex(v),'target':hex(target),'label':label,'reason':'external or non-exported entry'})
rows=[]
for f in fields['symbol_mapping']:
 if not f['fx3_offset'] or not f['fx6_offset']:continue
 sym=f['symbol'];row=dict(f);row['status']='UNKNOWN';row['fx3_consumer_windows']=refs[sym];row['callbacks']={}
 for k,off in [('fx3_ap',f['fx3_offset']),('fx6_ap',f['fx6_offset'])]:
  p=prod[k].get(int(off,16));row['callbacks'][k]=p
  if p:
   a=p['target'];t=dis(k,a,a+384);arr=inst(t);stop=next((j+1 for j,x in enumerate(arr) if x[2]=='ret'),len(arr));arr=arr[:stop]
   filename=f'{k}-{a:x}.txt';(H/filename).write_text('\n'.join(x[4] for x in arr)+'\n')
   p.update({'entry':E[k].mapping(a),'excerpt':filename,'bounded_bytes':384,'first_ret_found':any(x[2]=='ret' for x in arr)})
 row['reachable_candidate_windows']=[{'got_load':r['got_load'],'owner':v} for r in refs[sym] for a,v in visited.items() if a<=int(r['got_load']['va'],16)<a+v['size']]
 row['return_type']='unknown';row['nested_fields_size_enums']='unknown';row['lifetime']='global callback pointer retained by Init; callback argument lifetime unknown'
 rows.append(row)
(H/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n')
(H/'sync-graph.json').write_text(json.dumps({'root':hex(start),'visited':{hex(k):v for k,v in visited.items()},'edges':edges,'unresolved_frontier':frontier,'limits':'direct calls through exact exported symbols, depth<=5; not complete reachability or runtime execution'},indent=2)+'\n')
for k in S:
 for name in ['_ZN3mpr20IntegRecordMovieInitEjPKjjt','_ZN3mpr4InitERKNS_11initInParamE']:
  if name in S[k]:a,z=S[k][name];(H/(k+'-'+('movie-init' if 'Movie' in name else 'init')+'.txt')).write_text(dis(k,a,a+z))
(H/'inputs.json').write_text(json.dumps({'hashes':old['hashes'],'paths':old['paths'],'parent_receipt_sha256':sha((B/'receipt.json').read_bytes()),'parent_matrix_sha256':sha((B/'callback-fields.json').read_bytes())},indent=2)+'\n')
print(json.dumps({'shared':len(rows),'producer_found':{k:sum(bool(r['callbacks'][k]) for r in rows) for k in prod},'got_windows':sum(len(v) for v in refs.values()),'reachable_functions':len(visited),'reachable_windows':[(r['symbol'],len(r['reachable_candidate_windows'])) for r in rows if r['reachable_candidate_windows']]}))
