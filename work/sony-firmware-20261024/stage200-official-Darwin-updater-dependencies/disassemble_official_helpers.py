"""Decode original helper ELF files, including PLT relocation and unwind ranges."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from capstone.arm64 import ARM64_OP_IMM,ARM64_OP_REG,ARM64_OP_MEM
from elftools.elf.elffile import ELFFile
from elftools.dwarf.callframe import FDE
H=Path(__file__).resolve().parent
FILES=[('historical2.05-init',H/'originals/historical2.05-p1/usr/bin/ud_darwin_init.elf',
        'c943c7462e4d94b834b891555a2224c4a2c34d722204368e66d6d97d3eca91ad'),
       ('official7.02-firmup',H/'originals/official7.02-Ubody/bin/ud_darwin_firmup.elf',
        'f0b0fd8fd1fd3c2c348744faeb9b0267668b99ebf5875560ef2fd7dddb424ea8')]
c=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);c.detail=True
def put(n,v):
    with (H/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def canonical(i,reg):
    n=i.reg_name(reg)
    return 'x'+n[1:] if n.startswith('w') else n
results=[]
for label,path,expected in FILES:
    data=path.read_bytes();assert sha256(data).hexdigest()==expected
    e=ELFFile(BytesIO(data));assert e['e_machine']=='EM_AARCH64'
    def raw_at(a,n):
        for p in e.iter_segments():
            if p['p_type']=='PT_LOAD' and p['p_vaddr']<=a and a+n<=p['p_vaddr']+p['p_filesz']:
                off=p['p_offset']+a-p['p_vaddr'];return data[off:off+n]
        return None
    def str_at(a):
        out=bytearray()
        for k in range(180):
            b=raw_at(a+k,1)
            if b==b'\0':break
            if b is None or b[0] not in (9,10,13) and not 32<=b[0]<127:return None
            out.extend(b)
        else:return None
        return out.decode('ascii') if len(out)>=4 else None
    slots={}
    rel=e.get_section_by_name('.rela.plt')
    if rel:
        sy=e.get_section(rel['sh_link'])
        slots={r['r_offset']:sy.get_symbol(r['r_info_sym']).name for r in rel.iter_relocations()}
    plt={};ps=e.get_section_by_name('.plt');pi=list(c.disasm(ps.data(),ps['sh_addr']))
    for k,i in enumerate(pi[:-1]):
        n=pi[k+1]
        if i.mnemonic=='adrp' and i.op_str.startswith('x16,') and n.mnemonic=='ldr' and n.op_str.startswith('x17,'):
            slot=i.operands[1].imm+n.operands[1].mem.disp
            if slot in slots:
                assert pi[k+3].mnemonic=='br' and pi[k+3].op_str=='x17'
                plt[i.address]={'name':slots[slot],'GOT_slot':hex(slot)}
    assert len(plt)==len(slots)
    fdes=[]
    for record in e.get_dwarf_info().EH_CFI_entries():
        if isinstance(record,FDE):fdes.append({'start':hex(record['initial_location']),
            'end_exclusive':hex(record['initial_location']+record['address_range']),'bytes':record['address_range']})
    text=e.get_section_by_name('.text');assert text['sh_size']%4==0
    ins=[];unknown_words=[];td=text.data()
    for off in range(0,len(td),4):
        decoded=list(c.disasm(td[off:off+4],text['sh_addr']+off,count=1))
        if decoded:ins.append(decoded[0])
        else:unknown_words.append(hex(text['sh_addr']+off))
    known={};strings=[];calls=[];lines=[]
    for i in ins:
        old=known.copy();ops=i.operands;new={};note=''
        if i.mnemonic in ('adrp','adr'):
            new[canonical(i,ops[0].reg)]=ops[1].imm
        elif i.mnemonic in ('add','sub') and len(ops)==3 and ops[1].type==ARM64_OP_REG and ops[2].type==ARM64_OP_IMM and canonical(i,ops[1].reg) in old:
            value=old[canonical(i,ops[1].reg)]+(1 if i.mnemonic=='add' else -1)*(ops[2].imm<<ops[2].shift.value)
            new[canonical(i,ops[0].reg)]=value
            s=str_at(value)
            if s:
                note=' ; source string candidate '+repr(s)
                strings.append({'site':hex(i.address),'address':hex(value),'value':s,'locator_only':True})
        for r in i.regs_access()[1]:known.pop(canonical(i,r),None)
        known.update(new)
        if i.mnemonic in ('bl','b') and ops and ops[0].type==ARM64_OP_IMM:
            target=ops[0].imm;call={'site':hex(i.address),'kind':i.mnemonic,'target':hex(target)}
            if target in plt:call['import']=plt[target]['name'];note+=' ; import '+plt[target]['name']
            calls.append(call)
        lines.append(f'{i.address:#x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}{note}')
        if i.mnemonic=='bl':
            for k in range(19):known.pop('x'+str(k),None)
        elif i.mnemonic in ('b','br','ret'):known.clear()
    with (H/(label+'-text.txt')).open('x') as f:
        f.write('# Original ELF VA, every4B alignment includes possible data; locators only, not measured camera PC.\n'+'\n'.join(lines)+'\n')
    results.append({'label':label,'path':str(path),'sha256':expected,'entry':hex(e['e_entry']),
        'text':{'VA':hex(text['sh_addr']),'file_offset':hex(text['sh_offset']),'bytes':text['sh_size']},
        'PLT':{hex(a):v for a,v in plt.items()},'unwind_function_ranges':fdes,'calls':calls,'string_candidates':strings,
        'undecoded_words':unknown_words,'text_scan_scope':'all4B alignments may include data; selected function code must be separately checked'})
put('helper-disassembly.json',{'helpers':results,'scope':'ELF mapping and candidate string references; FDE ranges do not establish entry reachability','original_or_guest_execution':False,'root_or_device_operations':0})
print(json.dumps({'helpers':[{'label':x['label'],'text_bytes':x['text']['bytes'],'unwind_ranges':len(x['unwind_function_ranges']),
    'imports':len(x['PLT'])} for x in results],'original_or_guest_execution':False}))
