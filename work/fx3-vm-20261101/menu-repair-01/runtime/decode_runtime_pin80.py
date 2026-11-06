from pathlib import Path
import struct,json,sys
run=Path(sys.argv[1]);b=(run/'ui-gate-counters.bin').read_bytes();h=struct.unpack_from('<8Q',b);assert h[0]==0x3145544147335846 and h[1]==2
v=struct.unpack_from('<80Q',b,0x100+h[2]*0x1000);names=['peak_all','peak_gate','field_samples']+[f'hist_{i}' for i in range(6)]+[f'gate_hist_{i}' for i in range(6)]+['system_false','backlog_skip','time_skip','time_pass','dequeue_total','timer_dequeue','a12_nonzero','a13_nonzero','last_object','last_a18','last_a12','last_a13','first_ns','last_ns','mirror_skip','selftest','bound'];assert len(names)==32
x={'header':list(h),'counts':{str(i):n for i,n in enumerate(v[:48])},'statistics':dict(zip(names,v[48:])),'snapshot_scope':'latest completed double-bank snapshot at QMP stop; may lag a probe paused in callback; raw boot records independently committed','histogram_buckets':['0','1','2','3..10','11..100','>100'],'boot_records':[]}
rnames=['id','n','tid','pc','x0','x1','x2','x3','x4','x19','x20','x21','x22','x25','x26','x27','x28','fp','token_or_req','create_sequence','create_function','completion_sequence','completion_handle','commit']
for i in range(64):
 z=struct.unpack_from('<24Q',b,0x4000+i*24*8)
 if z[-1]==0x544f4f4245544147:x['boot_records'].append(dict(zip(rnames,z)))
x['extended_header']=list(struct.unpack_from('<12Q',b));x['topology_captures']=[]
for index in range(4):
 off=0x8000+index*0xa00;head=struct.unpack_from('<8Q',b,off)
 if head[0]!=0x31504f5447583346:continue
 rows=[]
 for row in range(50):
  left=b[off+64+row*24:off+64+(row+1)*24];right=b[off+1264+row*24:off+1264+(row+1)*24]
  rows.append({'row':row,'selected_hex':left.hex(),'current_hex':right.hex(),'selected_fields':list(struct.unpack('<QIIQ',left)),'current_fields':list(struct.unpack('<QIIQ',right)),'differs':left!=right})
 x['topology_captures'].append({'header':list(head),'rows':rows,'all50_rows_present':len(rows)==50,'scope':'entry-time readonly copy; not an atomic snapshot across other threads; no topology mutation'})
x['change_mode_input24_hex']=b[0x7800:0x7818].hex()
x['extended_header']=list(struct.unpack_from('<16Q',b));gh=struct.unpack_from('<3Q',b,0xb000);x['pin_graph_header']=list(gh)
if gh[0]==0x3150414e53504e46 and gh[1]==3096:
 off=0xb040;v=struct.unpack_from('<2I4Q',b,off);graph={'ready':v[0],'fault':v[1],'serial':v[2],'queries':v[3],'connections':v[4],'disconnects':v[5],'pins':[],'buffers':[]}
 for i in range(22):
  at=off+40+i*104;key=list(struct.unpack_from('<4I',b,at));state,peer,generation,reply_refs,resource_refs,pending=struct.unpack_from('<IiQ3I',b,at+16);q=struct.unpack_from('<4I5Q',b,at+48);graph['pins'].append({'key':key,'state':state,'peer':peer,'generation':generation,'reply_refs':reply_refs,'resource_refs':resource_refs,'pending_hardware':pending,'queue':{'active':q[0],'capacity':q[1],'head':q[2],'count':q[3],'generation':q[4],'handles':list(q[5:])}})
 for i in range(16):
  vals=struct.unpack_from('<4I3QI',b,off+2328+i*48);graph['buffers'].append(dict(zip(['active','domain','producer','consumer','handle','generation','capacity','refs'],vals)))
 graph['eleven_edges_verified']=graph['ready']==1 and graph['fault']==0 and graph['connections']==11 and all(p['state']==0 and 0<=p['peer']<22 and graph['pins'][p['peer']]['peer']==i and not p['reply_refs'] and not p['resource_refs'] and p['queue']['active']==1 and p['queue']['capacity']==4 and p['queue']['count']==0 and not any(p['queue']['handles']) for i,p in enumerate(graph['pins'])) and all(z['active']==0 and z['refs']==0 for z in graph['buffers']);x['pin_graph']=graph
(run.parent.parent/(sys.argv[2].lower()+'-gate-readback.json')).write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x,indent=2))
