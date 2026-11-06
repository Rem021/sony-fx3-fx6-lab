#!/usr/bin/env python3
"""Independent cross-check of generated receipts and pinned source artifacts."""
import hashlib,json,pathlib,platform
ROOT=pathlib.Path(__file__).resolve().parent
DONOR=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 m=json.loads((ROOT/'mapping.json').read_text())
 d=json.loads((ROOT/'descriptor-diff.json').read_text())
 e=json.loads((ROOT/'consumer-edge.json').read_text())
 i=json.loads((ROOT/'initializer-edges.json').read_text())
 r=json.loads((ROOT/'cpu-replay.json').read_text())
 assert m['cp']['sha256']==sha(DONOR/'fat-files/nflasha8/cpapp-b.bin')
 assert m['av']['sha256']==sha(DONOR/'fat-files/nflasha3/av-cam.bin')
 assert e['instruction_bytes_sha256']==r['function_original_bytes_sha256']
 assert d['fx6_descriptor_count']==d['fx3_descriptor_count']==612
 assert d['same_name_and_payload_count']==583
 assert len(d['vintage_renamed_and_changed'])==29
 assert len(i['fx6_copy_edges'])==3 and r['result']=='PASS'
 files=['analyze.py','replay_lookup.py','mapping.json','config-evidence.json','descriptor-diff.json','consumer-edge.json','initializer-edges.json','cpu-replay.json']
 receipt={'result':'PASS','scope':'static source pins, JSON cross-checks and bounded CPU replay receipt; no device/VM/camera',
          'python':platform.python_version(),'source_bytes_rehashed':{'cp':m['cp']['bytes'],'av':m['av']['bytes']},
          'output_sha256':{x:sha(ROOT/x) for x in files},
          'counts':{'descriptors':612,'identical_common':583,'changed_vintage':29,'static_copy_edges':3,'cpu_cases':len(r['cases'])}}
 (ROOT/'run-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'result':'PASS','counts':receipt['counts']}))
if __name__=='__main__':main()
