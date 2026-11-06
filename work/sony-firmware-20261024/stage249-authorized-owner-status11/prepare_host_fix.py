"""Preserve trial11 and derive a host-only repair; never launch any helper."""
from pathlib import Path
from hashlib import sha256
import difflib,json,os

D=Path(__file__).resolve().parent
H=D.parent/'stage248-fixed-owner-status-launch-package'
C=D/'host-fix-candidate'
C.mkdir(mode=0o700,exist_ok=False)
changes={}

old=(H/'receipt_receiver.py').read_text()
needle="if struct.unpack_from('<I',result,at)[0] not in range(1,14):raise Rejected('private event phase')"
replacement="""# Native claim tracing emits 101..109 (109 once per endpoint).
        # These are host API substeps, not additional camera operations.
        event_phase=struct.unpack_from('<I',result,at)[0]
        if event_phase not in range(1,14) and event_phase not in range(101,110):
            raise Rejected('private event phase')"""
assert old.count(needle)==1
changes['receipt_receiver.py']=(old,old.replace(needle,replacement))

old=(H/'supervisor.py').read_text()
needle="""        value=R.decode_record(data,self.verified.identity,self.frame.nonce)"""
replacement="""        # Preserve the original frame from this already identified stream
        # before decoding. A rejected frame is evidence, never a success.
        raw_file(self.directory/'received-final-record.bin',data)
        value=R.decode_record(data,self.verified.identity,self.frame.nonce)"""
assert old.count(needle)==1
new=old.replace(needle,replacement)
needle="""        if self.error:return dict(state,status='UNKNOWN_OBSERVER_ERROR',error=self.error)"""
replacement="""        if self.error:
            state.update(status='UNKNOWN_OBSERVER_ERROR',error=self.error)
            if self.verified is not None:
                try:current=self.ipc.probe(self.verified.identity.pid)
                except OSError:
                    state['process_observation_failed']=True
                    return state
                original=self.verified.identity
                gone=current is None or (current.pid==original.pid and
                    (current.sec,current.usec)!=(original.sec,original.usec))
                state['original_helper_gone']=gone
                # Close only this observer after confirmed helper exit.
                # No accepted receipt means no operation-success verdict.
                state['observer_may_finish']=gone
            return state"""
assert new.count(needle)==1
changes['supervisor.py']=(old,new.replace(needle,replacement))

old=(H/'run_approved_status.py').read_text()
needle="if result.get('helper_terminal_observed'):"
assert old.count(needle)==2
changes['run_approved_status.py']=(old,old.replace(needle,"if result.get('helper_terminal_observed') or result.get('observer_may_finish'):"))

diff=[];sources=[]
for name,(before,after) in changes.items():
    (C/name).write_text(after)
    compile(after,str(C/name),'exec')
    diff.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='stage248/'+name,tofile='candidate/'+name))
    sources.append(dict(path=name,original_sha256=sha256(before.encode()).hexdigest(),candidate_sha256=sha256(after.encode()).hexdigest()))
(D/'host-receipt-fix.patch').write_text(''.join(diff))
(D/'host-fix-source-receipt.json').write_text(json.dumps(dict(sources=sources,root_or_USB_operations=0,original_trial_unchanged=True,original_status='UNKNOWN',candidate_is_not_an_approved_launch_package=True),indent=2)+'\n')
print(json.dumps(dict(status='HOST_ONLY_FIX_PREPARED',files=len(changes),root_or_USB_operations=0)))
