"""Verify pinned source lines and original instruction words, without execution."""
from pathlib import Path
from hashlib import sha256,sha1
from io import BytesIO
import ast,json,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
H=Path(__file__).resolve().parent;B=H.parent
sources=[]
for name in ['source-capture.json','source-retry-capture.json','source-followup-capture.json']:
 for row in json.loads((H/name).read_text())['files']:
  if 'sha256' not in row:continue
  p=H/row['output'];raw=p.read_bytes();assert len(raw)==row['bytes'] and sha256(raw).hexdigest()==row['sha256']
  assert sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()==row['git_blob_sha1'];sources.append(row)
assert len(sources)==24
by={(x['repo'],x['path']):x for x in sources};lines=[]
def line(repo,path,fragment):
 row=by[(repo,path)];text=(H/row['output']).read_text().splitlines();found=[(n+1,s) for n,s in enumerate(text) if fragment in s];assert len(found)==1,(path,fragment,found)
 n,s=found[0];r=dict(repo=repo,commit=row['commit'],path=row['output'],source_sha256=row['sha256'],line=n,text=s,url=f'https://github.com/{repo}/blob/{row["commit"]}/{path}#L{n}');lines.append(r);return r
D='dino2048/zv-e10-toolkit';C='cokeenet/zve10-qemu'
line(D,'linux/helpers/bootrom-reader/read_page.S','.arch armv7-a')
line(D,'linux/helpers/bootrom-reader/read_page.S','page_base: .word 0xffff0')
line(D,'linux/helpers/bootrom-reader/read_page.S','cmp r1, #0x35')
line(D,'linux/docs/bootrom-dump.md','30110_05.2025031501')
line(D,'linux/docs/root-terminal.md','setTerminalEnable(True)')
line(D,'linux/host/zve10_bootrom_dump.py','camera.setTerminalEnable(True)')
line(D,'linux/host/zve10_bootrom_dump.py','check_mounts(camera.dev)')
line(D,'bootrom/docs/hardware.md','needs dedicated wiring')
line(D,'bootrom/docs/recovery.md','boot0/boot1, partition tables or physical hardware faults')
line(D,'bootrom/host/restore_rescue.py','back = with_device(30, lambda d: fetch(d, name, rows[name]')
line(D,'bootrom/host/restore_rescue.py','ok = back == slices[name]')
line(C,'docs/incidents/INCIDENT_20261028_LDSO_PRELOAD.md','直接原因不是 preload')
line(C,'docs/incidents/INCIDENT_20261028_LDSO_PRELOAD.md','第 1 步之后相机没好转')
line(C,'docs/incidents/SD_UPDATE_RECOVERY.md','整个流程能否在')
line(C,'fastboot/host/flash_partition.py','part_start_lba + byte_off // 512')
line(C,'fastboot/host/flash_partition.py','part_start_lba = a.part_start // 512')
line(C,'fastboot/host/flash_partition.py','part_start_lba = 0')
line(C,'fastboot/host/flash_partition.py','target[i * bgran:(i + 1) * bgran] != ref')
line(C,'fastboot/host/flash_partition.py','if a.plan_only:')
line(C,'fastboot/host/verify_partition.py','n = len(img) // CH')
line(C,'fastboot/host/verify_partition.py','for i in range(n):')
line(C,'fastboot/host/verify_partition.py','RESULT: 0 mismatching blocks')
line(C,'README.md','显示链路未完成')
# AST only: importing the tools would also load transport modules. Do not import.
for row in sources:
 if row['path'].endswith('.py'):ast.parse((H/row['output']).read_text(),filename=row['output'])
raw=(H/'originals/app/bin/bootin.elf').read_bytes();assert sha256(raw).hexdigest()=='dab3ce4b6c28a6c9ffd9f0b893dce1d08f3ee7302a09df87e518409e728be2f2'
e=ELFFile(BytesIO(raw));assert e.elfclass==64 and e.header['e_machine']=='EM_AARCH64'
def original(va,n):
 s=next(x for x in e.iter_segments() if x['p_type']=='PT_LOAD' and x['p_vaddr']<=va and va+n<=x['p_vaddr']+x['p_filesz']);at=s['p_offset']+va-s['p_vaddr'];return raw[at:at+n],at
assert original(0x403bec,20)[0]==b'/setting/mode/dmode\0';assert original(0x403a28,2)[0]==b'3\0'
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM);md.skipdata=True
text=e.get_section_by_name('.text');ins=list(md.disasm(text.data(),text['sh_addr']));gaps=[i.address for i in ins if i.mnemonic.startswith('.')]
assert sum(i.size for i in ins)==text['sh_size']==7952 and gaps==[0x401928,0x401930,0x401938]
# Check real relocation-to-PLT identity, then decode original branches directly.
st=e.get_section_by_name('.dynsym');plt=e.get_section_by_name('.plt');rel=e.get_section_by_name('.rela.plt')
pt={plt['sh_addr']+32+i*16:st.get_symbol(x['r_info_sym']).name for i,x in enumerate(rel.iter_relocations())}
assert pt[0x4014f0]=='open' and pt[0x401590]=='read' and pt[0x4016e0]=='close'
checks=[]
def word(va):return struct.unpack('<I',original(va,4)[0])[0]
def check(va,mask,expected,note):
 w=word(va);assert w&mask==expected,(hex(va),hex(w),note);checks.append(dict(VA=hex(va),word=hex(w),mask=hex(mask),expected=hex(expected),meaning=note))
