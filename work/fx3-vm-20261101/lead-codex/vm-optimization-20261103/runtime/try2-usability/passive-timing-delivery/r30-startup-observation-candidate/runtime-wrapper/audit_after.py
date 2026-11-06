"""Read-only original-runtime audit; r24 mutable outputs remain in this run; never a menu-success assertion."""
from common import *
from preflight import verify

def main():
 cleanup=read('CLEANUP.json')
 assert cleanup['runner_alive'] is False and cleanup['port_closed'] is True and not cleanup['errors']
 verify('INPUTS-AFTER.json')
 write('OUTPUT-BOUNDARY-AFTER.json',{'original_runtime_writes_allowed':[],'candidate_run_outputs_root':str(HERE),**stamp()})
 print(json.dumps({'status':'collected_only','menu_acceptance':'requires independent real eight-step visual/native evidence review'}))
if __name__=='__main__':main()
