"""Reconstruct every Git tree object locally from complete recursive listings."""
from pathlib import Path,PurePosixPath
from hashlib import sha1
import json
H=Path(__file__).resolve().parent;U=H/'upstream';reports=[]
for slug in ['dino2048--zv-e10-toolkit','cokeenet--zve10-qemu','YuuLuo--a7c2-service-preload']:
 h=json.loads((U/(slug+'-head.json')).read_text());t=json.loads((U/(slug+'-tree.json')).read_text());assert not t['truncated']
 rows=t['tree'];by={x['path']:x for x in rows};assert len(by)==len(rows)
 groups={'':[]}
 for x in rows:
  p=PurePosixPath(x['path']);assert not p.is_absolute() and all(v not in ('..','.') for v in p.parts)
  par=str(p.parent);par='' if par=='.' else par
  assert par=='' or by[par]['type']=='tree';groups.setdefault(par,[]).append(x)
  if x['type']=='tree':groups.setdefault(x['path'],[])
 verified=[]
 for parent,items in sorted(groups.items(),key=lambda x:(x[0].count('/')+(bool(x[0]))),reverse=True):
  children=sorted(items,key=lambda x:PurePosixPath(x['path']).name.encode()+ (b'/' if x['type']=='tree' else b''))
  body=b''.join(f'{int(x["mode"],8):o} '.encode()+PurePosixPath(x['path']).name.encode()+b'\0'+bytes.fromhex(x['sha']) for x in children)
  digest=sha1(f'tree {len(body)}\0'.encode()+body).hexdigest();want=by[parent]['sha'] if parent else h['commit']['tree']['sha'];assert digest==want,(slug,parent,digest,want)
  verified.append(dict(path=parent or '/',members=len(items),bytes=len(body),git_tree_sha1=digest))
 reports.append(dict(repo=slug.replace('--','/'),commit=h['sha'],api_response_sha=t['sha'],expected_root_tree=h['commit']['tree']['sha'],recursive_members=len(rows),verified_tree_objects=verified))
(H/'git-tree-object-proof.json').open('x').write(json.dumps({'schema':'git-complete-tree-reconstruction-v1','repositories':reports,'upstream_code_executed':False},ensure_ascii=False,indent=2)+'\n')
print([(r['repo'],len(r['verified_tree_objects']),r['expected_root_tree']) for r in reports])
