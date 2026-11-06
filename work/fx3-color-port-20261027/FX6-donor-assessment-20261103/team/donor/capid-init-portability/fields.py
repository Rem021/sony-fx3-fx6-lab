from pathlib import Path
import re,json,struct,subprocess
ns={'__file__':str(Path(__file__).resolve().parent/'analyze.py')};exec((Path(__file__).parent/'analyze.py').read_text().split('E={k:ELF')[0],ns)
P=ns['P'];ELF=ns['ELF'];HERE=ns['HERE'];out={}
for key,start,end in [('fx3_mpr',0xb6844,0xb70b0),('fx6_mpr',0x12b3dc,0x12bd80)]:
 e=ELF(P[key]);b=e.b;got={}
 for s in e.sections:
  if s[1]!=4:continue
  ds=e.sections[s[6]];ss=e.sections[ds[6]];strings=b[ss[4]:ss[4]+ss[5]]
  for off in range(s[4],s[4]+s[5],24):
   va,info,add=struct.unpack_from('<QQq',b,off);idx=info>>32
   if idx:
    no=struct.unpack_from('<I',b,ds[4]+idx*24)[0];got[va]=strings[no:].split(b'\0')[0].decode()
 text=subprocess.check_output(['xcrun','llvm-objdump','-d',f'--start-address={start}',f'--stop-address={end}',str(P[key])],text=True)
 (HERE/(key+'-init-field-consumer.txt')).write_text(text)
 page=None;field=None;fields=[]
 for line in text.splitlines():
  m=re.search(r'^\s*([0-9a-f]+):.*\badrp\s+x0, (0x[0-9a-f]+)',line)
  if m:page=int(m[2],16)
  m=re.search(r'^\s*([0-9a-f]+):.*\bldr\s+x1, \[x19, #(0x[0-9a-f]+)\]',line)
  if m:field={'offset':int(m[2],16),'load':e.mapping(int(m[1],16))}
  m=re.search(r'^\s*([0-9a-f]+):.*\bldr\s+x0, \[x0, #(0x[0-9a-f]+)\]',line)
  if m and field and page is not None:
   va=page+int(m[2],16)
   if va in got:fields.append({**field,'destination_symbol':got[va],'got_va':hex(va),'got_load':e.mapping(int(m[1],16))})
   field=None
 out[key]=fields
m3={x['destination_symbol']:x for x in out['fx3_mpr']};m6={x['destination_symbol']:x for x in out['fx6_mpr']}
rows=[]
for sym in sorted(m3.keys()|m6.keys()):
 rows.append({'symbol':sym,'fx3_offset':hex(m3[sym]['offset']) if sym in m3 else None,'fx6_offset':hex(m6[sym]['offset']) if sym in m6 else None,'status':'same destination symbol; callback signature and nested ABI NOT proven' if sym in m3 and sym in m6 else 'unmatched'})
(HERE/'callback-fields.json').write_text(json.dumps({'loads':out,'symbol_mapping':rows},indent=2)+'\n')
print(json.dumps(rows,indent=2))
