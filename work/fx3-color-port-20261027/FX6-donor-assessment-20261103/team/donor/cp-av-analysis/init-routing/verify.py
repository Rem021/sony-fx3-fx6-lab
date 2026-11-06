#!/usr/bin/env python3
"""Rehash pinned originals and cross-check init, controls, DMA and comparison receipts."""
import hashlib,json,pathlib,platform
ROOT=pathlib.Path(__file__).resolve().parent
AV=ROOT.parents[1]/'fat-files/nflasha3/av-cam.bin'
PIN='56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(4*1024*1024):h.update(b)
 return h.hexdigest()
def load(n):return json.loads((ROOT/n).read_text())
def main():
 assert sha(AV)==PIN
 i=load('init-trace.json');c=load('controls.json');d=load('dma-trace.json');r=load('route-diff.json')
 assert i['source_sha256']==c['source_sha256']==d['source_sha256']==PIN
 assert i['error'] is None and not i['violations'] and i['stop_pc']=='0x60000000'
 assert i['target_equals_original_source'] and i['source_unchanged']
 assert i['calls_to_original_memcpy']==1166
 assert i['image_write_intervals']==[{'start':'0xa88bd0','end_exclusive':'0xab4020'}]
 assert i['image_write_unique_bytes']==177232 and len(i['image_write_instruction_offsets'])==13
 assert sum(x['dst_offset']=='0xaa5208' and x['src_offset']=='0xb83218' and x['bytes']==152 for x in i['copies'])==1
 assert c['positive']['returned_to_stop'] and c['positive']['canary_preserved']==[True,True]
 assert c['negative_source_mutation']['returned_to_stop'] and not c['negative_source_mutation']['target_equals_unpatched_original_source']
 assert not c['negative_budget_exhaustion']['returned_to_stop']
 assert d['error'] is None and not d['violations'] and d['dma_stop_pc']=='0x60000000'
 assert d['all_70_rows_match_original_descriptor_fields'] and d['hardware_submitted'] is False
 assert len(d['dma_rows'])==70 and len(d['target_slot_read_events'])==3
 assert d['slot63_dma_row'][1]==0xf3019200 and d['slot63_dma_row'][3]==0x0e48900d
 assert r['dma_builder']['hardware_submitted'] is False and r['dma_builder']['same_register_destination'] and r['dma_builder']['same_transfer_control_word']
 files=['trace_init.py','replay_controls.py','trace_dma.py','compare_route.py','init-trace.json','controls.json','dma-trace.json','route-diff.json']
 result={'result':'PASS','python':platform.python_version(),'pinned_fx6_av_sha256':PIN,
         'steps':['bounded initializer with original memcpy','guard and mutation/budget controls',
                  'bounded DMA-list builder with declared provider stubs','FX3/FX6 fixture route comparison'],
         'checks':{'initializer_instructions':i['instruction_count'],'original_memcpy_calls':i['calls_to_original_memcpy'],
                   'image_write_events':i['image_write_events'],'image_write_unique_bytes':i['image_write_unique_bytes'],
                   'image_write_instruction_count':len(i['image_write_instruction_offsets']),'target_copy_count':1,
                   'dma_builder_instructions':d['dma_instruction_count'],'dma_rows':len(d['dma_rows']),
                   'target_slot_read_events':len(d['target_slot_read_events']),'hardware_submitted':False},
         'artifact_sha256':{n:sha(ROOT/n) for n in files},
         'scope':'CPU guest and static comparison only; no VM/runtime/USB/camera/hardware DMA'}
 (ROOT/'run-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'result':'PASS','checks':result['checks']}))
if __name__=='__main__':main()
