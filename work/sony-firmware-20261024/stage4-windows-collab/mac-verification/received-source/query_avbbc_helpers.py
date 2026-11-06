from fx3_native import *
OUT=ROOT/'outputs/h265-path-research'
n=Native('/lib/libInfraAvbbc.so');plt=n.plt();defined={s['name']:s for s in n.symbols() if s['defined'] and s['name']}
targets=[0x9c330,0x9db50,0x9c910,0x9bf70,0x9edd0]
rows=[]
for a in targets:
    name=plt.get(a);s=defined.get(name,{})
    rows.append({'plt_ELF_VA':hex(a),'symbol':name,'implementation_ELF_VA':s.get('VA'),'size':s.get('size')})
(OUT/'avbbc-parameter-helper-symbols.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows,indent=2))
