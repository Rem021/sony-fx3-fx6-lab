#!/usr/bin/env python3
"""Rebuild newc CPIO preserving every non-target header/content byte."""
import hashlib,json,struct,sys
from pathlib import Path
def parse(b):
 out=[];pos=0
 while True:
  if b[pos:pos+6]!=b'070701':raise SystemExit('not newc at %d'%pos)
  hdr=b[pos:pos+110]; vals=[int(hdr[6+i*8:14+i*8],16) for i in range(13)]
  namesize,filesize=vals[11],vals[6]; name=b[pos+110:pos+110+namesize]; start=(pos+110+namesize+3)&~3; end=start+filesize; data=b[start:end]; pos=(end+3)&~3
  out.append({'header':hdr,'fields':vals,'name':name.rstrip(b'\0'),'data':data,'offset':pos})
  if name.rstrip(b'\0')==b'TRAILER!!!':return out
def hdr(fields,name):
 vals=list(fields);vals[11]=len(name)+1;return b'070701'+b''.join(b'%08x'%x for x in vals[:13])+name+b'\0'
def pad(b):return b+b'\0'*((-len(b))%4)
def build(entries):
 out=b''
 for e in entries:
  h=hdr(e['fields'],e['name']);d=e['data'];out+=pad(h)+pad(d)
 return out
def main(old,patched,newbin,out,diff):
 b=Path(old).read_bytes();es=parse(b);orig={e['name']:e for e in es}
 patched_data=Path(patched).read_bytes();bin_data=Path(newbin).read_bytes()
 target={b'init':patched_data,b'simulation/fx3-map-snapshot':bin_data};seen=set();new=[]
 for e in es:
  name=e['name']
  if name in target and name!=b'TRAILER!!!':
   e=dict(e);e['data']=target[name];e['fields']=list(e['fields']);e['fields'][6]=len(e['data']);seen.add(name)
  new.append(e)
 # append the new member before trailer if not present in original
 if b'simulation/fx3-map-snapshot' not in seen:
  tr=new[-1];assert tr['name']==b'TRAILER!!!'
  f=list(tr['fields']);f[0]=max(x['fields'][0] for x in es if x['name']!=b'TRAILER!!!')+1;f[1]=0o100755;f[2]=0;f[3]=0;f[4]=1;f[5]=0;f[6]=len(bin_data);f[7]=f[8]=f[9]=f[10]=0;f[11]=len(b'simulation/fx3-map-snapshot')+1;f[12]=0
  new.insert(len(new)-1,{'header':None,'fields':f,'name':b'simulation/fx3-map-snapshot','data':bin_data})
 # preserve original zero/padding bytes after the TRAILER member; no subsequent archive is appended
 tail=b[es[-1]['offset']:] if es else b''
 outb=build(new)+tail;Path(out).write_bytes(outb)
 # diff
 oldnames=[];newnames=[]
 for e in es:
  if e['name']==b'TRAILER!!!':continue
  oldnames.append(e['name'])
 for e in new:
  if e['name']==b'TRAILER!!!':continue
  newnames.append(e['name'])
 mism=[]
 by={e['name']:e for e in new}
 for e in es:
  n=e['name']
  if n==b'TRAILER!!!':continue
  q=by.get(n)
  if q is None:mism.append({'name':n.decode(),'why':'missing'})
  elif n not in target and (e['header']!=q['header'] or e['data']!=q['data']):mism.append({'name':n.decode(),'why':'metadata/content_changed'})
  elif n in target and n!=b'init':mism.append({'name':n.decode(),'why':'target_extra_mismatch'})
 newparsed=parse(outb); report={'schema':'fx6-map-cpio-diff-v1','original':old,'new':out,'original_sha256':hashlib.sha256(b).hexdigest(),'new_sha256':hashlib.sha256(outb).hexdigest(),'tail_padding_bytes':len(tail),'actual_reparse_count':len([e for e in newparsed if e['name']!=b'TRAILER!!!']),'actual_reparse_ok':all((e['name'] not in target and e['name']!=b'TRAILER!!!' and e['name']!=b'init' and e['name'] in by and e['header']==by[e['name']]['header'] and e['data']==by[e['name']]['data']) or (e['name']==b'TRAILER!!!' and e['data']==b'') or (e['name']==b'init' and e['data']==by[e['name']]['data']) or (e['name']==b'simulation/fx3-map-snapshot' and e['data']==by[e['name']]['data']) for e in newparsed),'original_count':len(oldnames),'new_count':len(newnames),'only_expected_changes':not mism and len(newparsed)==len(new),'mismatches':mism,'changed':[{'name':'init','old_bytes':len(orig[b'init']['data']),'new_bytes':len(patched_data),'old_sha256':hashlib.sha256(orig[b'init']['data']).hexdigest(),'new_sha256':hashlib.sha256(patched_data).hexdigest()},{'name':'simulation/fx3-map-snapshot','new_bytes':len(bin_data),'sha256':hashlib.sha256(bin_data).hexdigest()}],'unchanged_members':sum(1 for e in es if e['name'] not in (b'TRAILER!!!',b'init') and e['name'] in by and e['header']==by[e['name']]['header'] and e['data']==by[e['name']]['data'])}
 Path(diff).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2)[:3000])
if __name__=='__main__':main(*sys.argv[1:])
