#!/usr/bin/env python3
from pathlib import Path
import re,json,subprocess,hashlib,time
O=Path(__file__).resolve().parent;D=O.parent;s=(D/'v25-r15-snapshot-tail/fx3-ui-gate-v15.c').read_text();a=s.index('static int bind_ram(void)');b=s.index('\nstatic void bind(void *h)',a);(O/'tests/original-bind-ram.inc').write_text(s[a:b]+'\n')
cmd=['/usr/bin/clang','-O2','-I'+str(O/'tests'),str(O/'tests/claim_fixture.c'),'-o',str(O/'build/host-claim')];c=subprocess.run(cmd,capture_output=True);(O/'receipts/claim-compile.stderr').write_bytes(c.stderr);assert not c.returncode,c.stderr.decode()
claim=O/'tests'/('claim-'+str(time.time_ns())+'.identity');receipts=[]
for expected in [0,-1,-1]:
 args=[cmd[-1],str(claim),str(expected)];r=subprocess.run(args,capture_output=True);receipts.append({'argv':args,'exit':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode()});assert r.returncode==0,r.stderr.decode()
# Preserve claim, including the original text payload, do not unlink/reuse quota.
# Historical evidence: matching UI/OSD modules in the same im maps and only one bound UI.
history=[]
for r in json.loads((D/'r35-existing-log-opportunities/opportunities.json').read_text())['runs']:
 b=Path(r['source']).read_bytes()[:r['cut']];bound=re.findall(rb'FX3_UI_GATE_BOUND [^\n]*\n',b);assert len(bound)==1,(r['tag'],len(bound))
 blocks=re.finditer(rb'FX3_AP_EARLY_MAPS_(\d+)_(\d+)_BEGIN\r?\n(.*?)FX3_AP_EARLY_MAPS_\1_\2_END',b,re.S);found=[]
 for m in blocks:
  lines=m.group(3).splitlines();osd=[l.decode('ascii','replace') for l in lines if b'/simulation/fx3-osd-headless-v5.so' in l];ui=[l.decode('ascii','replace') for l in lines if b'/simulation/fx3-ui-gate-v1.so' in l]
  if osd and ui:found.append({'pid':int(m.group(1)),'round':int(m.group(2)),'osd_map_lines':osd,'ui_map_lines':ui})
 # Later full task maps are acceptable if early maps not logged in a window.
 history.append({'run':r['tag'],'one_UI_BOUND_before_cut':True,'early_same_process_map_evidence':found[:1],'limits':'historical, not a future loader/lifetime guarantee'})
result={'claim_test_compile':cmd,'host_real_O_EXCL_process_restarts':receipts,'claim_file':str(claim),'claim_sha256':hashlib.sha256(claim.read_bytes()).hexdigest(),'history':history,'contract':['Fresh exact fixed guest uses the original unchanged preload line','Only callbacks installed after successful original bind_ram may export','Original global O_EXCL claim persists until End; no authorized unlink/reset/uninstall/reload remapping','Initial active preload module remains loaded; added same-process module cannot install because original claim exists','Foreign TGID cannot touch even CLONE_VM shared diagnostic BSS','External host run identity scopes serial and End cutoff; PID/init stamps alone are not global identity']}
(O/'INSTANCE-CONTRACT.json').write_text(json.dumps(result,indent=2)+'\n');print('original claim ordering and actual host O_EXCL restart test PASS; historical map evidence recorded')
