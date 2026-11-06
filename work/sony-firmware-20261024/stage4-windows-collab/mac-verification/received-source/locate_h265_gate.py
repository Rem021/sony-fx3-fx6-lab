from fx3_native import *
import re
OUT=ROOT/'outputs/h265-path-research'
app=Native('/lib/appFw.so')
ro=app.elf.get_section_by_name('.rodata');raw=ro.data();base=ro['sh_addr']
targets={}
for match in re.finditer(rb'[\x20-\x7e]{5,}\x00',raw):
    label=match.group()[:-1].decode('ascii')
    if label.startswith('PRM_HAITA_setting_file_format') and 'frame_rate' in label:
        targets[base+match.start()+4]=label[4:]
rows=[]
for rel in app.elf.get_section_by_name('.rela.dyn').iter_relocations():
    if rel['r_info_type']!=1027 or rel['r_addend'] not in targets:continue
    off,add=rel['r_offset'],rel['r_addend']
    packed,length=struct.unpack('<QQ',app.read(off-16,16))
    rows.append({'name':targets[add],'reference_ELF_VA':hex(off),'model_parameter_id':hex(packed>>32),'kind':packed&0xffffffff,'declared_name_length':length,'actual_length_including_nul':len(targets[add])+1})
(OUT/'frame-availability-gate-parameters.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(rows)
