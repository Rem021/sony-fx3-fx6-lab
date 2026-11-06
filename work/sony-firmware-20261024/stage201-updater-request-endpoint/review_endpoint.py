"""Independent raw-word checks of the branch cases; no guest instruction execution."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json, struct
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
H=Path(__file__).resolve().parent
def put(n,v):
    with (H/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def mapped(raw,a,n):
    e=ELFFile(BytesIO(raw))
    seg=[s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz']];assert len(seg)==1
    s=seg[0];off=s['p_offset']+a-s['p_vaddr'];return raw[off:off+n]
proof=json.loads((H/'queue-endpoint-proof.json').read_text())
# Tighten two unsealed ranges: include dispatch argument loads, exclude helper literal/startup tail.
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
for label,a,z in [('current-user-dispatch',0x32cc,0x3340),('current-helper-reply',0x400a38,0x400adc)]:
    row=next(x for x in proof['selected_original_ranges'] if x['disassembly']==label+'.txt');raw=(H/'originals/7.02-main'/row['source'].lstrip('/')).read_bytes();part=mapped(raw,a,z-a)
    e=ELFFile(BytesIO(raw));rs=e.get_section_by_name('.rela.plt');st=e.get_section(rs['sh_link']);plt=e.get_section_by_name('.plt');names={plt['sh_addr']+32+16*n:st.get_symbol(r['r_info_sym']).name for n,r in enumerate(rs.iter_relocations())}
    lines=[]
    for i in md.disasm(part,a):
        target=int(i.op_str[1:],16) if i.mnemonic in ['bl','b'] and i.op_str.startswith('#') else -1
        lines.append(f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}'+(' ; '+names[target] if target in names else ''))
    assert len(lines)*4==len(part)
    (H/(label+'.txt')).write_text('\n'.join(lines)+'\n');row.update(start=hex(a),end_exclusive=hex(z),bytes=len(part),sha256=sha256(part).hexdigest())
(H/'queue-endpoint-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
raw=(H/'originals/7.02-main/lib/libObj.so').read_bytes()
word=lambda a:struct.unpack('<I',mapped(raw,a,4))[0]
def sx(n,b):return n-(1<<b) if n&(1<<(b-1)) else n
def cond(a,target,condition):
    w=word(a);assert w&0xff000010==0x54000000 and w&15==condition
    assert a+sx((w>>5)&0x7ffff,19)*4==target
def cbz(a,target,reg):
    w=word(a);assert w&0xff000000==0x34000000 and w&31==reg
    assert a+sx((w>>5)&0x7ffff,19)*4==target
def cmp19(a,value):
    w=word(a);assert w&0xffc003ff==0x7100027f and (w>>10)&0xfff==value
def branch(a,target,link=False):
    w=word(a);assert w&0xfc000000==(0x94000000 if link else 0x14000000)
    assert a+sx(w&0x3ffffff,26)*4==target
checks=[]
cbz(0xed9ec,0xeda9c,19);checks.append('command0 takes reply path after remove wrapper success')
for a,value,target in [(0xeda08,2,0xeda9c),(0xeda10,4,0xeda5c),(0xeda18,6,0xeda68)]:
    cmp19(a,value);cond(a+4,target,0);checks.append(f'command{value} compare and EQ branch')
cmp19(0xeda20,3);cond(0xeda24,0xeda50,1);checks.append('other commands including5/7 reach command-error path')
branch(0xeda64,0xeda30);branch(0xeda70,0xeda30);checks.append('4/6 share create-specific-flag path')
branch(0xed9c8,0xed8cc,True);branch(0xeda34,0xed940,True);checks.append('remove wrapper precedes command switch; flag creation calls open wrapper')
branch(0xee188,0x57c50,True);checks.append('registration BL points to ELF relocation-named osal_reg_msg_queue_cb PLT')
branch(0xeda94,0x57bc0,True);branch(0xeda58,0xed9d8);checks.append('unsupported command logs and frees; no reply allocation on that local path')
calls=[]
for a in range(0xed990,0xedae0,4):
    w=word(a)
    if w&0xfc000000==0x94000000:calls.append(dict(at=hex(a),target=hex(a+sx(w&0x3ffffff,26)*4)))
    assert w&0xfffffc1f!=0xd63f0000,'unexpected indirect call in selected complete callback'
checks.append('complete selected callback has listed direct BL sites and no BLR')
references=json.loads((H/'reference-providers.json').read_text());pairs=[]
for name in sorted({r['path_in_fs'] for r in references['captures']}):
    a,b=[next(r for r in references['captures'] if r['path_in_fs']==name and r['version']==v) for v in ['2.04','2.05']]
    x,y=[Path(r['output']).read_bytes() for r in [a,b]];nx,ny=bytearray(x),bytearray(y)
    for v,data in [(nx,x),(ny,y)]:
        e=ELFFile(BytesIO(data));s=e.get_section_by_name('.note.gnu.build-id')
        if s:v[s['sh_offset']:s['sh_offset']+s['sh_size']]=bytes(s['sh_size'])
    pairs.append(dict(path=name,identical=x==y,identical_after_build_id_note_zeroed=nx==ny,current_body_attestation=False))
put('endpoint-raw-audit.json',dict(checks=checks,check_count=len(checks),selected_callback_direct_calls=calls,
    decoder='independent fixed AArch64 word masks/sign-extension; no instruction interpreter or emulated callee',
    branch_conditions='static ordinary return paths only; successful helper/flag operations are conditions, not observed results',
    historical_reference_identity=pairs,original_or_guest_execution=False,root_or_device_operations=0))
put('analysis-corrections.json',dict(corrections=[
    'Initial Ext2 row filter used SquashFS string type; assertion failed before captures. Corrected to Ext2 integer regular-file type32768.',
    'Expanded user callback slice to include argument loads; stopped helper reply slice before literal/startup tail. Unsealed selected hashes regenerated.',
    'Stage183 high-id-audit had already located libObj sites; earlier unresolved-consumer synthesis did not follow their actual PLT relocation. This stage binds register and callback from the same7.02 ELF.',
    'Historical p1 has different message providers; current-main helper is independently captured and has a different SHA from historical helpers. Reference binaries were never substituted for current runtime.'
],device_or_original_execution=0))
print(json.dumps(dict(independent_raw_checks=len(checks),callback_calls=calls,historical_pairs=pairs)))
