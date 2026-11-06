"""Bind C-runtime zeroing and public Backup rate evidence; no firmware execution."""
from pathlib import Path
from hashlib import sha256
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
import json,struct,re,tarfile
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
NP=B/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin';N=NP.read_bytes();NB=0xfe049000;assert sha256(N).hexdigest()=='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
AP=B/'stage204-public-AP-boot-reference/reference/emmc_boot/esram_0xfe040000.bin';A=AP.read_bytes();AB=0xfe040000;assert sha256(A).hexdigest()=='2e37d90bc8f489db13a0319a3e7f8f1e746921c380484147b922957af3e95d74'
def word(d,b,a):return int.from_bytes(d[a-b:a-b+4],'little')
def bl(d,b,a):
 w=word(d,b,a);assert w&0xfc000000==0x94000000;n=w&0x3ffffff;return a+4*(n-(1<<26) if n&(1<<25) else n)
w=lambda a:word(N,NB,a)
def ldr64(d,b,a):
 w=word(d,b,a);assert w&0xff000000==0x58000000;n=(w>>5)&0x7ffff;n=n-(1<<19) if n&(1<<18) else n;target=a+n*4;return target,struct.unpack_from('<Q',d,target-b)[0]
# Region table is bounded entirely in the current file. Handler bit0 is clear.
assert ldr64(N,NB,0xfe04c6f0)==(0xfe04c740,0xfe061450)
assert ldr64(N,NB,0xfe04c6fc)==(0xfe04c748,0xfe061470)
assert w(0xfe04c72c)==0x91008273 and w(0xfe04c730)==0xd63f0060
src,dst,size,handler=struct.unpack_from('<4Q',N,0xfe061450-NB);assert (src,dst,size,handler)==(0xfe061e00,0xfe061e00,7480,0xfe04c750)
for a,v in [(0xfe04c750,0x52800000),(0xfe04c754,0x14000003),(0xfe04c758,0xb8004420),(0xfe04c75c,0xd1001042),(0xfe04c760,0xf100005f),(0xfe04c764,0x54ffffa1),(0xfe04c768,0xd65f03c0)]:assert w(a)==v
assert size%4==0 and dst<=0xfe0625cc<0xfe0625dc<=dst+size
assert bl(N,NB,0xfe04c708)==0xfe04a134 and bl(N,NB,0xfe04a144)==0xfe059f34
# First zero writer is conditional on executing this C-init path; not a final
# SIO configuration. The later assignment is still unresolved in current NOR.
assert w(0xfe0523b4)==0x90000095 and w(0xfe0523e8)==0xb945cea8
# Reference initializer reads property0x51002C into its actual rate global.
aw=lambda a:word(A,AB,a)
assert aw(0xfe0535c4)==0xf00000a1 and aw(0xfe0535c8)==0x52800580 and aw(0xfe0535cc)==0x9124d021 and aw(0xfe0535d0)==0x72a00a20
assert bl(A,AB,0xfe0535d4)==0xfe05b2b8
assert aw(0xfe04ddd8)==0xb94936a8
assert aw(0xfe0537dc)==0x321f03f3 and aw(0xfe0537e0)==0x14000019 and aw(0xfe053844)==0x2a1303e0
# Reference reader's BKSB mode scans12-byte records and copies declared bytes.
assert aw(0xfe05b2dc)==0x7100111f and bl(A,AB,0xfe05b2e4)==0xfe05aeac
assert aw(0xfe05b30c)==0x91003108 and bl(A,AB,0xfe05b374)==0xfe04b444
assert aw(0xfe05aeac)==0x52802208 and aw(0xfe05aeb0)==0x72bfc088 and aw(0xfe05aeb4)==0xb9400100
assert struct.unpack_from('<I',A,0x110)[0]==0xfe048800
bk=json.loads((H/'boot-backup-reference-and-list.json').read_text());assert bk['properties']==66 and bk['all_property_bounds_checked'] and bk['rate_ID_in_current_list']
rate=next(x for x in bk['selected'] if x['ID']=='0x51002c');assert rate['value_u32']==3 and rate['value_address']=='0xfe048b48'
# All11 classic templates, both records: selected rate is3. Primary AP GPIO/
# SIO values and alternate-bank sentinels are kept as public default bytes.
values=json.loads((H/'SIO-Backup-property-results.json').read_text());assert len(values['templates'])==11
for t in values['templates']:
 raw=(R/t['source_path']).read_bytes();assert sha256(raw).hexdigest()==t['source_sha256']
 assert len(t['records'])==2
 for i,rec in enumerate(t['records']):
  fields={int(r['id'],16):r for r in rec['selected_properties']};assert fields[0x51002c]['value_u32']==3 and all(r['present'] and r['bytes']==4 for r in fields.values())
  assert [fields[x]['value_u32'] for x in [0xf900d4,0xf900b1,0xf9006d]]==([0,4,2] if i==0 else [5,4,30])
  for ident in [0xf90148,0xf9013c,0xf9010d]:assert fields[ident]['value_u32']==0xffffffff
