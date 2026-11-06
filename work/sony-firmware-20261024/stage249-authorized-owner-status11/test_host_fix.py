"""Pure decode/process fixtures. Synthetic envelopes are never live receipts."""
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
import importlib.util,json,struct,sys

D=Path(__file__).resolve().parent;H=D.parent/'stage248-fixed-owner-status-launch-package';C=D/'host-fix-candidate'
sys.path.insert(0,str(H))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
old=load('original_receiver249',H/'receipt_receiver.py')
new=load('fixed_receiver249',C/'receipt_receiver.py')
supervisor=load('fixed_supervisor249',C/'supervisor.py');supervisor.R=new
saved=json.loads((D/'verified-helper.json').read_text());identity=new.Identity(**saved['identity']);nonce=bytes.fromhex(saved['nonce'])
result=(D/'untrusted-shared-result.bin').read_bytes()
checks=[]
def envelope(body):
    out=bytearray(1024);out[:8]=b'FX3RCPT1'
    struct.pack_into('<6IQQ',out,8,1,1,1024,4,identity.uid,identity.pid,identity.sec,identity.usec)
    out[48:64]=nonce;out[64:96]=sha256(new.GRANT_ID.encode()).digest()
    struct.pack_into('<IiiIII',out,96,728,0,0,0,1,0)
    out[160:888]=body;out[120:152]=sha256(body).digest();out[992:]=sha256(out[:992]).digest();return bytes(out)
def rejected(module,data,needle=None):
    try:module.decode_record(data,identity,nonce)
    except module.Rejected as e:
        if needle:assert needle in str(e),str(e)
        return
    raise AssertionError('invalid record accepted')
good=envelope(result)
rejected(old,good,'private event phase');checks.append('old_decoder_reproduces_real_native_trace_rejection')
decoded=new.decode_record(good,identity,nonce);assert decoded['result']['event_count']==23 and not decoded['transport_peer_verified']
checks.append('synthetic_envelope_with_actual_untrusted_23event_trace_decodes_without_transport_proof')
for phase in [0,14,100,110,0xffffffff]:
    bad=bytearray(result);struct.pack_into('<I',bad,216,phase);rejected(new,envelope(bad),'private event phase')
checks.append('five_out_of_domain_phases_still_rejected')
for phase in range(101,110):
    body=bytearray(result);struct.pack_into('<I',body,216,phase);assert not new.decode_record(envelope(body),identity,nonce)['transport_peer_verified']
checks.append('all_nine_native_trace_identifiers_accepted_as_format_only')
for offset in [48,120,160,992]:
    bad=bytearray(good);bad[offset]^=1;rejected(new,bytes(bad))
checks.append('nonce_result_and_envelope_corruption_still_rejected')

T=D/'pure-fixture-records';T.mkdir(mode=0o700,exist_ok=False)
job=supervisor.Job();job.receipt=None;job.hello=True;job.verified=new.VerifiedHelper(identity,'live','0'*64)
job.frame=SimpleNamespace(nonce=nonce);job.responses=[{'status':0}]*3;job.ops=[1,6,5]
job.directory=T
bad=bytearray(result);struct.pack_into('<I',bad,216,110);bad_frame=envelope(bad)
try:job._message(bad_frame)
except new.Rejected:pass
else:raise AssertionError('bad native frame accepted')
assert (T/'received-final-record.bin').read_bytes()==bad_frame and job.receipt is None
assert not (T/'private-record.bin').exists()
checks.append('rejected_synthetic_frame_preserved_before_decoder_without_accepted_receipt')

def state(probe):
    j=supervisor.Job();j.runner=SimpleNamespace(poll=lambda:0);j.relay=j.runner
    j.error='test decoder error';j.verified=new.VerifiedHelper(identity,'live');j.ipc=SimpleNamespace(probe=probe)
    return j.step()
x=state(lambda pid:None);assert x['observer_may_finish'] and not x['helper_terminal_observed'] and x['status']=='UNKNOWN_OBSERVER_ERROR'
checks.append('confirmed_absence_allows_only_observer_to_finish_with_unknown')
x=state(lambda pid:identity);assert not x['observer_may_finish'] and not x['helper_terminal_observed']
checks.append('same_live_helper_preserves_original_context')
reused=new.Identity(identity.uid,identity.pid,identity.sec+1,identity.usec,identity.path,'')
x=state(lambda pid:reused);assert x['observer_may_finish'] and x['status']=='UNKNOWN_OBSERVER_ERROR'
checks.append('pid_reuse_proves_old_helper_gone_without_success')
def denied(pid):raise PermissionError('synthetic process metadata denial')
x=state(denied);assert x['process_observation_failed'] and not x.get('observer_may_finish')
checks.append('metadata_error_never_proves_exit')

out=dict(status='PASS_HOST_ONLY_REGRESSION',checks=checks,synthetic_private_envelope=True,synthetic_envelope_sha256=sha256(good).hexdigest(),actual_private_receipt_recovered=False,trial11_status_still='UNKNOWN',root_helper_launches=0,USB_or_driver_operations=0,network_operations=0,original_stage248_modified=False)
(D/'host-fix-test-receipt.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))
