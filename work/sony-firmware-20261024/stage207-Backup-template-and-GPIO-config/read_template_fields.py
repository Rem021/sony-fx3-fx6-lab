"""Read only3 named settings from pinned classic FX3 default BK4 templates.

Format reference: ma1co/Sony-PMCA-RE pmca/backup at pinned a82f5baa.
This reader has no mutation, device, authentication or firmware execution path.
"""
from pathlib import Path
from hashlib import sha256
import json, struct
H=Path(__file__).resolve().parent
R=H.parents[2]
capture=json.loads((H/'template-source-capture.json').read_text())
TARGETS=[0xf900d4,0xf900b1,0xf9006d]
def read_record(data,base):
    assert base+256<=len(data)
    magic,cookie,write,revision,ns,np,start,size,checksum=struct.unpack_from('<III4s5I',data,base)
    assert revision==b'BK4\0' and 0<ns<65536 and 0<np<1<<24
    end=base+start+size
    pbase=256+ns*6
    assert pbase+np*6<=start and end<=len(data)
    assert sum(data[base:base+32])+sum(data[base+36:end])==checksum
    subs=[]
    for n in range(ns):
        count,index=struct.unpack_from('<HI',data,base+256+n*6)
        assert index+count<=np
        subs.append((count,index))
    props=[]
    fixed=oversize=variable=invalid=0
    for n in range(np):
        table=base+pbase+n*6
        attr,ptr=struct.unpack_from('<HI',data,table)
        if ptr==0xffffffff:
            props.append(None);invalid+=1;continue
        length,off=ptr>>24,ptr&0xffffff
        assert start<=off<start+size
        if length==255:
            assert off+2<=start+size
            length,=struct.unpack_from('<H',data,base+off)
            maximum=length;off+=2;oversize+=1
        elif length==0:
            assert off+4<=start+size
            length,maximum=struct.unpack_from('<HH',data,base+off)
            off+=4;variable+=1
        else:
            maximum=length;fixed+=1
        assert length<=maximum and off+maximum<=start+size
        props.append(dict(attr=attr,length=length,max_length=maximum,record_data_offset=off,table_offset=table))
    values=[]
    for ident in TARGETS:
        sub,unit=ident>>16,ident&65535
        if sub>=len(subs) or unit>=subs[sub][0]:
            values.append(dict(id=hex(ident),present=False,reason='not in subsystem unit range'));continue
        p=props[subs[sub][1]+unit]
        if p is None:
            values.append(dict(id=hex(ident),present=False,reason='invalid-pointer sentinel'));continue
        assert p['length']==4
        off=base+p['record_data_offset'];value,=struct.unpack_from('<I',data,off)
        values.append(dict(id=hex(ident),present=True,value_u32=value,attribute=p['attr'],
            property_table_file_offset=p['table_offset'],value_file_offset=off,bytes=4,
            raw4_sha256=sha256(data[off:off+4]).hexdigest()))
    return dict(offset=base,record_bytes=start+size,subsystems=ns,property_entries=np,
        data_offset=start,data_bytes=size,checksum_matches=True,all_property_bounds_checked=True,
        fixed_properties=fixed,oversize_properties=oversize,variable_properties=variable,invalid_properties=invalid,
        selected_properties=values),end
results=[]
for row in capture['files']:
    p=R/row['output'];data=p.read_bytes();assert len(data)==row['size'] and sha256(data).hexdigest()==row['sha256']
    first,end=read_record(data,0)
    next_base=(end+4095)&~4095
    assert next_base<len(data) and not any(data[end:next_base])
    second,last=read_record(data,next_base)
    assert last==len(data)
    vals=[x['value_u32'] for x in first['selected_properties'] if x['present']]
    assert vals==[0,4,2]
    assert [x['value_u32'] for x in second['selected_properties'] if x['present']]==[5,4,30]
    results.append(dict(name=Path(row['name']).name,source_sha256=row['sha256'],source_path=row['output'],
        records=[first,second],inter_record_padding_bytes=next_base-end,inter_record_padding_all_zero=True,
        original_full_file_preserved=True))
result=dict(status='CLASSIC_ALCIN_11_TEMPLATES_HAVE_TWO_VALID_RECORDS_WITH_DISTINCT_INPUTS',
    templates=results,all_first_record_values=[0,4,2],all_first_record_values_equal=True,
    all_second_record_values=[5,4,30],all_second_record_values_equal=True,
    target_property_order=[hex(x) for x in TARGETS],selected_source_record=None,
    source_record_role_or_runtime_selection_proven=False,
    default_values_only=True,current_body_values_read=False,HIBIKI2_templates_used=False,
    only_named_property_values_exported=True,Sony_code_or_guest_execution=False,root_or_device_operations=0)
(H/'template-field-results.json').open('x').write(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(templates=len(results),records_checked=2*len(results),record0_values=[0,4,2],record1_values=[5,4,30],
    property_entries_bounds_checked=sum(r['property_entries'] for t in results for r in t['records']),
    actual_camera_operations=0)))
