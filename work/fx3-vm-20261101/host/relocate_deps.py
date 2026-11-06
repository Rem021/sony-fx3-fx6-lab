from pathlib import Path
import subprocess,json,hashlib,re,os,plistlib
root=Path(__file__).resolve().parent
deps=root/'deps';records=[]
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
paths={p.name:p.resolve() for p in deps.rglob('*.dylib')}
files=sorted(p for p in set(paths.values()) if p.parts[len(deps.parts)] in ['glib','pcre2'] or p.name.startswith('libintl.'))
pkg=[p for p in (deps/'pkgconf').rglob('pkgconf') if p.is_file() and p.parent.name=='bin'][0]
for p in files+[pkg]:
 before=hashlib.sha256(p.read_bytes()).hexdigest()
 listing=subprocess.check_output(['otool','-L',str(p)],text=True)
 changes=[]
 for l in listing.splitlines()[1:]:
  old=l.strip().split(' (')[0]
  if old.startswith('/opt/homebrew/') or old.startswith('@@HOMEBREW'):
   base=Path(old).name
   if base not in paths:raise RuntimeError(('missing local dylib',old,p))
   target=paths[base]
   if target==p:
    subprocess.run(['install_name_tool','-id',str(p),str(p)],check=True,capture_output=True)
   else:
    subprocess.run(['install_name_tool','-change',old,str(target),str(p)],check=True,capture_output=True)
   changes.append({'old':old,'new':str(target)})
 if changes:subprocess.run(['codesign','--force','--sign','-',str(p)],check=True,capture_output=True)
 records.append({'path':str(p),'before':before,'after':hashlib.sha256(p.read_bytes()).hexdigest(),'changes':changes})
pcdir=root/'pkgconfig';pcdir.mkdir(exist_ok=True)
for p in deps.rglob('*.pc'):
 s=p.read_text()
 for name in ['pcre2','gettext','glib','pkgconf']:
  prefix=next(x for x in (deps/name).iterdir() if x.is_dir())
  s=s.replace('/opt/homebrew/opt/'+name,str(prefix))
  s=re.sub(r'/opt/homebrew/Cellar/'+name+r'/[^/\s]+',str(prefix),s)
 p2=pcdir/p.name;p2.write_text(s)
(root/'dependency-relocation.json').write_text(json.dumps(records,indent=2)+'\n')
print('LOCAL_PKGCONF',pkg)
print('DYLIBS',len(files))
print('PKGCONFIG',pcdir)
