from pathlib import Path
import json,re
R=Path(__file__).resolve().parent
for stage in ['ap86bv2','ap86a']:
 p=R/(stage+'-review.json');v=json.loads(p.read_text());run=Path(v['run']);raw=(run/'serial.log').read_bytes().decode(errors='replace');samples=[]
 for m in re.finditer(r'FX3_OSD_LIFE_FILE_BEGIN tag=(\S+) path=/proc/osal/uipc\r?\n(.*?)FX3_OSD_LIFE_FILE_END',raw,re.S):
  text=m.group(2);normal=text.split('- normal vblock',1)[-1].split('- realtime vblock',1)[0];sizes=[int(n) for n in re.findall(r'ffffff[a-fA-F0-9]+[ \t]+(\d+)\r?\n',normal)];qs=[];globalq=text.split('[] GMSGQ',1)[-1].split('[] GSEM',1)[0]
  for row in globalq.split('\n'):
   q=re.match(r'^([A-Fa-f0-9]+)\t(\d+)[ \t]+(\d+)[ \t]+(\d+)[ \t]+(\d+)[ \t]+(\d+)[ \t]+(\d+)[ \t]+(\d+)[ \t]+(\d+)\r?$',row)
   if q:qs.append((q.group(1),int(q.group(2)),q.group(0)))
  total=re.match(r'\s*\((\d+)\)',normal);samples.append({'tag':m.group(1),'line':raw[:m.start()].count('\n')+1,'normal_heading_value_uninterpreted':int(total.group(1)) if total else None,'free_blocks_parsed':len(sizes),'free_bytes_parsed_lower_bound':sum(sizes),'largest_block_parsed':max(sizes) if sizes else None,'top_GMSGQ_M':sorted(qs,key=lambda z:z[1],reverse=True)[:10],'scope':'First GLOBAL normal vblock only; later per-client local blocks excluded. Concurrent serial interleaving may corrupt rows; sums are parsed lower bounds, kernel QMP final is authoritative.'})
 v['pool_periodic_readonly_samples']=samples;p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(stage,'FIRST_LAST',json.dumps([samples[0],samples[-1]],ensure_ascii=False));print('TREND',[(x['normal_heading_value_uninterpreted'],x['free_bytes_parsed_lower_bound'],x['largest_block_parsed']) for x in samples])
