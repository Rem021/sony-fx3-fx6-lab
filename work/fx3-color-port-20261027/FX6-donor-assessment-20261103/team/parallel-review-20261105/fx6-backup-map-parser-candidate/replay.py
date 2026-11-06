#!/usr/bin/env python3
"""Incremental offline replay at explicit logical-line cut points."""
import json,sys
from pathlib import Path
import mapping_parser as M

def run(serial, cuts, contract='official_im_elf'):
    data=Path(serial).read_bytes(); lines=data.splitlines(keepends=True); out={'schema':'fx6-map-parser-replay-v1','serial':str(serial),'producer_contract':contract,'cuts':[]}
    for n in cuts:
        seg=b''.join(lines[:n]); p=M.MappingProvider(producer_contract=contract)
        try:
            v=p.select(seg);out['cuts'].append({'lines':n,'status':'accepted','block_span':v['block_span'],'bias':hex(v['ap']['bias'])})
        except M.MapParserError as e:
            d=e.as_dict();out['cuts'].append({'lines':n,'status':'blocked','reason':d['code'],'block':d['block'],'diagnostics':d['diagnostics']})
    return out
if __name__=='__main__':
    serial=sys.argv[1];cuts=[int(x) for x in sys.argv[2].split(',')];contract=sys.argv[3] if len(sys.argv)>=5 else 'official_im_elf';dest=sys.argv[4] if len(sys.argv)>=5 else sys.argv[3]
    o=run(serial,cuts,contract);Path(dest).write_text(json.dumps(o,indent=2)+'\n');print(json.dumps(o,indent=2))
