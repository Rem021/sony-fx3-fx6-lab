"""Saved own-fixture bytes test decoder binding only; no live-origin proof."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,struct,sys
sys.dont_write_bytecode=True
import receipt_receiver as R
import flow_receiver as F
import supervisor as S
H=Path(__file__).resolve().parent
d=H/'runs/attempt01-manual-idle-exit'
identity=R.Identity(**json.loads((d/'verified-helper.json').read_text())['identity'])
nonce=bytes.fromhex(json.loads((d/'spec.json').read_text())['nonce'])
flow=F.FlowReceiver(identity,nonce,R.GRANT_ID)
for p in sorted(d.glob('flow-*.bin')):flow.accept(p.read_bytes())
raw=bytearray((d/'private-record.bin').read_bytes());struct.pack_into('<Q',raw,960,101)
raw[992:]=sha256(raw[:992]).digest();value=R.decode_record(bytes(raw),identity,nonce)
assert value['manual_recovery']['source_node']==101 and flow.source_node==100
clone=S.Job();clone.receipt=None;clone.hello=True;clone.verified=R.VerifiedHelper(identity,'fixture')
clone.frame=type('FormatOnly',(),{'nonce':nonce})();clone.flow_state=flow;clone.ops=[];clone.responses=[]
clone.require_manual_recovery=True;clone.recovery_expected=None
clone.directory=H/'runs/saved-manual-source-counterexample';clone.directory.mkdir(mode=0o700)
try:clone._message(bytes(raw))
except R.Rejected as e:assert 'actual flow source' in str(e),e
else:raise AssertionError('manual source did not match flow but was accepted')
assert clone.receipt is None
old=H.parent/'stage264-cooperative-idle-held-exit/receipt_receiver.py'
spec=importlib.util.spec_from_file_location('fixture_old_receipt4',old)
legacy=importlib.util.module_from_spec(spec);sys.modules[spec.name]=legacy;spec.loader.exec_module(legacy)
try:legacy.decode_record((d/'private-record.bin').read_bytes(),identity,nonce)
except legacy.Rejected as e:assert 'magic' in str(e),e
else:raise AssertionError('legacy RCPT4 reader accepted RCPT5')
result=dict(status='SAVED_FIXTURE_BINDING_COUNTEREXAMPLES_REJECTED',
    flow_source_mismatch_denied=True,legacy_RCPT4_rejects_RCPT5=True,
    live_origin_recreated=False,new_process_or_root_or_USB_operations=0)
with (H/'saved-binding-checks.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
