#!/usr/bin/env python3
"""Offline raw guest physical memory -> PNG. Never opens QMP or /dev/mem.
JSON contract and evidence limits: README.md. No third-party dependencies.
"""
import argparse, json, struct, zlib, binascii
from pathlib import Path

def num(v):
    if isinstance(v,bool): raise ValueError('boolean is not an integer')
    return int(v,0) if isinstance(v,str) else int(v)

def render(raw, cfg):
    base=num(cfg['dump_base']); w=num(cfg['width']); h=num(cfg['height'])
    if base<0 or w<=0 or h<=0 or w*h>16777216: raise ValueError('invalid canvas/base')
    out=[tuple(cfg.get('background',[0,0,0,0]))]*(w*h)
    if any(len(p)!=4 or any(not isinstance(x,int) or not 0<=x<=255 for x in p) for p in out[:1]):raise ValueError('bad background')
    planes=cfg['planes'];zs=[num(p['z']) for p in planes]
    if len(set(zs))!=len(zs):raise ValueError('ambiguous duplicate z')
    for p in sorted(planes,key=lambda p:num(p['z'])):
        pw=num(p['width']);ph=num(p['height']);stride=num(p['stride_pixels']);addr=num(p['address']);x=num(p['x']);y=num(p['y'])
        fmt=p['format'];order=p['component_order'];mode=p['alpha_mode'];ga=num(p['global_alpha'])
        if sorted(order)!=sorted('RGBA') or len(order)!=4:raise ValueError('explicit RGBA permutation required')
        if fmt not in ['format0-le16','format1-le32']:raise ValueError('unsupported format')
        if mode not in ['straight','opaque']:raise ValueError('unverified alpha mode')
        if not 0<=ga<=255 or pw<=0 or ph<=0 or stride<pw or pw*ph>16777216:raise ValueError('invalid plane')
        bpp=2 if fmt=='format0-le16' else 4;off=addr-base
        if off<0 or off+((ph-1)*stride+pw)*bpp>len(raw):raise ValueError('plane outside captured dump')
        for py in range(ph):
            for px in range(pw):
                pos=off+(py*stride+px)*bpp;value=int.from_bytes(raw[pos:pos+bpp],'little')
                if bpp==2:cs=[((value>>shift)&15)*17 for shift in [12,8,4,0]]
                else:cs=[(value>>shift)&255 for shift in [24,16,8,0]]
                c=dict(zip(order,cs));sa=(255 if mode=='opaque' else c['A'])*ga
                # sa denominator=65025; straight-alpha source-over, rounded once per channel.
                dx=x+px;dy=y+py
                if not(0<=dx<w and 0<=dy<h):continue
                di=dy*w+dx;d=out[di];den=sa*255+d[3]*(65025-sa)
                a=(den+32512)//65025
                rgb=[(c[k]*sa*255+d[j]*d[3]*(65025-sa)+den//2)//den if den else 0 for j,k in enumerate('RGB')]
                out[di]=tuple(rgb+[a])
    return w,h,bytes(v for pixel in out for v in pixel)

def png_bytes(w,h,rgba):
    def chunk(tag,data):return struct.pack('>I',len(data))+tag+data+struct.pack('>I',binascii.crc32(tag+data)&0xffffffff)
    rows=b''.join(b'\0'+rgba[y*w*4:(y+1)*w*4] for y in range(h))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')

def self_test():
    # >4GiB, little-endian nibble order, padding, layering and clipped negative x.
    cfg={'dump_base':'0x43feb5000','width':2,'height':2,'planes':[]}
    p={'address':'0x43feb5004','width':2,'height':2,'stride_pixels':3,'format':'format0-le16','component_order':'RGBA','alpha_mode':'straight','global_alpha':255,'x':0,'y':0,'z':0}
    raw=b'head'+struct.pack('<6H',0xf00f,0x0f0f,0xdead,0x00ff,0xffff,0xbeef)
    cfg['planes']=[p];w,h,pix=render(raw,cfg)
    expected=bytes([255,0,0,255,0,255,0,255,0,0,255,255,255,255,255,255]);assert pix==expected
    overlay={**p,'address':hex(num(cfg['dump_base'])+len(raw)),'width':1,'height':1,'stride_pixels':1,'format':'format1-le32','global_alpha':128,'z':1}
    raw+=struct.pack('<I',0x0000ffff);cfg['planes'].append(overlay)
    assert render(raw,cfg)[2][:4]==bytes([127,0,128,255])
    overlay['x']=-1;assert render(raw,cfg)[2]==expected;overlay['x']=0
    # Transparent source over transparent destination stays zero; forced opaque and channel permutation.
    q={**p,'width':1,'height':1,'stride_pixels':1,'component_order':'ARGB','address':cfg['dump_base']}
    c={'dump_base':cfg['dump_base'],'width':1,'height':1,'planes':[q]}
    assert render(struct.pack('<H',0xf123),c)[2]==bytes([17,34,51,255])
    q['component_order']='RGBA';assert render(b'\0\0',c)[2]==bytes(4)
    q['alpha_mode']='opaque';assert render(b'\0\0',c)[2]==bytes([0,0,0,255])
    failures=0
    for key,value in [('address','0x43feb4fff'),('stride_pixels',0),('format','format3'),('component_order','RRGA'),('alpha_mode','premultiplied')]:
        bad={**p,key:value}
        try:render(raw,{**cfg,'planes':[bad]})
        except ValueError:failures+=1
        else:raise AssertionError(key)
    image=png_bytes(w,h,expected);assert image.startswith(b'\x89PNG');assert b'\0'+expected[:8]+b'\0'+expected[8:] == zlib.decompress(image[41:-16])
    out=Path(__file__).resolve().parent
    (out/'synthetic.raw').write_bytes(raw);(out/'synthetic-planes.json').write_text(json.dumps(cfg,indent=2)+'\n');(out/'synthetic.png').write_bytes(png_bytes(*render(raw,cfg)))
    (out/'self-test.json').write_text(json.dumps({'passed':True,'checks':['4444 channels/endian/row padding','>4GiB dump offset','8888 source-over 128','negative placement clipping','ARGB permutation','transparent and opaque','PNG decompression'], 'negative_cases':failures,'physical_guest_frame':False},indent=2)+'\n')
    print('PASS: offline decoder synthetic pixel/PNG checks and 5 rejection cases')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('raw',nargs='?');ap.add_argument('planes',nargs='?');ap.add_argument('output',nargs='?');ap.add_argument('--self-test',action='store_true');a=ap.parse_args()
    if a.self_test:self_test();return
    if not all([a.raw,a.planes,a.output]):ap.error('raw planes.json output.png required')
    w,h,rgba=render(Path(a.raw).read_bytes(),json.loads(Path(a.planes).read_text()));Path(a.output).write_bytes(png_bytes(w,h,rgba));print(f'Wrote {w}x{h} PNG; offline interpretation only')
if __name__=='__main__':main()
