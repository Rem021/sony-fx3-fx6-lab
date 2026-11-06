def parse_maps(serial):
    blocks=[];active=None;pos=0
    for line in serial.splitlines(keepends=True):
        stripped=line.strip(); begin=EARLY_BEGIN.fullmatch(stripped); end=EARLY_END.fullmatch(stripped)
        if begin:
            if active:blocks.append(active)
            active={'pid':int(begin[1]),'epoch':int(begin[2]),'rows':[],'complete':False,'byte_start':pos,'byte_end':None}
        elif active is not None:
            if end and int(end[1])==active['pid'] and int(end[2])==active['epoch']:
                active['complete']=True;active['byte_end']=pos+len(line);blocks.append(active);active=None
            else:
                m=MAP.match(stripped)
                if m:active['rows'].append({'start':int(m[1],16),'end':int(m[2],16),'perms':m[3].decode(),'offset':int(m[4],16),'inode':int(m[5]),'path':m[6]})
        pos+=len(line)
    if active:blocks.append(active)
    return blocks

def map_bias(rows,path,loads):
    present=[r for r in rows if r['path']==path]
    if not present or len({r['inode'] for r in present})!=1:raise ValueError('missing/mixed inode')
    if any(r['end']-r['start']<PAGE for r in present):raise ValueError('map row shorter than a page')
    valid=[]
    for bias in {r['start']-seg['va']//PAGE*PAGE for r in present for seg in loads if r['offset']==seg['fileoff']//PAGE*PAGE}:
        good=True
        for seg in loads:
            pageva=seg['va']//PAGE*PAGE;pageoff=seg['fileoff']//PAGE*PAGE
            # Require the page-aligned file-backed extent; a final partial page may
            # legitimately be a guard/protected mapping in the current loader.
            need=bias+pageva+max(PAGE,(seg['filesz']//PAGE)*PAGE)
            rr=[r for r in present if r['offset']>=pageoff and r['offset']<pageoff+seg['filesz'] and r['start']>=bias+pageva and r['start']<need]
            if not rr or min(r['start'] for r in rr)!=bias+pageva:good=False;break
            if any(r['start']-bias-pageva != r['offset']-pageoff for r in rr):good=False;break
            # union must cover the whole file-backed segment (RELRO splits allowed)
            covered=[(r['start'],r['end']) for r in rr]
            end=max(x[1] for x in covered)
            if end<need:good=False;break
            if (seg['flags']&1) and not any('x' in r['perms'] for r in rr):good=False;break
            if (seg['flags']&2) and not any('w' in r['perms'] for r in rr):good=False;break
        if good:valid.append(bias)
    if len(valid)!=1:raise ValueError('ambiguous/incomplete appFw bias '+repr(valid))
    return {'bias':valid[0],'inode':present[0]['inode'],'rows':[{k:(v.decode() if isinstance(v,bytes) else v) for k,v in r.items()} for r in present]}


def choose_appfw(serial,elf_path):
    """Use the LAST early block only; never silently fall back to an older epoch."""
    blocks=parse_maps(serial)
    if not blocks:raise ValueError('no early map block')
    block=blocks[-1]
    if not block['complete']:raise ValueError('newest early map block incomplete')
    try:ap=map_bias(block['rows'],AP_PATH,elf_loads(elf_path))
    except ValueError as exc:raise ValueError('newest early map block invalid: '+str(exc))
    tids=sorted({x.decode() for x in APPFW_TID.findall(serial)})
