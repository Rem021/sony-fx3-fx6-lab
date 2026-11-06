from fx3_native import *
OUT=ROOT/'outputs/h265-path-research'
app=Native('/lib/appFw.so')
pattern=struct.pack('<II',100,12)
matches=[];start=0
while True:
    off=app.blob.find(pattern,start)
    if off<0:break
    start=off+1
    sec=next((s for s in app.sections if s[2]<=off<s[2]+s[1]-s[0]),None)
    if sec is None:continue
    va=sec[0]+off-sec[2]
    pairs=[]
    for pos in range(max(sec[0],va-32),min(sec[1]-8,va+40)+1,8):pairs.append({'ELF_VA':hex(pos),'u32_pair':list(struct.unpack('<II',app.read(pos,8)))})
    matches.append({'ELF_VA':hex(va),'section':sec[3],'nearby_pairs':pairs})
refs=app.string_references({0x968b890})
outside=[{'instruction_ELF_VA':hex(pc),'table_object_ELF_VA':hex(target),'context':app.disasm(pc-32,pc+40)} for pc,target in refs if not 0x2e68048<pc<0x2e69f00]
result={'literal_100_to_12_matches':matches,'quality_map_object_references_outside_converter':outside}
(OUT/'app-quality-map-evidence.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('Matches',len(matches),'refs outside converter',len(outside))
for m in matches:print(m)
for r in outside[:10]:print(r)
