"""Read-only original-runtime audit; r24 mutable outputs remain in this run; never a menu-success assertion."""
from common import *
from preflight import verify

def main():
 # Never trust the compatibility/latest index as completion proof.
 ref=evidence.load(HERE/'CLEANUP-COMPLETED.json')
 c=identity();proof=evidence.revalidate(HERE,ref,evidence.binding(HERE,c,CFG),c,CFG)
 write('CLEANUP-AUDIT.json',proof)
 verify('INPUTS-AFTER.json')
 write('OUTPUT-BOUNDARY-AFTER.json',{'original_runtime_writes_allowed':[],'candidate_run_outputs_root':str(HERE),**stamp()})
 print(json.dumps({'status':'collected_only','menu_acceptance':'requires independent real eight-step visual/native evidence review'}))
if __name__=='__main__':main()