def branch(va,target,kind):
 w=word(va)
 if kind=='b':assert w&0x7c000000==0x14000000;bits=w&0x3ffffff;width=26
 else:assert w&0xff000010==0x54000000;bits=(w>>5)&0x7ffff;width=19
 delta=(bits-(1<<width) if bits>>(width-1) else bits)<<2
 assert va+delta==target;checks.append(dict(VA=hex(va),word=hex(w),branch_target=hex(target),meaning=kind))
branch(0x402394,0x4014f0,'b');branch(0x4023ac,0x401590,'b');branch(0x402408,0x4016e0,'b')
# read requests at most30 bytes; loop consumes the returned count and preserves
# selected mode for ignored bytes. No full-loader/boot execution is claimed.
check(0x4023a4,0xffffffff,0xd28003c2,'mov x2,30: requested read length')
check(0x4023e8,0xffffffff,0x6b07001f,'cmp w0,w7: returned length vs position')
branch(0x4023ec,0x4024e8,'cond');assert word(0x4023ec)&15==12
check(0x4024e8,0xffffffff,0x38676aa4,'ldrb w4,[x21,x7]')
check(0x402504,0xffffffff,0x7100cc9f,'cmp w4,0x33')
branch(0x402508,0x402518,'cond');assert word(0x402508)&15==1
check(0x40250c,0xffffffff,0x52800026,'mov w6,1: mode was selected')
check(0x402510,0xffffffff,0xaa0b03e5,'mov x5,x11: address of literal3')
branch(0x402514,0x402530,'b')
check(0x402530,0xffffffff,0x910004e7,'increment byte position')
branch(0x402534,0x4023e8,'b');branch(0x40257c,0x402530,'cond');assert word(0x40257c)&15==1
check(0x4023f8,0xffffffff,0xf9000805,'store selected mode pointer on loop completion')
cuts=[]
for name,a,z in [('mode-read-and-commit',0x402334,0x40240c),('mode-parse',0x4024e8,0x4025ac),('mode-string',0x403a28,0x403a2a),('mode-path',0x403bec,0x403c00)]:
 b,at=original(a,z-a);dest=H/'raw'/name;dest.parent.mkdir(exist_ok=True);dest.open('xb').write(b)
 cuts.append(dict(name=name,source='originals/app/bin/bootin.elf',source_sha256=sha256(raw).hexdigest(),start=hex(a),end_exclusive=hex(z),file_offset=at,bytes=len(b),sha256=sha256(b).hexdigest(),output=str(dest.relative_to(H))))
# Primary scripts are preserved as data. Never source them on the host.
script=H/'originals/app/bin/change_mode.sh';assert sha256(script.read_bytes()).hexdigest()=='0c277c24e503f214ebdb651ea1bec569ebd31d6c19c27156f3df29394621fc75'
assert script.read_text().splitlines()[74].strip()=='echo 3 > $MODE_FILE'
proof=dict(schema='fx3-stage216-source-portability-proof-v1',source_files_git_blob_and_sha_verified=24,source_lines=lines,
 original_bootin_sha256=sha256(raw).hexdigest(),original_bootin_machine='EM_AARCH64',original_ranges=cuts,raw_instruction_checks=checks,
 original_text_coverage=dict(bytes=7952,instruction_bytes=7940,skipped_data_bytes=12,skipped_addresses=[hex(x) for x in gaps],selected_ranges_have_no_skipped_words=True),
 selected_mode_parser=dict(path_VA='0x403bec',read_limit=30,mode3_literal_VA='0x403a28',
  observation='Byte0x33 selects literal3; loop uses read return count. LF takes ignored-byte path. Selected parse accepts a single ASCII3 byte without requiringLF; not proof of full boot health.',
  preserve_healthy_same_body_bytes=True,community_newline_rule_not_ported=True,original_software_or_guest_execution=False),
 address_semantics=dict(upstream_write='partition-relative bytes in sparse run',upstream_verify='absolute LBA=part_start_bytes/512+relative_bytes/512',
  implicit_zero_start_present_without_reference=True,implicit_zero_start_not_accepted_for_FX3=True,same_target_reference_produces_empty_diff_without_full=True,
  sampled_verify_not_full_coverage=True,whole_verifier_floor64KiB_does_not_cover_arbitrary_tail=True,
  illustrative_tail=dict(input_bytes=65537,loop_chunks=1,covered_bytes=65536,uncovered_bytes=1,source_derived_arithmetic_only=True)),
 no_device_backend_imported=True,upstream_code_executed=False,Sony_code_or_guest_executed=False,root_or_device_operations=0)
(H/'portability-proof.json').open('x').write(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(source_files=24,source_lines=len(lines),original_ranges=len(cuts),raw_instruction_checks=len(checks),Sony_or_upstream_execution=False)))
