#!/usr/bin/env python3
"""Original class5 escape-loader projection and complete CPIR record bounds."""
import hashlib,importlib.util,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from capstone import Cs,CS_ARCH_ARM64,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_LITTLE_ENDIAN
from unicorn import Uc,UcError,UC_ARCH_ARM64,UC_MODE_ARM,UC_PROT_READ,UC_PROT_EXEC,UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_INVALID,UC_HOOK_MEM_WRITE
from unicorn import arm64_const as R
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PROJECT=HERE.parents[2]
FW=PROJECT/'work/sony-firmware-20261024';AP_BASE=0xfe040000;ROW=0x100000000;CTX=0x100100000;STACK=0x100200000
def sha(b):return hashlib.sha256(b).hexdigest()


class Fragment:
    def __init__(self,ap,row,cp_base,staging):
        self.u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);self.ap=ap;self.row=row;self.trace=[];self.boundary=None
        self.u.mem_map(AP_BASE,(len(ap)+4095)&~4095,UC_PROT_READ|UC_PROT_EXEC);self.u.mem_write(AP_BASE,ap)
        for base in [ROW,CTX,STACK]:self.u.mem_map(base,4096,UC_PROT_READ)
        self.u.mem_write(ROW,row);self.u.mem_write(CTX+0x218,struct.pack('<Q',cp_base));self.u.mem_write(STACK+0x18,struct.pack('<Q',staging))
        for reg,value in [(R.UC_ARM64_REG_X28,ROW+0x18),(R.UC_ARM64_REG_X19,CTX),(R.UC_ARM64_REG_SP,STACK),(R.UC_ARM64_REG_W21,struct.unpack_from('<I',row,0x10)[0])]:self.u.reg_write(reg,value)
        self.u.hook_add(UC_HOOK_CODE,self.code);self.u.hook_add(UC_HOOK_MEM_READ,self.read);self.u.hook_add(UC_HOOK_MEM_INVALID,self.invalid);self.u.hook_add(UC_HOOK_MEM_WRITE,self.write)
    def stop(self,reason,**extra):
        self.boundary=dict(reason=reason,PC=hex(self.u.reg_read(R.UC_ARM64_REG_PC)),**extra);self.u.emu_stop()
    def code(self,u,pc,size,user):
        if pc==0xfe059e20:self.stop('before_original_file_load');return
        if pc==0xfe052268:self.stop('before_original_class7_skip_diagnostic');return
        if pc==0xfe0522b8:self.stop('before_original_row_advance');return
        if not 0xfe052220<=pc<=0xfe052298:self.stop('before_outside_selected_fragment');return
        self.trace.append(hex(pc))
    def read(self,u,access,at,size,value,user):
        if AP_BASE<=at and at+size<=AP_BASE+len(self.ap):return
        if ROW<=at and at+size<=ROW+len(self.row):return
        if CTX+0x218<=at and at+size<=CTX+0x220:return
        if STACK+0x18<=at and at+size<=STACK+0x20:return
        self.stop('before_unknown_read',address=hex(at),bytes=size)
    def invalid(self,u,access,at,size,value,user):self.stop('before_unmapped_state',address=hex(at),bytes=size);return False
    def write(self,u,access,at,size,value,user):self.stop('unexpected_write',address=hex(at),bytes=size)
    def run(self):
        try:self.u.emu_start(0xfe052220,0xfe0522bc,timeout=1000000,count=1000)
        except UcError:
            if self.boundary is None:raise
        assert self.boundary is not None
        return dict(boundary=self.boundary,original_instruction_entries=len(self.trace),trace=self.trace,
            X0=hex(self.u.reg_read(R.UC_ARM64_REG_X0)),X1=hex(self.u.reg_read(R.UC_ARM64_REG_X1)),
            X29=hex(self.u.reg_read(R.UC_ARM64_REG_X29)),file_read_or_transfer_executed=False,
            unknown_state_or_success_reply_supplied=False,memory_writes=0)


