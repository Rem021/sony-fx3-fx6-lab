from pathlib import Path
R=Path(__file__).resolve().parent;p=R/'review_pin80.py';s=p.read_text();needle="v['same_candidate_repeat_group']=None;";add="""v['barrier_groups']=[];group=None
for z in records:
 if z['id']==22:
  group={'entry_tid':z['tid'],'parameters':[z[k]&0xffffffff for k in ['x1','x2','x3','x4']],'tokens':[],'post_remaining':[],'return_values':[]};v['barrier_groups'].append(group)
 elif group is not None and z['id']==23:group['tokens'].append(z['x0']&0xffffffff)
 elif group is not None and z['id']==24:group['post_remaining'].append(z['x22']&0xffffffff)
 elif group is not None and z['id']==25:group['return_values'].append(z['x0']&0xffffffff);group=None
v['barrier_passed']=any(collections.Counter(z['tokens'])==collections.Counter(handles) and len(handles)==4 and z['post_remaining'][-1:]==[0] and z['return_values']==[0] for z in v['barrier_groups']) and all(z['natural_completion_count']==1 and z['completion_function_returns']==[0] for z in v['boot_tasks'])
v['boot_return_notify_events']=[z for z in v['boot_events'] if 'FX3_BOOT_EVENT_LINK' in z['text'] or 'FX3_BOOT_CV_' in z['text']]
v['panel_reverse_enum']={'known':bool(g['extended_header'][12]),'value':g['extended_header'][13]}
""";s=s.replace(needle,add+needle);s=s.replace("v['new_pending_request']={'destination':'0x92840747','command':'0x328','size':10,'raw':'0d2028030a0001800300','reply_added':False};", "v['new_pending_request']=[{'line':i+1,'text':x} for i,x in enumerate(ls) if 'FX3_BOOT_TAIL_REQUEST' in x and ('flow=0' in x or 'destination=0x912f0335' in x)][-1:];");p.write_text(s);compile(s,str(p),'exec')
