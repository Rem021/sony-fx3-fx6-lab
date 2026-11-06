# Historical optional probe. Requires Capstone5.0.6 and fixed upstream appfw_elf.py; see tool-provenance.json.
# The supported dependency-free reproduction is inspect_mode_routes.py.
"""Read-only xref/disassembly probe of fixed FX3 appFw. Helper source is pinned in provenance.
No firmware code is executed. Emits candidate locations, not a patch or execution proof.
"""
import sys,pathlib,json,re,hashlib
sys.path.insert(0,str(pathlib.Path(__file__).parent/'references'))
from appfw_elf import AppElf
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
p=pathlib.Path(__file__).parents[1]/'extraction/files/nflasha15/lib/appFw.so'
e=AppElf(p)
if hashlib.sha256(e.data).hexdigest()!='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f':raise ValueError('Wrong base')
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
def dis(va,sz):
 off=e.offset(va);return [{'va':hex(a),'bytes':e.data[off+a-va:off+a-va+s].hex(),'op':m+' '+o} for a,s,m,o in md.disasm_lite(e.data[off:off+sz],va)]
rows=[]
strings=[]
s=e.by_name['.rodata']
for m in re.finditer(rb'[ -~]{6,}',e.data[s['offset']:s['offset']+s['size']]):
 text=m.group().decode()
 if ('convert2Movie' in text or 'determine_movie_rec_frame_rate(' in text or text in ['VPC_HEVC_1920x1080_420_10BIT_LONG','VPC_HEVC_1920x1080_422_10BIT_LONG','REC_FRAME_RATE_30P','FILE_FOMRAT_XAVC_HS_4K','FILE_FORMAT_XAVC_S_HD']):strings.append((s['addr']+m.start(),text))
for va,text in strings:
 refs=e.adrp_refs(va);nr=e.name_records(text)
 row={'va':hex(va),'text':text,'relocated_refs':[hex(x) for x in e.reloc_addend_to_targets.get(va,[])],'name_records':nr,'code_refs':[hex(x) for x in refs],'candidate_functions':[]}
 for x in refs[:6]:
  fn=e.function_start(x)
  row['candidate_functions'].append({'start':hex(fn),'ref':hex(x),'callers':[hex(a) for a in e.callers(fn)[:30]],'disassembly_near_ref':dis(max(e.text[0],x-64),200),'prologue':dis(fn,128)})
 rows.append(row)
 print(hex(va),text[:100], 'refs',len(refs),[hex(x) for x in refs])
(pathlib.Path(__file__).parent/'function-candidates.json').write_text(json.dumps({'input_sha256':hashlib.sha256(e.data).hexdigest(),'candidates':rows},indent=2))
