#!/usr/bin/env python3
"""Actual invocation of r41 parse_command_timing.py at the two phase cutoffs."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
DEL=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery')
R=Path(__file__).resolve().parent; OUT=R/'receipts'; RUN=DEL/'r47-runtime-integration-candidate/run-inputs/f9c618eedbad'; N=Path(json.loads((RUN/'runtime.json').read_text())['run'])
PARSER=DEL/'r41-command-entry-timing-candidate/parse_command_timing.py'; SERIAL=N/'serial.log'
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(tag,cutoff,out):
 if out.exists():out.unlink()
 cmd=[sys.executable,'-B',str(PARSER),str(SERIAL),'--run-id','v47runtime-n64-r47-f1be5a01'+('' if tag=='precleanup' else '-'+tag),'--cutoff-byte',str(cutoff),'--output',str(out)]
 t=time.time();p=subprocess.run(cmd,text=True,capture_output=True);dt=time.time()-t
 assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
 d=json.loads(out.read_text())
 return {'tag':tag,'cutoff_byte':cutoff,'argv':cmd,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'elapsed_s':dt,'output_path':str(out),'output_sha256':h(out),'summary':{k:d[k] for k in ('record_count','known_durations','known_same_thread_gaps','unknown_reason_counts','bytes_consumed','ignored_complete_other_lines')}}
def main():
 a=run('startup',3490401,OUT/'command-entry-parse-startup-3490401.json')
 b=run('precleanup',6077228,OUT/'command-entry-parse-6077228.json')
 value={'schema':'fx3-r49-parser-invocation-v1','parser_path':str(PARSER),'parser_sha256':h(PARSER),'serial_path':str(SERIAL),'serial_sha256':h(SERIAL),'serial_bytes':SERIAL.stat().st_size,
  'cutoffs':{'startup_first_qualified_evaluation_complete':3490401,'first_cleanup':6077228,'after_cleanup':6260972},
  'invocations':[a,b],
  'stage_boundary_source':str(R/'receipts/startup-observation-audit.json'),
  'later_6082916_not_used':True,
  'scope':'guest CLOCK_MONOTONIC command entry->return marks only; no CPU/FIFO/HTTP inference'}
 (OUT/'parser-invocation.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'parser_sha256':value['parser_sha256'],'startup':a['summary'],'precleanup':b['summary'],'receipt':str(OUT/'parser-invocation.json')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
