"""Read-only completed/live serial aggregation. Output remains outside completed runs."""
from pathlib import Path
import argparse,collections,json,re,struct,hashlib
R=Path(__file__).resolve().parent

def summarize(run):
 text=(run/'serial.log').read_text(errors='replace');commands={};raws={};intervals={};textures={};frames=[];publications=[];incomplete=[];duplicates=[]
 def fields(line,tag):return dict(re.findall(r'([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)',line[line.index(tag)+len(tag):]))
 for n,line in enumerate(text.splitlines(),1):
  if 'FX3_GPE_RAW_PARAMS ' in line:
   f=fields(line,'FX3_GPE_RAW_PARAMS ')
   try:
    seq=int(f['seq']);raw=bytes.fromhex(f['raw_hex']);assert len(raw)==int(f['len']);raws[seq]={'line':n,'op':f['op'],'raw_hex':raw.hex(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
   except (KeyError,ValueError,AssertionError):incomplete.append({'line':n,'kind':'raw_params','text':line})
  if 'FX3_GPE_CMD ' in line:
   f=fields(line,'FX3_GPE_CMD ')
   try:
    seq=int(f['seq']);assert all(k in f for k in ['op','fmt','flags','selector','K','dst_phys','result']);int(f['result']);item={'line':n,'fields':f}
    if seq in commands:duplicates.append({'seq':seq,'before':commands[seq],'after':item})
    commands[seq]=item
   except (KeyError,ValueError,AssertionError):incomplete.append({'line':n,'kind':'command','text':line})
  if 'FX3_GPE_DRAW_INTERVAL ' in line:
   f=fields(line,'FX3_GPE_DRAW_INTERVAL ')
   try:intervals[int(f['seq'])]={'line':n,'fields':f}
   except (KeyError,ValueError):incomplete.append({'line':n,'kind':'target','text':line})
  for tag,key in [('FX3_TEX102_BEFORE ','before'),('FX3_TEX102_AFTER ','after'),('FX3_TEX102_SKIPPED ','skipped')]:
   if tag in line:
    f=fields(line,tag)
    try:textures.setdefault(int(f['seq']),{})[key]={'line':n,'fields':f}
    except (KeyError,ValueError):incomplete.append({'line':n,'kind':key,'text':line})
  if 'FX3_TEX102_HIST ' in line:
   f=fields(line,'FX3_TEX102_HIST ')
   try:
    seq,c,bins=int(f['seq']),int(f['channel']),int(f['bins']);hist={int(k):int(v) for k,v in (pair.split(':') for pair in f['counts'].split(','))};assert set(hist)==set(range(bins));textures.setdefault(seq,{}).setdefault('histograms',{})[str(c)]={'line':n,'bins':bins,'counts':hist,'pixel_count':sum(hist.values())}
   except (KeyError,ValueError,AssertionError):incomplete.append({'line':n,'kind':'histogram','text':line})
  if 'FX3_OSD102_COMMIT ' in line:
   f=fields(line,'FX3_OSD102_COMMIT ')
   try:
    assert all(k in f for k in ['frame','op','copied_GPE_last','FB','bitmap','physical','descriptor36']);desc=bytes.fromhex(f['descriptor36']);assert len(desc)==36;frames.append({'line':n,'fields':f,'descriptor_u32_raw_uninterpreted':list(struct.unpack('<9I',desc))})
   except (KeyError,ValueError,AssertionError):incomplete.append({'line':n,'kind':'OSD_commit','text':line})
  if 'FX3_OSD_HEADLESS_PUBLISH ' in line:
   publications.append({'line':n,'fields':fields(line,'FX3_OSD_HEADLESS_PUBLISH ')})
 for seq,item in commands.items():
  item['original_params']=raws.get(seq);item['validated_draw_target']=intervals.get(seq);item['texture_observation']=textures.get(seq)
 groups=collections.Counter()
 for seq,item in commands.items():
  f=item['fields'];target=intervals.get(seq,{}).get('fields',{});groups[(f['op'],f['fmt'],f['flags'],f['selector'],f['K'],target.get('destination_parent','unavailable'),f['dst_phys'],f['result'])]+=1
 prev=0
 for frame in frames:
  last=int(frame['fields']['copied_GPE_last']);ids=[seq for seq in commands if prev<seq<=last];frame['GPE_commands_since_prior_pixel_copy'] = ids;frame['GPE_op_counts'] = dict(collections.Counter(commands[x]['fields']['op'] for x in ids));frame['correlation']='last completed GPE sequence observed under same raster lock while native FB pixels copied; shared/retained surfaces and 1005 are not a hardware layer identity';prev=max(prev,last)
 for seq,t in textures.items():
  hist=t.get('histograms',{});t['four_complete_channel_histograms']=set(hist)=={'0','1','2','3'}
  if 'before' in t and t['four_complete_channel_histograms']:
   f=t['before']['fields'];expected=int(f['source_rows'])*int(f['source_line_bytes'])//int(f['source_bpp']);t['all_histograms_match_crop_pixel_count']=all(v['pixel_count']==expected for v in hist.values());t['raw_channel3_nonzero_pixels']=sum(v for k,v in hist['3']['counts'].items() if k);t['raw_channel3_all_zero']=t['raw_channel3_nonzero_pixels']==0
 identities=collections.Counter((f['fields']['FB'],f['fields']['bitmap'],f['fields']['token'],f['fields']['physical'],f['fields']['FBformat'],f['fields']['bitmapformat']) for f in frames)
 return {'run':str(run),'serial_sha256':hashlib.sha256((run/'serial.log').read_bytes()).hexdigest(),'GPE_commands':commands,'GPE_stats':[{'op':k[0],'fmt':k[1],'flags':k[2],'selector':k[3],'K':k[4],'destination_object':k[5],'destination_physical':k[6],'result':k[7],'count':v} for k,v in sorted(groups.items())],'OSD_committed_frames':frames,'OSD_publications':publications,'FB_identity_groups':[{'FB':k[0],'bitmap':k[1],'token':k[2],'physical':k[3],'FBformat':k[4],'bitmapformat':k[5],'commits':v,'plane_role_unproven':True} for k,v in identities.items()],'texture_observations':textures,'incomplete_records':incomplete,'duplicate_GPE_sequences':duplicates,'scope':'Full serial records retained; line interleaving/incomplete rows reported. Different FB/token/physical can be double buffers and do not prove multiple layers; 1003/1005 meanings follow existing software consumer only.'}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('run');a=p.parse_args();run=(R/'runs'/a.run).resolve();out=summarize(run);dest=R/(run.name+'-graphics102-v1.json');dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'path':str(dest),'commands':len(out['GPE_commands']),'commits':len(out['OSD_committed_frames']),'textures':len(out['texture_observations']),'incomplete':len(out['incomplete_records'])}))
