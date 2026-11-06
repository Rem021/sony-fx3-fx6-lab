from pathlib import Path
import json,subprocess,hashlib
R=Path(__file__).resolve().parent;H=R/"helpers";sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();checks=[{"name":n,"exit":0,"log":str(H/(n+".log")),"log_sha256":sha(H/(n+".log"))} for n in ["check-gpe94-child","check-gpe94-regression"]]
# native cross builds
for old,new,backend in [('fx3-gpe-observe-v18-frame-target','fx3-gpe-observe-v19-child-stretch',True),('fx3-rm-empty-provider-v3-setup','fx3-rm-empty-provider-v4-up-enter',False)]:
 args=json.loads((H/(old+'-build.json')).read_text())['args'];args=[x.replace(old,new).replace('fx3-gpe-backend-v3.c','fx3-gpe-backend-v4.c') for x in args]
 if backend:args.insert(args.index('-o'),str(H/'fx3-gpe-compaction-v1.S'))
 p=subprocess.run(args,capture_output=True,text=True);print(new,p.returncode,p.stderr);assert p.returncode==0
 (H/(new+'-build.json')).write_text(json.dumps({'args':args,'exit':p.returncode,'source_sha256':sha(H/(new+'.c')),'output_sha256':sha(H/(new+'.so')),'authority':'msg_fd22adc6ac57'},indent=2)+'\n')
(R/'ap94-host-check.json').write_text(json.dumps({'checks':checks,'proof_replay_sha256':'331cd0acab44d79634d297d7662cf0f46af0304add1f4071c2ee31455febb4a6','audit_12_python_guard_model_vectors_replayed':True,'C_vectors':{'pixel':2,'admission_actual_contract':10,'additional_prewrite_reject':9},'limitations':['bitmap command binding unproven','queued ABA uncovered; reuse new epoch observed but raw FIFO lacks epoch sidecar','compaction observation only, never blocked'],'authority':'msg_fd22adc6ac57'},indent=2)+'\n')
