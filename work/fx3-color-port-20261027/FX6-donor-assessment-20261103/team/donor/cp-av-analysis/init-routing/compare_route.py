#!/usr/bin/env python3
"""Evidence-tiered FX3/FX6 look-22 CPU route comparison."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
FX3=ROOT.parents[4]
assert FX3.name=='fx3-color-port-20261027'
PINS={'fx3_initializer':'29c76396ae58e8caca2bd96e0eb0408854c163e60556b5d27b4da9d6bd76ab95',
      'fx3_look':'6443be58aaa2a547aa7488a7551452ab4ce995bc108e8cb9244f7892b7b84a4f'}
def load(p,sha=None):
 b=p.read_bytes()
 if sha:assert hashlib.sha256(b).hexdigest()==sha
 return json.loads(b)
def hxrow(x):return [hex(v) for v in x]
def main():
 init=load(ROOT/'init-trace.json');dma=load(ROOT/'dma-trace.json');controls=load(ROOT/'controls.json')
 diff=load(ROOT.parent/'descriptor-diff.json')
 fx3i=load(FX3/'initializer-guest-results.json',PINS['fx3_initializer'])
 fx3l=load(FX3/'look-consumer-guest-results.json',PINS['fx3_look'])
 fx3copy=next(x for x in fx3i['copies'] if x['dst']=='0xb07ba0' and x['name']=='MLUT_MTX_A_REG_SG3TOAP1_0')
 fx6copy=next(x for x in init['copies'] if x['dst_offset']=='0xaa5208')
 fx3look=next(x for x in fx3l['lookup'] if x['input']==22)
 fx3case=fx3l['dma_list_cases'][0]
 fx3row=fx3case['descriptors'][63];fx6row=dma['slot63_dma_row']
 assert fx3copy['size']==fx6copy['bytes']==152
 assert fx3copy['name']=='MLUT_MTX_A_REG_SG3TOAP1_0' and fx6copy['src_offset']=='0xb83218'
 assert fx3look['name']=='MLUT_LOOKNAME_SL3SG3_TO_ACESREC709'
 assert fx3look['descriptor_count']==70 and len(fx3case['descriptors'])==70
 assert diff['venice_all_payloads_match_fx3'] and diff['venice_matrix']['same_as_fx3']
 assert diff['venice_matrix']['raw_words']==[1,0,0,0,75487,516574,522051,521632,79077,513403,523481,475,65868]
 assert dma['all_70_rows_match_original_descriptor_fields'] and dma['hardware_submitted'] is False
 assert fx3row[1]==fx6row[1]==0xf3019200 and fx3row[3]==fx6row[3]==0x0e48900d
 result={'scope':'selected look 22 in CPU fixtures; not current camera MAIN route, pixel computation, or hardware DMA',
  'input_source_sha256':{'fx6_av':init['source_sha256'],'fx3_initializer_json':PINS['fx3_initializer'],'fx3_look_json':PINS['fx3_look']},
  'look_selector':{'fx3':{'input':22,'name':fx3look['name'],'descriptors':fx3look['descriptor_count']},
                   'fx6':{'input':22,'name':'MLUT_LOOKNAME_SL3SG3_TO_ACESREC709','descriptors':70},
                   'evidence':'both original CPU lookup functions, FX3 prior receipt and FX6 cp-av-analysis/cpu-replay.json'},
  'matrix_source':{'fx3':{'descriptor_offset':fx3copy['src'],'matrix_data_pointer_low32':'0x1c15aa8'},
                   'fx6':{'descriptor_offset':fx6copy['src_offset'],'matrix_data_pointer_low32':hex(fx6row[0])},
                   'payload':'same 13 matrix words and SHA (from pinned descriptor comparison); pointer difference is image layout'},
  'initializer_copy':{'fx3':{'entry_offsets':fx3i['initializer_offsets'],'caller_offset':fx3copy['caller'],'dest_offset':fx3copy['dst'],'bytes':fx3copy['size']},
                      'fx6':{'entry_offset':'0x29f508','caller_offset':fx6copy['caller_offset'],'dest_offset':fx6copy['dst_offset'],'bytes':fx6copy['bytes'],
                             'instruction_count':init['instruction_count'],'original_memcpy_calls':init['calls_to_original_memcpy'],
                             'guarded_target_equals_original_source':controls['positive']['target_equals_unpatched_original_source']}},
  'dma_builder':{'fx3':{'entry_offset':'0x2c4794','row63':hxrow(fx3row),'register_base_low32':fx3case['register_base_low32'],
                          'evidence':fx3case['status']},
                 'fx6':{'entry_offset':dma['dma_entry_offset'],'row63':hxrow(fx6row),'register_base_low32':dma['register_base_low32'],
                        'slot_reads':dma['target_slot_read_events'],'callback_stubs':dma['stub_semantics'],
                        'all_70_rows_match_fields':dma['all_70_rows_match_original_descriptor_fields']},
                 'same_register_destination':fx3row[1]==fx6row[1],
                 'same_transfer_control_word':fx3row[3]==fx6row[3],
                 'source_pointer_difference':'relocated descriptor data in two image layouts',
                 'next_pointer_difference':'different isolated output buffer addresses, not a color algorithm change',
                 'hardware_submitted':False},
  'preprocessing_and_upstream_pixel_domain':{'fx3':'prior CPU descriptor initialization and lookup only',
    'fx6':'original CPU descriptor initialization and DMA-list construction only',
    'sensor_calibration_black_level_demosaic_noise_reduction':'unlocated in this route',
    'main_video_active_selection':'unobserved',
    'conclusion':'shared VENICE MLUT bytes and selected-look CPU routing do not establish equal final video color or RAW/ISP processing'},
  'vintage_scope':'29 descriptor pairs differ in Vintage look data; no inference about all FX6 video color differences'}
 (ROOT/'route-diff.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'look':22,'fx3_row63':hxrow(fx3row),'fx6_row63':hxrow(fx6row),'same_destination':result['dma_builder']['same_register_destination'],'same_control':result['dma_builder']['same_transfer_control_word']}))
if __name__=='__main__':main()
