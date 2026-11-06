from pathlib import Path
from hashlib import sha256,sha1
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json,subprocess
H=Path(__file__).resolve().parent;U=H/'upstream'
selected={
'dino2048/zv-e10-toolkit':['README.md','linux/docs/bootrom-dump.md','linux/helpers/bootrom-reader/README.md','linux/helpers/bootrom-reader/read_page.S','linux/helpers/bootrom-reader/build_page_helper.py','linux/host/zve10_bootrom_dump.py','bootrom/docs/hardware.md','bootrom/docs/recovery.md','bootrom/host/restore_rescue.py','bootrom/host/bootstrap.py','bootrom/stage1/README.md','bootrom/stage2/README.md'],
'cokeenet/zve10-qemu':['README.md','docs/FASTBOOT_EMMC.md','docs/ANTIBRICK_SYSTEM.md','docs/analysis/memory/REAL_DEVICE_MEMORY_MAP.md','docs/incidents/INCIDENT_20261028_LDSO_PRELOAD.md','docs/incidents/SD_UPDATE_RECOVERY.md','docs/incidents/ZVEGISK_BRICK_RECOVERY.md'],
'YuuLuo/a7c2-service-preload':['README.md']}
jobs=[]
for slug,paths in selected.items():
 name=slug.replace('/','--');head=json.loads((U/(name+'-head.json')).read_text());tree=json.loads((U/(name+'-tree.json')).read_text());assert not tree['truncated']
 by={x['path']:x for x in tree['tree']}
 for path in paths:
  m=by[path];assert m['type']=='blob' and m['size']<100000
  jobs.append((slug,head['sha'],path,m))
def capture(job):
 slug,commit,path,m=job;url=f'https://raw.githubusercontent.com/{slug}/{commit}/{path}'
 result=subprocess.run(['/usr/bin/curl','--http1.1','-fL','--connect-timeout','10','--max-time','45','-sS',url],capture_output=True)
 if result.returncode:return dict(repo=slug,path=path,url=url,error=result.stderr.decode()[:256])
 raw=result.stdout;assert len(raw)==m['size'] and sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()==m['sha']
 dest=H/'reference'/slug.replace('/','--')/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.open('xb').write(raw)
 return dict(repo=slug,commit=commit,path=path,url=url,git_blob_sha1=m['sha'],bytes=len(raw),sha256=sha256(raw).hexdigest(),output=str(dest.relative_to(H)))
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(capture,jobs))
(H/'source-capture.json').open('x').write(json.dumps(dict(observed_utc=datetime.now(timezone.utc).isoformat(),files=rows,upstream_code_executed=False,camera_operations=0),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(selected=len(rows),ok=sum('sha256'in x for x in rows),errors=[x for x in rows if 'error'in x])))
