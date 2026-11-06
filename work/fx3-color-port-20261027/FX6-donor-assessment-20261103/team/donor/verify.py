#!/usr/bin/env python3
"""Rehash every recorded regular file and core artifact, no parser dependency."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
def main():
 checks=[('BODYDATA.DAT',json.loads((ROOT/'download-receipt.json').read_text())['sha256'])]
 u=json.loads((ROOT/'unpack-receipt.json').read_text())
 checks += [('firmware.fdat',u['fdat_sha256']),('firmware.tar',u['firmware.tar']['sha256']),('updater.img',u['updater.img']['sha256'])]
 specs=[('manifest.json',lambda e:ROOT/'tree'/e['path']),
        ('nflasha15-manifest.json',lambda e:ROOT/'nflasha15-files'/e['stored_path']),
        ('fat-manifest.json',lambda e:ROOT/'fat-files'/e['partition']/e['path'].lstrip('/')),
        ('fat32-manifest.json',lambda e:ROOT/'fat-files/nflasha23'/e['path'].lstrip('/')),
        ('nested-manifest.json',lambda e:ROOT/'nested-files'/e['image']/e['path'].lstrip('/'))]
 counts={}
 for fn,mapper in specs:
  es=json.loads((ROOT/fn).read_text())['entries'];n=0
  for e in es:
   if e.get('kind','file')!='file':continue
   p=mapper(e);assert p.stat().st_size==e['bytes'],p
   assert sha(p)==e['sha256'],p
   n+=1
  counts[fn]=n
 for name,expected in checks:assert sha(ROOT/name)==expected,name
 receipt={'result':'pass','member_files_rehashed':counts,'core_artifacts_rehashed':[x[0] for x in checks]}
 (ROOT/'verify-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt))
if __name__=='__main__':main()
