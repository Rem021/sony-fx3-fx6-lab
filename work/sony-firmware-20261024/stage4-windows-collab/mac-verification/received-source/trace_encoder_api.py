from fx3_native import *
import re
OUT=ROOT/'outputs/h265-path-research'
report=[]
for name in ['/lib/libmpr.so','/lib/libInfraAvbbc.so']:
    n=Native(name);syms=n.symbols();stem=Path(name).name
    (OUT/(stem+'-symbols.json')).write_text(json.dumps(syms,indent=2),encoding='utf-8')
    report.append('\nFILE '+name)
    selected=[s for s in syms if s['defined'] and re.search(r'EncOpen|Enc.*Param|SetCodec|SetEnc|VQuality|Gop|GOP|EncInfo|EncodeInfo|EncFmt|EncFormat',s['name'])]
    report.extend(f"{s['VA']}+{s['size']:x} {s['name']}" for s in selected)
    if 'libmpr' in name:
        targets={0x2829a4,0x282da8,0xcc4d4}
        refs=n.callers(targets)
        for pc,target in refs:
            owner=next((s for s in syms if s['type']=='STT_FUNC' and int(s['VA'],16)<=pc<int(s['VA'],16)+s['size']),{})
            report.append(f"CALL {pc:x}->{target:x} from {owner.get('VA')} {owner.get('name')}")
        plt=n.plt()
        for start,end in [(0x2829a4,0x282da8),(0xd6698,0xd6808)]:
            report.append(f'\nCODE {start:x}-{end:x}')
            for i in n.instructions(start,end):
                extra=''
                if i.mnemonic in ('bl','b') and i.op_str.startswith('#'):
                    addr=int(i.op_str[1:],0)
                    sym=next((s for s in syms if int(s['VA'],16)==addr and s['defined']),{})
                    extra=' ; '+plt.get(addr,sym.get('name',''))
                report.append(f'{i.address:08x}: {i.mnemonic:8} {i.op_str}{extra}')
(OUT/'encoder-api-review.txt').write_text('\n'.join(report),encoding='utf-8')
print('\n'.join(report[:100]))
