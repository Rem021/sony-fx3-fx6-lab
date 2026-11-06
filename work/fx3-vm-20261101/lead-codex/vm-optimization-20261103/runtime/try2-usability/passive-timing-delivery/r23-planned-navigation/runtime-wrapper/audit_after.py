"""Read-only fixed-input audit plus copies of the three authorized runtime outputs into this run; never a menu-success assertion."""
from common import *
from preflight import verify

def main():
 cleanup=read('CLEANUP.json')
 assert cleanup['runner_alive'] is False and cleanup['port_closed'] is True and not cleanup['errors']
 verify('INPUTS-AFTER.json')
 after=HERE/'authorized-outputs-after';after.mkdir()
 rows=[]
 for row in read('OUTPUT-BOUNDARY-BEFORE.json')['allowed_outputs']:
  p=Path(row['path']);assert p.parent==FROZEN and not p.is_symlink()
  entry={'path':str(p),'exists':p.exists(),'symlink':False,'in_frozen_sums':False}
  if p.exists():
   target=after/p.name;target.write_bytes(p.read_bytes());entry.update(sha256=sha(p),bytes=p.stat().st_size,copied_to=str(target))
  rows.append(entry)
 write('OUTPUT-BOUNDARY-AFTER.json',{'allowed_outputs':rows,**stamp()})
 print(json.dumps({'status':'collected_only','menu_acceptance':'requires independent real eight-step visual/native evidence review'}))
if __name__=='__main__':main()
