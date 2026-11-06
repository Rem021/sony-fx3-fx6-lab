from pathlib import Path
import json,hashlib,struct
R=Path(__file__).resolve().parent;H=R/'helpers';P=R.parents[1]/'lead-claude/audits/pin-topology/pin-topology-proof.json';v=json.loads(P.read_text());keys=[tuple(int(z,16) for z in x['pin']) for x in v['model_after_11_connections']];assert len(keys)==len(set(keys))==22;edges=[]
for x in v['differences']:
 if x['state']==1:edges.append((keys.index(tuple(int(z,16) for z in x['source']['words'])),keys.index(tuple(int(z,16) for z in x['destination']['words']))))
assert len(edges)==11;out='/* Derived only from fixed FX3 pin topology proof; no A7C2 objects copied. */\nstatic const unsigned pkeys[22][4]={'+','.join('{'+','.join(hex(z)+'U' for z in k)+'}' for k in keys)+'};\nstatic const unsigned pedges[11][2]={'+','.join('{%d,%d}'%k for k in edges)+'};\n';(H/'fx3-pin-config-v1.h').write_text(out)
fixtures=[]
for x in v['projected_cold_software_requests']:
 req=bytes.fromhex(x['business_request']);rep=bytes.fromhex(x['reply_payload56']);fixtures.append({'dst':x['destination'],'request':req.hex(),'reply':rep.hex(),'row':x['row'],'kind':x['kind']});assert len(rep)==56 and len(req) in (24,40)
(R/'ap80a-static-fixtures.json').write_text(json.dumps({'proof_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'keys':keys,'edges':edges,'requests':fixtures,'checks':v['software_model_checks'],'scope':'33 conditional static requests as independent expected bytes; not guest evidence'},indent=2)+'\n');print('22 canonical endpoints/11 edges/33 fixtures frozen')
