#!/usr/bin/env python3
"""Read-only image-hash/observation correction for r48 screenshots."""
import hashlib,json
from pathlib import Path
DEL=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery')
RUN=DEL/'r47-runtime-integration-candidate/run-inputs/f9c618eedbad'; OUT=DEL/'r49-frame-admission-analysis/receipts'
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
paths={'initial':'initial-standby/current.png','recovery_before':'step-01-attempt-01/recovery-review/observation.png','recovery_after':'step-01-attempt-01/recovery-cancel/observation/observation.png'}
obs={'initial':'actual r48/coordinator view: FX3 camera standby UI; NO CARD visible in the frame area','recovery_before':'actual r49 view: camera standby UI; NO CARD text absent from the frame area','recovery_after':'actual r48/coordinator view: camera standby UI; NO CARD visible'}
value={'schema':'fx3-r49-visual-correction-v1','images':{},'old_r48_report_claim':'r48 REPORT said all three images had NO CARD; that is imprecise.',
 'corrected_observation':'NO CARD is visible in initial-standby and recovery-after, absent in recovery-before; all three are standby/camera UI with no menu open.',
 'scope':'image observation only; do not modify old r48 sealed files; this does not prove native OSD flicker or the cause of the frame-generation change.',
 'fact_vs_inference':{'fact':['the three PNGs have distinct hashes','recovery-before has no NO CARD text; initial/after have it'],'inference':['the frame content/generation during the click window changed','the visible difference may reflect an OSD/content refresh'],'not_proven':['native flicker causality','whether NO CARD absence caused the frame SHA change','guest/CPU/FIFO behavior']}}
for k,rel in paths.items():
 p=RUN/rel; value['images'][k]={'path':str(p),'sha256':h(p),'bytes':p.stat().st_size,'observation':obs[k],'viewed':True}
assert value['images']['recovery_before']['sha256']=='7cf4783282db9dbd350f90cb787eda0da6d03ee76a308e8a1d0823c9beb4e13f'
assert value['images']['initial']['sha256']=='4854157cc2d0554ecc19a20c0eb6aca7d4b99571c1cf9b5a81ad5fac06696fb8'
assert value['images']['recovery_after']['sha256']=='4e9c654e5772c38e0e0e4b854a27fa75bdf881b349d0602dc4425dde9d372abc'
(OUT/'visual-correction.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'images':{k:v['sha256'][:12] for k,v in value['images'].items()},'receipt':str(OUT/'visual-correction.json')}))
