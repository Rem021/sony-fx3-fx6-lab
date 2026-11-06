from fx3_native import *
import re
OUT=ROOT/'outputs/h265-path-research';OUT.mkdir(exist_ok=True)
app=Native('/lib/appFw.so');mpr=Native('/lib/libmpr.so')
calls=app.callers({0x2e68048,0x2e68010})
report=[];rows=[]
for pc,target in calls:
    if target==0x2e68010 and 0x2e68048<pc<0x2e6a000:continue
    row={'call_ELF_VA':hex(pc),'target_ELF_VA':hex(target),'context':app.disasm(max(app.base,pc-64),pc+96)}
    rows.append(row);report.append('\nCALL '+hex(pc)+' -> '+hex(target));report.extend(row['context'])
(OUT/'converter-callers.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('Converter and nonlocal quality-map callers:',[(hex(a),hex(b)) for a,b in calls if b==0x2e68048 or not 0x2e68048<a<0x2e6a000])
relevant=[s for s in mpr.symbols() if re.search(r'movie|video|quality|framerate|recparam|format|encod|gop|bitrate|comb',s['name'],re.I)]
(OUT/'mpr-relevant-symbols.json').write_text(json.dumps(relevant,indent=2),encoding='utf-8')
for s in relevant:
    if s['defined']:report.append(f"MPR {s['VA']} +{s['size']:x} {s['name']}")
strings=[]
for sec in mpr.elf.iter_sections():
    if sec.name not in ('.rodata','.data.rel.ro'):continue
    for match in re.finditer(rb'[\x20-\x7e]{5,}\x00',sec.data()):
        text=match.group()[:-1].decode('ascii')
        if re.search(r'hevc|h265|avc|VideoParamComb|quality|bitrate|gop|v_frame_rate|video_param|record.*param|check.*param',text,re.I):
            strings.append({'ELF_VA':hex(sec['sh_addr']+match.start()),'text':text})
(OUT/'mpr-encoding-strings.json').write_text(json.dumps(strings,indent=2),encoding='utf-8')
(OUT/'initial-downstream-review.txt').write_text('\n'.join(report),encoding='utf-8')
print('MPR relevant symbols',len(relevant),'selected strings',len(strings))
print('\n'.join(report[-80:]))
