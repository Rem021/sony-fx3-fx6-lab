#!/usr/bin/env python3
"""Read-only audit of native startup-observation phases/ready/limits; no runtime contact."""
import hashlib,json
from pathlib import Path
DEL=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery')
RUN=DEL/'r47-runtime-integration-candidate/run-inputs/f9c618eedbad'
N=Path(json.loads((RUN/'runtime.json').read_text())['run'])
R=Path(__file__).resolve().parent; OUT=R/'receipts'
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=N/'startup-observation.json'; d=json.loads(p.read_text())
 phases=d['phases']; ready=d['ready']; headers=d['headers']
 expected_phase_offsets=[0,6077228,6260972]
 got=[x['serial_offset'] for x in phases['first_kinds']]
 assert d['schema']=='fx3-startup-observation-r30-v1',d['schema']
 assert d['saved'] is True and d['flush_attempted'] is True
 assert d['errors']=={},d['errors']
 assert d['stage']=='after_cleanup' and d.get('ready_incomplete') is None
 assert got==expected_phase_offsets,got
 assert phases['evicted_transitions']==0 and phases['first_kind_omitted']==0
 assert ready['evicted_transitions']==0 and ready['first_kind_omitted']==0
 assert headers['evicted_transitions']==0 and headers['first_kind_omitted']==0
 assert headers['observations']==157 and headers['transitions']==4 and headers['recent_limit']==48
 assert phases['observations']==3 and phases['transitions']==3 and phases['recent_limit']==8
 assert ready['observations']==1230 and ready['transitions']==6 and ready['recent_limit']==32
 assert d['header_counts']=={'bad_magic':91,'valid_seq0':2,'valid_positive':64}
 assert d['limits']=={'header_recent':48,'ready_recent':32,'phase_recent':8,'first_kind_per_stream':32,'marker_whitelist':14,'serial_carry_bytes':42,'file_bytes':262144}
 assert d['serial']['bytes']==6260972 and d['serial']['consumed_offset']==6260972 and d['serial']['carry_bytes']==42
 assert len(d['markers'])==14
 firstq=[x for x in ready['first_kinds'] if x.get('qualified') is True and x.get('evaluation_complete') is True]
 assert firstq and firstq[0]['serial_offset']==3490401, firstq[:1]
 assert ready['last']['serial_offset']==6077228
 cleanup=json.loads((RUN/'cleanup-calls/dc3a1077-4b0d-4bff-8351-ff77d26c582b/result.json').read_text())
 later=json.loads(Path(json.loads((RUN/'runtime.json').read_text())['run']).joinpath('receipt.json').read_text()).get('cleanup',{}).get('serial_bytes_before_cleanup')
 value={'schema':'fx3-r49-startup-observation-audit-v1','native_run':str(N),'startup_observation_path':str(p),'startup_observation_sha256':h(p),
  'serial_path':str(N/'serial.log'),'serial_sha256':h(N/'serial.log'),'serial_bytes':6260972,'serial_consumed_offset':6260972,'serial_carry_bytes':42,
  'schema_ok':True,'errors':d['errors'],'saved':d['saved'],'flush_attempted':d['flush_attempted'],'stage':d['stage'],'ready_incomplete':d.get('ready_incomplete'),
  'limits':d['limits'],'header_counts':d['header_counts'],'headers_meta':{k:headers.get(k) for k in ('observations','transitions','recent_limit','evicted_transitions','first_kind_omitted')},
  'phases_meta':{k:phases.get(k) for k in ('observations','transitions','recent_limit','evicted_transitions','first_kind_omitted')},
  'phases_first_kinds':phases['first_kinds'],
  'ready_meta':{k:ready.get(k) for k in ('observations','transitions','recent_limit','evicted_transitions','first_kind_omitted')},
  'ready_first_kinds':ready['first_kinds'],
  'startup_first_qualified_evaluation_complete_offset':3490401,
  'first_cleanup_serial_offset':6077228,'after_cleanup_serial_offset':6260972,
  'ready_last_at_first_cleanup':ready.get('last'),
  'later_cleanup_receipt_serial_bytes_before_cleanup':later,
  'later_6082916_used_for_phase':False,
  'boundary_notes':{'startup_phase':'[0,6077228) serial offsets','first_startup_qualified_eval_complete':'3490401','cleanup_phase':'[6077228,6260972]','after_cleanup':'6260972',
   'boot_guest_entry':'unknown: phases.startup.serial_offset=0 is host observation start, not exact guest entry','guest_command_entry':'separate FX3_GPE104_CMD_RETURN entry_ns records parsed by r41 parser'},
  'write_policy':d.get('write_policy'),'marker_count':len(d['markers'])}
 assert later is not None and later>6077228 and later!=6077228
 (OUT/'startup-observation-audit.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'schema':d['schema'],'errors':d['errors'],'first_startup_qualified':3490401,'first_cleanup':6077228,'after_cleanup':6260972,'ready_first_kinds':len(ready['first_kinds']),'phases':got,'later_not_used':later,'receipt':str(OUT/'startup-observation-audit.json')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