cross=json.loads((H/'PMCA-rate-crosscheck.json').read_text());assert cross['records']==22 and cross['cases']==154 and all(x['match'] for x in cross['checks'])
listpath=R/bk['current_list'];assert sha256(listpath.read_bytes()).hexdigest()==bk['current_list_sha256'];ids=[int(x,16) for x in re.findall(r'0x[0-9A-Fa-f]+',listpath.read_text())];assert len(ids)==65 and 0x51002c in ids
# Compare package catalog scope only; this is not a same-body backup search.
audit=B/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/current-updater-asset-audit.json';inventory=json.loads(audit.read_text());listmembers=[r for r in inventory['nor_loader_members'] if r['name']=='LdrBkupList.txt'];assert len(listmembers)==1 and listmembers[0]['sha256']==bk['current_list_sha256']
outer=next(r for r in inventory['tar']['members'] if r['name']=='0750_nor_loader/loader_nor.tar');outerpath=Path(outer['output']);assert sha256(outerpath.read_bytes()).hexdigest()==outer['sha256']=='913d1a3271f855b90192d84fbbdb224533c8d8493833d0c194b3d14fdad4dd3f'
with tarfile.open(outerpath,'r:') as tf:
 assert tf.extractfile('LdrBkupList.txt').read()==listpath.read_bytes()
 inner_names=[m.name for m in tf.getmembers() if m.isfile()]
 assert set(inner_names)=={r['name'] for r in inventory['nor_loader_members']}
BKSBmembers=[r['name'] for r in inventory['tar']['members'] if r['name'].lower().endswith('/ldrbkup.bin')]+[n for n in inner_names if n.lower()=='ldrbkup.bin']
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);pins=[];pd=H/'pins';pd.mkdir()
def pin(p,raw,base,a,z,label,kind='code'):
 part=raw[a-base:z-base];assert len(part)==z-a;o=pd/(label+'.txt')
 lines=[part.hex()] if kind=='data' else [f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}' for i in md.disasm(part,a)]
 o.open('x').write('\n'.join(lines)+'\n');pins.append(dict(source=str(p.relative_to(R)),source_sha256=sha256(raw).hexdigest(),base=hex(base),start=hex(a),end_exclusive=hex(z),bytes=z-a,sha256=sha256(part).hexdigest(),kind=kind,output=str(o.relative_to(R))))
