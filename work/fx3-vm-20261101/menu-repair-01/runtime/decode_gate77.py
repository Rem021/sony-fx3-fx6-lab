from pathlib import Path
import struct,json,sys
run=Path(sys.argv[1]);b=(run/'ui-gate-counters.bin').read_bytes();h=struct.unpack_from('<8Q',b);assert h[0]==0x3145544147335846 and h[1]==2
v=struct.unpack_from('<80Q',b,0x100+h[2]*0x1000);names=['peak_all','peak_gate','field_samples']+[f'hist_{i}' for i in range(6)]+[f'gate_hist_{i}' for i in range(6)]+['system_false','backlog_skip','time_skip','time_pass','dequeue_total','timer_dequeue','a12_nonzero','a13_nonzero','last_object','last_a18','last_a12','last_a13','first_ns','last_ns','mirror_skip','selftest','bound'];assert len(names)==32
x={'header':list(h),'counts':{str(i):n for i,n in enumerate(v[:48])},'statistics':dict(zip(names,v[48:])),'snapshot_scope':'latest completed double-bank snapshot at QMP stop; may lag a probe paused in callback; raw boot records independently committed','histogram_buckets':['0','1','2','3..10','11..100','>100'],'boot_records':[]}
rnames=['id','n','tid','pc','x0','x1','x2','x3','x4','x19','x20','x21','x22','x25','x26','x27','x28','fp','token_or_req','create_sequence','create_function','completion_sequence','completion_handle','commit']
for i in range(64):
 z=struct.unpack_from('<24Q',b,0x4000+i*24*8)
 if z[-1]==0x544f4f4245544147:x['boot_records'].append(dict(zip(rnames,z)))
(run.parent.parent/'ap77a-gate-readback.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x,indent=2))
