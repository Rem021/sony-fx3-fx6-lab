"""Compare fixed native policy to saved actual evidence, without root or USB."""
from pathlib import Path
from hashlib import sha256
import json,re
H=Path(__file__).resolve().parent
text=(H/'manual_recovery_binding.h').read_text()
old=H.parent/'stage268-fixed-manual-recovered-communication02'
material=json.loads((old/'fixed-material.json').read_text())
held=(H/'prior-evidence/held-record.bin').read_bytes()
def carray(name):
    pattern=name+r'(?:\[[0-9]+\])?\s*=\s*\{([^}]+)\}'
    m=re.search(pattern,text);assert m,name
    return bytes(int(x.strip(),0)for x in m[1].split(','))
assert carray('FX3_PRIOR_PRIVACY_KEY')==bytes.fromhex(material['privacy_key'])
assert carray(r'\.previous_nonce')==held[48:64]==bytes.fromhex(material['nonce'])
assert carray(r'\.previous_grant_hash')==held[64:96]==sha256(material['grant_id'].encode()).digest()
assert carray(r'\.prior_body_tag')==held[248:280]
runtime=json.loads((H/'prior-evidence/original-runtime-review.json').read_text())
owner=runtime['helper_identity'];cleanup=json.loads((H/'prior-evidence/host-cleanup.json').read_text())
assert owner['pid']==cleanup['actual_program_stdout']['helper_PID']==34474
assert cleanup['independent_original_PID_probes']=={'34474':None,'34391':None}
assert cleanup['actual_program_stdout']['old_guard_bytes_unchanged']is True
assert '.previous_owner={34474u,0u,1793523718ull,860262ull}'in text
assert '.previous_observer={34391u,501u,1793523705ull,650572ull}'in text
prior=json.loads((H/'fixed-prior-evidence.json').read_text())
for x in prior['files']:assert sha256((H/x['path']).read_bytes()).hexdigest()==x['sha256']
digest=sha256(json.dumps(prior['files'],sort_keys=True,separators=(',',':')).encode()).digest()
assert digest.hex()==prior['evidence_digest_sha256']and carray(r'\.fixed_evidence_digest')==digest
cache=json.loads((H/'recovered-MSC-cache.json').read_text())
assert cache['same_body_as_actual269_HMAC_in_memory']is True
assert cache['target']['registryID']==4296064081 and cache['physical_port_registryID']==4294968654
current=json.loads((H/'fixed-material.json').read_text())
assert current['target']['registryID']==4296064081 and current['grant_id']!=material['grant_id']
assert current['nonce']!=material['nonce']and current['privacy_key']!=material['privacy_key']
result=dict(status='CURRENT_ACTUAL269_270_RECOVERY_POLICY_AND_NEW_TARGET_BOUND',
    saved_private_result_body_tag_matches_policy=True,old_key_compared_without_output=True,
    previous_actors_and_grant_match_actual_evidence=True,new_grant_nonce_key_are_distinct=True,
    fixed_evidence_members=len(prior['files']),current_target_cache_only=True,
    actual_root_journal_accessed=False,new_root_or_USB_operations=0,
    saved_records_do_not_recreate_original_live_peer=True)
with(H/'current-binding-check.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
