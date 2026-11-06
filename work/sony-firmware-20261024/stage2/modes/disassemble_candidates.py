# Historical optional probe. Requires Capstone5.0.6 and fixed upstream appfw_elf.py; see tool-provenance.json.
# The supported dependency-free reproduction is inspect_mode_routes.py.
import sys,pathlib,json,re,struct
sys.path.insert(0,str(pathlib.Path(__file__).parent/'references'))
from appfw_elf import AppElf
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
p=pathlib.Path(__file__).parents[1]/'extraction/files/nflasha15/lib/appFw.so';e=AppElf(p);md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);out=pathlib.Path(__file__).parent
for n,va,sz in [('main-params',0x2e68048,0x1f38),('frame-rate-dispatch',0x2a4f280,0x100),('vpc-enum-name',0x2e54074,0xc4),('main-params-callers',0x2e69f80,0xb00)]:
 off=e.offset(va);ls=[f'{a:#x} {m:<7} {o}' for a,s,m,o in md.disasm_lite(e.data[off:off+sz],va)];(out/(n+'.asm')).write_text('\n'.join(ls)+'\n')
r=[]
for text in ['VAL_setting_file_format_FILE_FOMRAT_XAVC_HS_4K','VAL_setting_file_format_FILE_FORMAT_XAVC_S_HD','FILE_FORMAT_XAVC_HS_4K','FILE_FOMRAT_XAVC_HS_4K','FILE_FORMAT_XAVC_S_HD','PRM_setting_file_format','PRM_setting_movie_rec_frame_rate_xavc_hs_4k']:
 r.append({'text':text,'records':e.name_records(text),'strings':[hex(x) for x in e.find_cstr(text)]})
(out/'selected-name-records.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
