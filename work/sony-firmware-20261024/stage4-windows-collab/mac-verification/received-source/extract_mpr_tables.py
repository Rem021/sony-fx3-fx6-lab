from fx3_native import *
OUT=ROOT/'outputs/h265-path-research'
m=Native('/lib/libmpr.so')
comb=struct.unpack('<78I',m.read(0x2cb108,312))
rows=[{'ordinal':i,'raw_six_u32':list(comb[i*6:i*6+6])} for i in range(13)]
quality=struct.unpack('<52I',m.read(0x2e0a70,208))
qualities=[{'DefStruct_VQuality':i+2,'raw_GetVideoBitrate':v} for i,v in enumerate(quality)]
(OUT/'mpr-basic-tables.json').write_text(json.dumps({'video_param_combinations':rows,'quality_to_bitrate':qualities},indent=2),encoding='utf-8')
print('Combination records:',rows)
print('Bitrate table:',qualities)
print('CheckMovieRecParam:',m.disasm(0xcc4d4,0xcc540))