def main():
    out=HERE/'escape-source-proof.json';assert not out.exists()
    ref=FW/'stage204-public-AP-boot-reference/reference/emmc_boot/esram_0xfe040000.bin';ap=ref.read_bytes();assert sha(ap)=='2e37d90bc8f489db13a0319a3e7f8f1e746921c380484147b922957af3e95d74'
    bk=TASK/'dmm-backup-20261029';manifest=json.loads((bk/'final-receipt.json').read_text())
    hp=bk/'extract_backup_parameters.py';hp_pin=next(x for x in manifest['files'] if x['path']==hp.name);assert sha(hp.read_bytes())==hp_pin['sha256']
    spec=importlib.util.spec_from_file_location('owned_BK4_reader',hp);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    records=[];params=[]
    for bank in [0,1]:
        path=bk/f'original-records/canonical-bank{bank}.bin';b=path.read_bytes();pin=next(x for x in manifest['files'] if x['path']==str(path.relative_to(bk)));assert sha(b)==pin['sha256']
        assert (sum(b[:32])+sum(b[36:]))&0xffffffff==struct.unpack_from('<I',b,32)[0]
        records.append(b);params.append(dict(bank=bank,path=str(path),sha256=sha(b),values=[h.property_at(b,key) for key in [0xfa019a,0xfa019b,0xfa01d0,0xfa01d3,0xfa0077,0xfa01af]]))
    value=lambda bank,key:int.from_bytes(bytes.fromhex(h.property_at(records[bank],key)['value_hex']),'little')
    staging,cap=value(0,0xfa019a),value(0,0xfa019b);cp_base,cp_end=value(1,0xfa01d0),value(1,0xfa01d3)
    assert (staging,cap,cp_base,cp_end)==(0x412000000,0x2a00000,0x808730000,0x809a21e00)
    source=json.loads((TASK/'config-producer-20261029/load-descriptor-sources.json').read_text());bank=next(x for x in source['templates'] if x['member']==source['canonical_template'])['banks'][1]
    table_path=TASK/'config-producer-20261029'/bank['saved_payload'];table=table_path.read_bytes();assert sha(table)==bank['payload_sha256']
    cases=[]
    for name in ['DmmCfg.bin','cpImg.dat','tomco.txt']:
        row=next(x for x in bank['entries'] if x['path'].lstrip('\\')==name);at=int(row['record_offset'],16);raw=table[at:at+0x90];assert sha(raw)==row['original_record_sha256']
        result=Fragment(ap,raw,cp_base,staging).run()
        if name=='tomco.txt':assert result['boundary']['reason']=='before_original_class7_skip_diagnostic'
        else:assert result['boundary']['reason']=='before_original_file_load' and int(result['X1'],16)==staging+int(row['start'],16)-cp_base
        cases.append(dict(original_row=row,original_row_sha256=sha(raw),explicit_reference_fragment=result))
    ordinary=[r for r in bank['entries'] if int(r['mode'],16)==0x05000000]
    assert len(ordinary)==9 and min(int(r['start'],16) for r in ordinary)==cp_base and max(int(r['end'],16)+1 for r in ordinary)==cp_end
    fsroot=FW/'stage2/extraction';reader=fsroot/'read_filesystems.py';assert sha(reader.read_bytes())=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    sys.path.insert(0,str(fsroot));from read_filesystems import FAT16
    image=fsroot/'nflasha8.img';assert sha(image.read_bytes())=='3c751e784fe6790a4b455990d7c6e144c33cf51c643cf3bf9523f8a3bd5a6a2b'
    fs=FAT16(image);entries=list(fs.walk());available={x['path'].lstrip('/'):x for x in entries}
    for r in ordinary:r['present_in_original_update_p8_FAT']=r['path'].lstrip('\\').replace('\\','/') in available
    e=available['cpImg.dat'];cpir=fs.data(e['cluster'],e['size']);assert sha(cpir)=='76af47a5f97470c396c9d0edc576e2bd31b808e8242d742f7722c6f9e90d91c9'
    magic,version,total,offset,stride,count,extra=struct.unpack_from('<7I',cpir);assert (magic,version,total,offset,stride,count,extra)==(0x52495043,1,len(cpir),28,20,500,20)
    cursor=offset+stride*count+extra;items=[]
    for i in range(count):
        n,a,b,f0,f1,f2=struct.unpack_from('<IHHIII',cpir,offset+i*stride);assert cursor+n<=len(cpir)
        items.append(dict(index=i,descriptor_offset=hex(offset+i*stride),payload_offset=hex(cursor),payload_bytes=n,
            u16_4=a,u16_6=b,u32_8=f0,u32_c=f1,u32_10=f2,payload_sha256=sha(cpir[cursor:cursor+n]),
            fits_align16_two_byte_plane=(n==((a*2+15)&~15)*b)));cursor+=n
    assert cursor==len(cpir) and sum(x['fits_align16_two_byte_plane'] for x in items)==474
    dmm_path=TASK/'dmm-config-20261029/original-files/DmmCfg.bin';dmm=dmm_path.read_bytes();assert sha(dmm)=='820dc02b6a001636b93fff51d90baaced1ba75cf9bbaa90600dfc7fd7a705166'
    cp_path=fsroot/'files/nflasha8/cpapp-b.bin';cp=cp_path.read_bytes();assert sha(cp)=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
    cpir_result=dict(source_image=str(image),image_sha256=sha(image.read_bytes()),member='/cpImg.dat',bytes=len(cpir),sha256=sha(cpir),
        header=dict(magic='CPIR',version=version,total=total,table_offset=offset,record_stride=stride,count=count,extra_header_bytes=extra),
        payload_start='0x2740',all_payloads_end_exactly_at_file_end=True,records=items,two_byte_plane_row_pitch_candidates=474,
        pixel_encoding_or_graphics_use_proved=False,CMOS_RAW_or_complete_CP_RAM_image_proved=False,
        full_unmodified_DmmCfg_plain_embedding=dict(cpImg_offset=cpir.find(dmm),cpapp_offset=cp.find(dmm),scope='Exact full-file bytes only; not all compressed/encoded representations.'))
    (HERE/'CPIR-inventory.json').write_text(json.dumps(cpir_result,indent=2)+'\n')
    listing=HERE/'listings';listing.mkdir(exist_ok=False);fragments=[]
    for label,data,base,lo,hi,arch,mode in [
        ('reference-escape-context-properties',ap,AP_BASE,0xfe04eb78,0xfe04ed6c,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN),
        ('reference-class5-escape-load',ap,AP_BASE,0xfe052168,0xfe0522c8,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN),
        ('reference-escape-bulk-transfer',ap,AP_BASE,0xfe052af8,0xfe052bdc,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN),
        ('original-CP-CPIR-header-check',cp,0x108000,0x4aa23c,0x4aa2b0,CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_LITTLE_ENDIAN),
        ('original-CP-CPIR-record-walk',cp,0x108000,0x4aa2dc,0x4aa3c2,CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_LITTLE_ENDIAN)]:
        raw=data[lo-base:hi-base];path=listing/(label+'.txt');md=Cs(arch,mode)
        path.write_text('\n'.join(f'{i.address:#x}: {i.bytes.hex():10} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,lo))+'\n')
        fragments.append(dict(label=label,source='AP_reference' if data is ap else 'FX3_CPapp',VA=hex(lo),end_exclusive=hex(hi),bytes=len(raw),original_bytes_sha256=sha(raw),listing=str(path.relative_to(HERE))))
    proof=dict(AP_reference=dict(path=str(ref),sha256=sha(ap),model='ILCE-7M4 v2.00, not this FX3'),original_CPapp=dict(path=str(cp_path),sha256=sha(cp)),
        original_default_parameters=params,original_table=dict(path=str(table_path),sha256=sha(table)),
        parameter_projection=dict(AP_staging_base=hex(staging),AP_staging_capacity=hex(cap),CP_escape_start=hex(cp_base),CP_escape_end_exclusive=hex(cp_end),
            CP_escape_bytes=hex(cp_end-cp_base),range_equals_nine_original_class5_rows_envelope=True,fits_AP_declared_capacity=cp_end-cp_base<=cap,
            scope='Explicit analytical composition of original AP-default staging and CP-default escape bounds. Not real selected records, not the reference camera runtime values, and not a completed loader.'),
        fragment_cases=cases,class5_rows=ordinary,rows_present_in_original_update_p8=sum(x['present_in_original_update_p8_FAT'] for x in ordinary),
        reference_loading_contract=dict(entry='0xfe0520d4',staging_property='0xfa019a',context_base_property='0xfa01d0',context_end_property='0xfa01d3',
            original_address_arithmetic_PC=['0xfe05227c','0xfe05228c','0xfe052290'],formula='staging + row.start - context.CP_escape_start',file_load_call='0xfe052298 ->0xfe059e20',
            ordinary_class7_skipped=True,ordinary_class5_reaches_file_loader=True),
        unresolved=dict(actual_FX3_AP_loader_not_obtained=True,real_AP_CP_record_selection_unproved=True,
            context_source_pointer_0x38_not_bound_to_staging_in_this_stage=True,actual_file_loading_and_bulk_delivery_unproved=True,
            physical_buffers_RAW_and_full_ISP_unproved=True,flashable_package_produced=False),source_fragments=fragments,
        native_Sony_or_device_operations=0,other_owner_files_written=False)
    out.write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(dict(reference_fragment_results=[dict(path=x['original_row']['path'],result=x['explicit_reference_fragment']['boundary'],destination=x['explicit_reference_fragment']['X1']) for x in cases],
        class5_rows=len(ordinary),present_in_update_p8=proof['rows_present_in_original_update_p8'],CPIR_records=count,CPIR_exact_end=True,whole_target_goal_proved=False)))
if __name__=='__main__':main()
