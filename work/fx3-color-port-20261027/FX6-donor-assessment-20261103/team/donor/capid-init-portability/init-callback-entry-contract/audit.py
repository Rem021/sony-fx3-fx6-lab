"""Recheck originals, old deliverables and each excerpt word; write only this directory."""
import sys
sys.dont_write_bytecode=True
import json, re, struct, ast
from trace import E, P, H, B, sha
from test_subset import run

def main():
    old=[]
    for rel,key in [('delivery-manifest.json','files'),('callback-contracts/receipt.json','artifacts'),
                    ('poweron-contract/receipt.json','artifacts'),('init-u16-contract/receipt.json','artifacts')]:
        p=B/rel; data=json.loads(p.read_text()); verified={}
        for name,meta in data[key].items():
            q=p.parent/name; digest=sha(q.read_bytes());assert digest==meta['sha256'],str(q)
            verified[name]=digest
        old.append({'manifest':rel,'manifest_sha256':sha(p.read_bytes()),'files_verified':verified})
    words={};excerpts={}
    for p in sorted(H.glob('*.txt')):
        match=re.fullmatch(r'(fx[36]_(?:mpr|ap))-([0-9a-f]+)-([0-9a-f]+)\.txt',p.name)
        if not match:continue
        k,start,end=match.groups(); lines=[]
        for line in p.read_text().splitlines():
            m=re.match(r'\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.*)',line)
            if not m:continue
            va=int(m[1],16);w=int(m[2],16);mapping=E[k].mapping(va)
            assert int.from_bytes(bytes.fromhex(mapping['bytes_le']),'little')==w,(p.name,line)
            words[f'{k}:{va:x}']={**mapping,'machine_word':m[2],'instruction':m[3]}
            lines.append(va)
        excerpts[p.name]={'start':E[k].mapping(int(start,16)),'end_exclusive':hex(int(end,16)),
                          'instructions':len(lines),'sha256':sha(p.read_bytes())}
    targets={'fx3_mpr':[0x2f9438,0x2faaa0,0x2fa470,0x2fa250,0x2fa118,0x2facd0,0x2faf28,
                         0x2fa548,0x2f9788,0x2f9df8,0x2f9eb0],
             'fx6_mpr':[0x108d0f0,0x108cd80,0x108cfc0]}
    relocations=[]
    for k,ts in targets.items():
        e=E[k];sy=e.named['.dynsym'];st=e.sections[sy[6]];ss=e.b[st[4]:st[4]+st[5]]
        for s in e.sections:
            if s[1]!=4:continue
            for off in range(s[4],s[4]+s[5],24):
                va,info,add=struct.unpack_from('<QQq',e.b,off)
                if va not in ts:continue
                n,i,o,sh,v,z=struct.unpack_from('<IBBHQQ',e.b,sy[4]+(info>>32)*sy[9])
                relocations.append({'input':k,'slot':e.mapping(va,8),'relocation_fileoff':hex(off),
                    'raw_rela':e.b[off:off+24].hex(),'type':info&0xffffffff,'addend':hex(add),
                    'symbol':ss[n:].split(b'\0')[0].decode(),'symbol_value':hex(v),'symbol_size':z,
                    'runtime_binding_proven':False})
    matrix=json.loads((B/'callback-contracts/matrix.json').read_text())
    rec=next(r for r in matrix if 'RecPbTime' in r['symbol'])
    event=rec['event_dispatch'][0];jump=event['jump_entry']
    assert E['fx3_mpr'].mapping(int(jump['va'],16),2)==jump
    graph=json.loads((B/'callback-contracts/sync-graph.json').read_text())
    (H/'evidence.json').write_text(json.dumps({'instructions':words,'excerpts':excerpts,'relocations':relocations,
        'reused_callback_registration':rec['callbacks'],'reused_event_dispatch':event,
        'reused_sync_graph_sha256':sha((B/'callback-contracts/sync-graph.json').read_bytes()),
        'reused_internal_codec_registrations':[r for r in graph['edges'] if 'SetCbFunc' in r['symbol']],
        'initial_broadcast_create_flag':E['fx3_mpr'].mapping(0x2ff0d1,1)},indent=2)+'\n')
    fixtures=run()
    for p in H.glob('*.py'):ast.parse(p.read_text())
    receipt={'status':'PARTIAL_STATIC_ENTRY_CONTRACT_WITH_REJECTING_OFFLINE_RECORD_SUBSET',
        'fixed_inputs':{k:{'path':str(P[k]),'sha256':sha(e.b)} for k,e in E.items()},
        'old_deliveries':old,'unique_instruction_words_verified':len(words),'excerpt_count':len(excerpts),
        'offline_positive':len(fixtures['positive_cases']),'offline_rejected':len(fixtures['rejected_cases']),
        'elf_execution':False,'stubs':[],'vm_device_or_firmware_mutation':False,
        'decision':'No general Init adapter yet; record-only 60B snapshot conversion is conditional and rejects unknowns',
        'artifacts':{p.name:{'sha256':sha(p.read_bytes()),'size':p.stat().st_size} for p in sorted(H.iterdir())
                     if p.is_file() and p.name!='receipt.json'}}
    (H/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'verified_originals':len(E),'old_files':sum(len(x['files_verified']) for x in old),
                     'unique_words':len(words),'excerpts':len(excerpts)}))
if __name__=='__main__':main()
