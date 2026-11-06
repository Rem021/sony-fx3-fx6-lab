#!/usr/bin/env python3
"""Original VENICE LMX byte ordering against the pinned FX3 AV table."""
import hashlib,json,struct
from art_matrix_guest import Guest,HERE
from macho_static import MachO


def short(s):
    b=s.encode('ascii');assert len(b)<23
    return b+b'\0'*(23-len(b))+bytes([len(b)])


def string_matrix(g,rows):
    refs=[]
    for row in rows:
        r=g.vector(b''.join(short(s) for s in row),24)
        refs.append(bytes(g.uc.mem_read(r,24)))
    return g.vector(b''.join(refs),24)


def run(g,values):
    words=[[v if v>=0 else (1<<19)+v for v in row] for row in values]
    assert all(0<=v<(1<<19) for row in words for v in row)
    strings=[[f'{v:08X}' for v in row] for row in words]
    inp=string_matrix(g,strings);out=string_matrix(g,[['']*4 for _ in range(9)])
    g.run(0x46dd0,[inp,8,out])
    first=g.uq(out);rows=[]
    for i in range(9):
        p=g.uq(first+24*i);row=[]
        for j in range(4):
            raw=bytes(g.uc.mem_read(p+24*j,24));assert raw[23]==2
            row.append(raw[:2].decode('ascii'))
        rows.append(row)
    binary=bytes.fromhex(''.join(s for row in rows for s in row))
    expected=struct.pack('<9I',*(v for row in words for v in row))
    assert binary==expected
    return dict(input_signed=values,encoded_hex=strings,output_hex_bytes=rows,
                original_instruction_steps=g.steps,imports=g.calls,bytes_hex=binary.hex())


def main():
    source=json.loads((HERE/'art-generator-source.json').read_text());m=MachO(source['path'])
    assert hashlib.sha256(m.file).hexdigest()==source['sha256']
    original=json.loads((HERE.parent/'extraction-results.json').read_text())
    image=__import__('pathlib').Path(original['image']).read_bytes()
    assert hashlib.sha256(image).hexdigest()==original['sha256']
    d=original['selected']['MLUT_MTX_A_REG_VENICE_LMX0_SLOG3_SGAMUT3_ACES']
    payload=image[d['data_offset']:d['data_offset']+d['byte_count']]
    assert hashlib.sha256(payload).hexdigest()==d['sha256']
    fixtures=[('original-fx3-venice',original['matrix']['signed_q16']),
              ('identity',[[65536,0,0],[0,65536,0],[0,0,65536]]),
              ('signed19-edges',[[-262144,262143,-1],[0,1,-65536],[65536,-131072,131071]])]
    rows=[]
    for label,values in fixtures:
        row=run(Guest(m,[0x46dd0]),values);row['case']=label;rows.append(row)
    assert bytes.fromhex(rows[0]['bytes_hex'])==payload[16:]
    result=dict(source_sha256=source['sha256'],serializer_entry='0x46dd0',
                fx3_original_sha256=original['sha256'],fx3_descriptor=d['name'],
                fx3_payload_file_offset=d['data_offset'],fx3_payload_sha256=d['sha256'],
                fx3_four_control_words=list(struct.unpack('<4I',payload[:16])),
                cases=rows,all_nine_existing_coefficient_words_match=True,
                limits=['Signed-negative to 19-bit hex preparation follows statically observed Basic_Info::dec2hexa_keta; that formatter was not executed here.',
                        'The original LMX_data2byte substring selection, loop indices and stores were executed; short-string substring construction is a host shim.',
                        'Only nine coefficient words match. FX3 control words, descriptors, stage routing, register addresses and sensor/ISP behavior are not a VENICE camera ABI.',
                        'No changed firmware or camera writes were produced.'])
    (HERE/'matrix-serialization-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'cases':len(rows),'fx3_existing_words_matched':9,'bytes':len(payload)-16,'native_library_loaded':False,'camera_actions':0}))

if __name__=='__main__':main()