for a,z,label,kind in [(0xfe04c6f0,0xfe04c738,'FX3-region-initializer','code'),(0xfe04c740,0xfe04c750,'FX3-region-table-literals','data'),(0xfe061450,0xfe061470,'FX3-region-record','data'),(0xfe04c750,0xfe04c76c,'FX3-bounded-zero-loop','code'),(0xfe04a134,0xfe04a150,'FX3-runtime-to-main-prefix','code'),(0xfe0523b0,0xfe05241c,'FX3-rate-consumer','code')]:pin(NP,N,NB,a,z,label,kind)
for a,z,label,kind in [(0xfe0535c4,0xfe0535e0,'A7IV-rate-property-input','code'),(0xfe0537dc,0xfe0537e4,'A7IV-rate-read-failure','code'),(0xfe053844,0xfe05385c,'A7IV-init-return','code'),(0xfe04ddd0,0xfe04de0c,'A7IV-rate-field-consumer','code'),(0xfe05b2b8,0xfe05b3c8,'A7IV-BKSB-property-reader','code'),(0xfe05aeac,0xfe05aebc,'A7IV-BKSB-pointer-getter','code'),(0xfe040110,0xfe040114,'A7IV-BKSB-pointer-cell','data'),(0xfe048800,0xfe048b20,'A7IV-BKSB-header-and-table','data'),(0xfe048b48,0xfe048b4c,'A7IV-BKSB-rate-word','data')]:pin(AP,A,AB,a,z,label,kind)
proof=dict(status='FIRST_ZERO_WRITER_AND_OFFICIAL_DEFAULT_RATE3_REFERENCE_CONSUMER_BOUND',
 C_initialization=dict(table_start='0xfe061450',table_end='0xfe061470',record_count=1,source_argument=hex(src),destination=hex(dst),bytes=size,handler=hex(handler),write_unit_bytes=4,
    clear_end_exclusive=hex(dst+size),clears_current_SIO_rate_and_channel_CS_fields=True,only_conditional_source_path_not_device_execution=True,later_rate_initialization_proven=False),
 rate_default=dict(Backup_ID='0x51002c',classic_templates=11,records=22,all_values=3,reference_init_call='0xfe0535d4',reference_rate_field='0xfe06a934',reference_BKSB_rate_value=3,
    reference_read_failure_returns=2,reference_has_fallback_rate3=False,current_list_contains_ID=True,current_FX3_NOR_consumer_of_this_ID_proven=False,current_body_value_read=False),
 current_package_catalog=dict(source=str(audit.relative_to(R)),source_sha256=sha256(audit.read_bytes()).hexdigest(),list_member=listmembers[0],NOR_inner_archive=outer,LdrBkup_bin_members=BKSBmembers,scope='outer saved package inventory and four-member NOR archive only; no device file/interface query'),
 independent_PMCA_property_cases=154,selected_original_ranges=pins,
 limits=['Public default3 and peer consumer justify an offline candidate, not current-body configuration or SIO Hz','Zeroing path is an initial source producer; it does not establish the later intended rate','Current NOR path loading the final rate and startup Backup state remain unresolved','Public reference BKSB is not current FX3 same-body Backup','No source/candidate code was run on the camera; no independent recovery or flash acceptance'],Sony_code_or_guest_execution=False,third_party_host_parser_execution_on_readonly_buffers=True,root_or_device_operations=0)
(H/'runtime-and-default-rate-proof.json').open('x').write(json.dumps(proof,indent=2)+'\n')
profile=dict(schema='fx3-early-link-profile-offline-v1',model='classic ILME-FX3',package_version='7.02',source_scope='11 public AP default templates; static reference consumer',
 SIO_channel=0,SIO_rate_word=3,SIO_rate_Backup_ID='0x51002c',GPIO_portid=4,GPIO_bitnum=2,GPIO_open_mode=2,
 distinct_Linux_firmware_writer_request_word=19,proof='runtime-and-default-rate-proof.json',current_NOR_final_rate_load_proven=False,actual_clock_Hz_or_transport_proven=False,
 executable_payload=False,device_operation_authorized=False,persistent_write_release=False,current_body_backup_or_independent_restore_proven=False)
(H/'FX3-early-link-profile-candidate.json').open('x').write(json.dumps(profile,indent=2)+'\n')
print(json.dumps(dict(original_ranges=len(pins),classic_rate_values=22,all_default_rate3=True,PMCA_cases=154,conditional_initial_zero_bytes=size,current_final_rate_load_proven=False,nonexecutable_profile=[3,0,4,2],actual_device_operations=0)))
