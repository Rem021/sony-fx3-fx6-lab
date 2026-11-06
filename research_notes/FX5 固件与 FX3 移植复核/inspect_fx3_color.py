from pathlib import Path
import json, re, struct, plistlib, subprocess

ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024')
OUT=Path(__file__).parent
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
files={'av-cam':'nflasha3/av-cam.bin','appFw':'nflasha15/lib/appFw.so','CP':'nflasha8/cpapp-b.bin'}
patterns={
 'white_balance_control':r'white.?balance|\bAWB\b|wb_mode|WB_GAIN',
 'CCM_named':r'color.?matrix|colour.?matrix|\bCCM\b',
 'monitor_look_stages':r'MLUT_(?:YC2RGB|L1D_[ABC]_ON|MTX_[ABCD]_ON|EIGAIN|YR1D|L3D_ON)|ddl_VfxSetMlut|3D-Lut table Write',
 'VENICE_named_look':r'MLUT_.*VENICE.*(?:SLOG3|SGAMUT|3DLUT)',
 'gamma_gamut':r'S.?Log3|S.?Gamut3|S.?Cinetone|EX_GAMMA_TABLE',
 'user_LUT':r'read3DLUTFile|model_user_lut_files|LUT%03d',
 'imaging_wrapper':r'infra_wrapper_imaging::.*(?:picture_profile|white_balance|gamma|noise)',
 'imager_calibration':r'Imager.*[Cc]alibrat|ExecImagerCalibration|CalibrationCallbackCamCore|sjob_get_black_level|BAD.?PIXEL|DEFECT.?PIXEL|DEMOSAIC|DEBAYER',
}
result={'scope':'Bounded static printable strings and ELF header/section metadata only. A string, function-name trace or VENICE label does not prove implementation recovery, active pipeline, table values, sensor calibration or color equivalence. Existing hashes reused, no repeated whole-file hashing.','modules':{}}
old=json.loads((OUT/'fx3-static-chain-receipt.json').read_text())
manifest=json.loads((ROOT/'stage2/extraction/extracted-manifest.json').read_text())
for label,rel in files.items():
 b=(ROOT/'stage2/extraction/files'/rel).read_bytes()
 info={'path':str(ROOT/'stage2/extraction/files'/rel),'bytes':len(b),'first16_hex':b[:16].hex(),'has_ELF_header':b[:4]==b'\x7fELF','patterns':{}}
 if label in old['files']:info['previously_verified_sha256']=old['files'][label]['sha256']
 else:info['source_manifest_sha256']=next(x['sha256'] for x in manifest if x.get('path')=='/cpapp-b.bin')
 if info['has_ELF_header']:
  e=struct.unpack_from('<16sHHIQQQIHHHHHH',b)
  sections=[struct.unpack_from('<IIQQQQIIQQ',b,e[6]+i*e[11]) for i in range(e[12])]
  info['ELF_machine']=e[2]
  info['ELF_symbol_tables']=[{'type':s[1],'bytes':s[5],'entries':s[5]//s[9]} for s in sections if s[1] in (2,11)]
  info['color_named_ELF_symbols']=[]
  for sec in sections:
   if sec[1] not in (2,11): continue
   stsec=sections[sec[6]]
   st=b[stsec[4]:stsec[4]+stsec[5]]
   for pos in range(sec[4],sec[4]+sec[5],sec[9]):
    name,sinfo,other,shndx,value,size=struct.unpack_from('<IBBHQQ',b,pos)
    text=st[name:st.find(b'\0',name)].decode('ascii','replace')
    if re.search(r'awb|white.?balance|mlut|3dlut|gamut|picture.?profile|calibrat|demosaic|debayer',text,re.I):
     info['color_named_ELF_symbols'].append({'name':text,'value':hex(value),'defined':shndx!=0,'size':size})
 strings=[(m.start(),m.group().decode()) for m in re.finditer(rb'[\x20-\x7e]{5,300}',b)]
 for name,pattern in patterns.items():
  matches=[{'file_offset':hex(offset),'text':text} for offset,text in strings if re.search(pattern,text,re.I)]
  info['patterns'][name]={'regex':pattern,'total':len(matches),'first_matches':matches[:40]}
 result['modules'][label]=info
(OUT/'fx3-color-static-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for label,info in result['modules'].items():
 print(label,{k:v['total'] for k,v in info['patterns'].items()})
 for k in ['imager_calibration','imaging_wrapper','monitor_look_stages']:
  print(k,json.dumps(info['patterns'][k]['first_matches'][:5],ensure_ascii=False))
