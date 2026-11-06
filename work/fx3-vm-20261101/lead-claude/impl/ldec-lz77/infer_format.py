#!/usr/bin/env python3
"""Reproduce format candidate rejection and independent length-table inference.

Reads fixed FX3 originals. Only writes results/format_inference.json.
No numpy or external solver; Gaussian elimination on normal equations.
"""
import collections
import hashlib
import itertools
import json
from pathlib import Path
from resource_tools import ROOT, RESOURCES, uxd_records
from decode_ldec import decode_details, rgba4444, DecodeError


def token_counts(src):
    if src[0] != 0xf0: raise ValueError("not f0")
    p, literals, counts = 1, 0, [0]*16
    while p < len(src):
        flags = src[p]; p += 1
        for bit in range(8):
            if flags >> bit & 1:
                if p + 2 > len(src): raise ValueError("truncated")
                first, second = src[p:p+2]; p += 2
                if ((first & 15) << 8 | second) == 0:
                    if p != len(src): raise ValueError("multiple blocks")
                    return literals,counts
                counts[first >> 4] += 1
            else:
                if p == len(src): raise ValueError("truncated")
                p += 1; literals += 1
    raise ValueError("missing terminator")


def generic_lzss(src, expected, skip, msb, literal_bit, endian, length_high, bias, distance_bias):
    p, out = skip, bytearray()
    while p < len(src):
        flags = src[p]; p += 1
        for bit in range(8):
            if p >= len(src): return bytes(out)
            if (flags >> (7-bit if msb else bit)) & 1 == literal_bit:
                out.append(src[p]); p += 1
            else:
                if p + 2 > len(src): return None
                word = int.from_bytes(src[p:p+2],endian); p += 2
                if word == 0: return bytes(out)
                code = word >> 12 if length_high else word & 15
                distance = word & 4095 if length_high else word >> 4
                distance += distance_bias
                if not 1 <= distance <= len(out): return None
                for _ in range(code+bias): out.append(out[-distance])
            if len(out) > expected: return None
    return bytes(out)


def nintendo_lz11(src, skip):
    p, out = skip, bytearray()
    while p < len(src):
        flags=src[p];p+=1
        for bit in range(7,-1,-1):
            if p>=len(src): return bytes(out)
            if flags >> bit & 1:
                a=src[p];p+=1;code=a>>4
                if code==0:
                    if p+2>len(src):return None
                    b,c=src[p:p+2];p+=2;length=((a&15)<<4 | b>>4)+17;dist=((b&15)<<8|c)+1
                elif code==1:
                    if p+3>len(src):return None
                    b,c,d=src[p:p+3];p+=3;length=((a&15)<<12|b<<4|c>>4)+273;dist=((c&15)<<8|d)+1
                else:
                    if p==len(src):return None
                    b=src[p];p+=1;length=code+1;dist=((a&15)<<8|b)+1
                if dist>len(out) or len(out)+length>1000000:return None
                for _ in range(length):out.append(out[-dist])
            else:out.append(src[p]);p+=1
    return bytes(out)


def main():
    data=(RESOURCES/'image_02_43.uxc').read_bytes()
    small=[r for r in uxd_records(data) if r['output_bytes']<=4096]
    eq=[]
    for r in small:
        s=r['source_offset'];src=data[s:s+r['source_bytes']]
        literals,counts=token_counts(src)
        eq.append((counts,r['output_bytes']-literals))
    a=[[float(sum(c[k]*c[j] for c,y in eq)) for j in range(16)]+
       [float(sum(c[k]*y for c,y in eq))] for k in range(16)]
    rank=0
    for j in range(16):
        pivot=max(range(j,16),key=lambda k:abs(a[k][j]))
        a[j],a[pivot]=a[pivot],a[j]
        fac=a[j][j]
        if abs(fac)<1e-8:continue
        rank+=1;a[j]=[x/fac for x in a[j]]
        for k in range(16):
            if k!=j:
                f=a[k][j];a[k]=[x-f*y for x,y in zip(a[k],a[j])]
    solved=[r[-1] for r in a];rounded=[round(x) for x in solved]
    residuals=[sum(x*y for x,y in zip(c,rounded))-target for c,target in eq]
    assert rank==16 and not any(residuals) and rounded==list(range(3,17))+[32,64]
    screen=sorted(small,key=lambda r:r['source_bytes'])[:24]+small[::max(1,len(small)//16)][:16]
    samples=[(r,data[r['source_offset']:r['source_offset']+r['source_bytes']]) for r in screen]
    candidates=[]
    for params in itertools.product(range(5),range(2),range(2),('big','little'),range(2),(1,2,3,4),range(2)):
        exact=sum((out is not None and len(out)==r['output_bytes']) for r,s in samples
                  for out in [generic_lzss(s,r['output_bytes'],*params)])
        candidates.append({'parameters':params,'exact_lengths':exact})
    candidates.sort(key=lambda x:x['exact_lengths'],reverse=True)
    nintendo=[]
    for skip in (0,1,4):
        score=sum((out is not None and len(out)==r['output_bytes']) for r,s in samples for out in [nintendo_lz11(s,skip)])
        nintendo.append({'variant':'LZ11','skip':skip,'exact_lengths':score})
    exact=0;metrics=[]
    for r,src in samples:
        raw,info=decode_details(src,r['output_bytes']);exact+=len(raw)==r['output_bytes']
        rgba=rgba4444(raw,r['width'],r['height'])
        metrics.append({'index':r['index'],'alpha_histogram':dict(collections.Counter(rgba[3::4])),
                        'adjacent_rgba_equal_fraction':sum(rgba[i:i+4]==rgba[i-4:i] for i in range(4,len(rgba),4))/max(1,len(rgba)//4-1)})
    result={'corpus':'image_02_43.uxc','sha256':hashlib.sha256(data).hexdigest(),
            'small_records':len(eq),'linear_system_rank':rank,'least_squares_values':solved,
            'inferred_length_table':rounded,'all_constraints_exact':not any(residuals),
            'screen_size':len(screen),'generic_parameter_order':['skip','msb_first','literal_bit','byte_order','length_high_nibble','length_bias','distance_bias'],
            'generic_variants_tested':len(candidates),'best_generic_variants':candidates[:10],
            'nintendo_lz10_note':'covered by MSB flags, big endian, high nibble length+3, distance+1 in generic grid',
            'nintendo_lz11':nintendo,'nintendo_header_magic_matches':sum(src[0] in (0x10,0x11) for _,src in samples),
            'sony_exact_lengths':exact,'sony_pixel_metrics':metrics,
            'limits':'Length equations identify the table given the tested flag/token framing; full corpus and primary public source corroborate framing. Pixel statistics are plausibility, not an independent hardware oracle.'}
    (ROOT/'results/format_inference.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(f"Format inference: rank {rank}, {len(eq)}/{len(eq)} constraints; generic best {candidates[0]['exact_lengths']}/{len(screen)}, Sony {exact}/{len(screen)}",flush=True)


if __name__=='__main__':main()
