#!/usr/bin/env python3
"""Compare a public AP reference with FX3 CP consumers; no hardware transfer."""
import hashlib,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from unicorn import Uc,UcError,UC_ARCH_ARM64,UC_MODE_ARM,UC_PROT_READ,UC_PROT_EXEC,UC_HOOK_CODE,UC_HOOK_MEM_INVALID,UC_HOOK_MEM_WRITE
from unicorn import arm64_const as R

HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PROJECT=HERE.parents[2]
FW=PROJECT/'work/sony-firmware-20261024';AP_BASE=0xfe040000;CP_BASE=0xfe049000;ROW=0x100000000
AP_PIN='2e37d90bc8f489db13a0319a3e7f8f1e746921c380484147b922957af3e95d74'
CP_PIN='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
def sha(b):return hashlib.sha256(b).hexdigest()


def field(words,n):
    return (words[n]>>5)&0xffff


def mov_address(words):
    value=field(words,0)
    for w in words[1:]:
        shift=((w>>21)&3)*16;value=(value&~(0xffff<<shift))|(((w>>5)&0xffff)<<shift)
    return value


class Fragment:
    def __init__(self,ap,row):
        self.u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);self.u.mem_map(AP_BASE,(len(ap)+4095)&~4095,UC_PROT_READ|UC_PROT_EXEC);self.u.mem_write(AP_BASE,ap)
        self.u.mem_map(ROW,4096,UC_PROT_READ);self.u.mem_write(ROW,row)
        self.u.reg_write(R.UC_ARM64_REG_X26,ROW+0x18)
        self.boundary=None;self.trace=[]
        self.u.hook_add(UC_HOOK_CODE,self.code);self.u.hook_add(UC_HOOK_MEM_INVALID,self.invalid);self.u.hook_add(UC_HOOK_MEM_WRITE,self.write)
    def stop(self,reason,**extra):
        self.boundary=dict(reason=reason,PC=hex(self.u.reg_read(R.UC_ARM64_REG_PC)),**extra);self.u.emu_stop()
    def code(self,u,pc,size,user):
        if pc==0xfe05a1e0:self.stop('before_original_file_size_query');return
        if pc==0xfe052e4c:self.stop('before_original_skip_diagnostic');return
        if not 0xfe052d4c<=pc<0xfe052e4c:self.stop('before_outside_selected_fragment');return
        self.trace.append(hex(pc))
    def invalid(self,u,access,at,size,value,user):
        self.stop('before_unknown_state',address=hex(at),bytes=size);return False
    def write(self,u,access,at,size,value,user):self.stop('unexpected_write',address=hex(at),bytes=size)
    def run(self):
        try:self.u.emu_start(0xfe052d4c,0xfe052e50,timeout=1000000,count=1000)
        except UcError:
            if self.boundary is None:raise
        assert self.boundary is not None
        return dict(boundary=self.boundary,original_instruction_entries=len(self.trace),trace=self.trace,
            registers=dict(X0=hex(self.u.reg_read(R.UC_ARM64_REG_X0)),W8=hex(self.u.reg_read(R.UC_ARM64_REG_W8)),W29=hex(self.u.reg_read(R.UC_ARM64_REG_W29))),
            state_supplied='Original row bytes and X26=explicit row path pointer only; no boot context, disk data or successful helper replies.',
            model_or_firmware_bytes_modified=False,file_query_or_transfer_executed=False)


def main():
    output=HERE/'handoff-source-proof.json';assert not output.exists()
    source_dir=FW/'stage204-public-AP-boot-reference';inventory=json.loads((source_dir/'source-capture.json').read_text())
    source=next(x for x in inventory['files'] if x['path']=='emmc_boot/esram_0xfe040000.bin')
    ap_path=PROJECT/source['output'];ap=ap_path.read_bytes();assert sha(ap)==source['sha256']==AP_PIN and len(ap)==190464
    assert hashlib.sha1(b'blob '+str(len(ap)).encode()+b'\0'+ap).hexdigest()==source['git_blob_sha1']
    cp_path=TASK/'config-producer-20261029/original-files/loader_nor.bin';cp=cp_path.read_bytes();assert sha(cp)==CP_PIN
    sources=json.loads((TASK/'config-producer-20261029/load-descriptor-sources.json').read_text())
    bank=next(x for x in sources['templates'] if x['member']==sources['canonical_template'])['banks'][1]
    payload_path=TASK/'config-producer-20261029'/bank['saved_payload'];payload=payload_path.read_bytes();assert sha(payload)==bank['payload_sha256']
    rows=[]
    for name,expected in [('DmmCfg.bin','before_original_skip_diagnostic'),('tomco.txt','before_original_file_size_query')]:
        record=next(x for x in bank['entries'] if x['path'].lstrip('\\')==name);at=int(record['record_offset'],16);raw=payload[at:at+0x90]
        assert sha(raw)==record['original_record_sha256'] and struct.unpack_from('<I',raw,0x14)[0]==int(record['mode'],16)
        result=Fragment(ap,raw).run();assert result['boundary']['reason']==expected
        if name.endswith('DmmCfg.bin'):assert result['registers']['W29']=='0x0'
        rows.append(dict(original_FX3_row=record,original_row_sha256=sha(raw),AP_reference_fragment=result))
    # Independent immediate-field arithmetic, not Capstone's printed constants.
    u32=lambda data,base,pc:struct.unpack_from('<I',data,pc-base)[0]
    AP_KRNE=mov_address([u32(ap,AP_BASE,p) for p in [0xfe052a10,0xfe052a18]])
    CP_KRNE=mov_address([u32(cp,CP_BASE,p) for p in [0xfe052e88,0xfe052e8c]])
    AP_ESCP=mov_address([u32(ap,AP_BASE,p) for p in [0xfe052afc,0xfe052b00]])
    CP_ESCP=mov_address([u32(cp,CP_BASE,p) for p in [0xfe052e04,0xfe052e08]])
    krne_dest=mov_address([u32(ap,AP_BASE,p) for p in [0xfe052a0c,0xfe052a14,0xfe052a20]])
    escp_dest=mov_address([u32(ap,AP_BASE,p) for p in [0xfe052bb0,0xfe052bb4,0xfe052bb8]])
    cp_krne_source=mov_address([u32(cp,CP_BASE,p) for p in [0xfe052e78,0xfe052e7c,0xfe052e80]])
    cp_escp_source=mov_address([u32(cp,CP_BASE,p) for p in [0xfe052df4,0xfe052df8,0xfe052dfc]])
    assert AP_KRNE==CP_KRNE==0x454e524b and AP_ESCP==CP_ESCP==0x50435345
    assert krne_dest==cp_krne_source==0x800107f20 and escp_dest==cp_escp_source==0x800107f30
    md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);listing=HERE/'listings';listing.mkdir(exist_ok=False)
    windows=[]
    for name,data,base,lo,hi in [
        ('AP-reference-KRNE-producer',ap,AP_BASE,0xfe052a08,0xfe052a3c),
        ('AP-reference-ESCP-producer',ap,AP_BASE,0xfe052af8,0xfe052bdc),
        ('AP-reference-handoff-pointer',ap,AP_BASE,0xfe0528c4,0xfe052968),
        ('AP-reference-transfer-class-filter',ap,AP_BASE,0xfe052d4c,0xfe052e60),
        ('AP-reference-transfer-function-prefix',ap,AP_BASE,0xfe05d884,0xfe05d8dc),
        ('FX3-original-CP-consumers',cp,CP_BASE,0xfe052de0,0xfe052ee8),
    ]:
        raw=data[lo-base:hi-base];file=listing/(name+'.txt')
        file.write_text('\n'.join(f'{i.address:#x}: {i.bytes.hex():8} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,lo))+'\n')
        windows.append(dict(source='AP_reference' if data is ap else 'FX3_CP',VA=hex(lo),end_exclusive=hex(hi),bytes=len(raw),original_bytes_sha256=sha(raw),listing=str(file.relative_to(HERE))))
    result=dict(source_AP=dict(path=str(ap_path),sha256=AP_PIN,bytes=len(ap),commit=inventory['commit'],upstream_path=source['path'],git_blob_sha1=source['git_blob_sha1'],model='Public ILCE-7M4 v2.00 reference, not this FX3'),
        source_CP=dict(path=str(cp_path),sha256=CP_PIN,bytes=len(cp),role='Original classic FX3 7.02 CP NOR component'),
        original_FX3_table=dict(path=str(payload_path),sha256=sha(payload),bytes=len(payload),canonical_template_is_body_selection=False),
        handoff_contract=dict(KRNE=dict(value=hex(AP_KRNE),AP_entry='0xfe052a08',AP_call='0xfe052a30',CP_consumer='0xfe052e74',address=hex(krne_dest),bytes=4),
            ESCP=dict(value=hex(AP_ESCP),AP_entry='0xfe052af8',AP_marker_call='0xfe052bc8',CP_consumer='0xfe052de0',address=hex(escp_dest),bytes=4),
            pointer=dict(AP_call='0xfe052930',address='0x800107f28',bytes=8,source='first u64 of current original load-table row, staged at AP context+8',CP_read='0xfe052e98',CP_context_store='0xfe052ea8'),
            reference_transfer_callee='0xfe05d884',actual_transfer_or_marker_delivery_proved=False,target_FX3_AP_sender_located=False),
        original_row_fragment_results=rows,source_fragments=windows,
        interpretation=dict(reference_marker_producers_located=True,matching_interface_with_FX3_original_CP=True,
            original_DmmCfg_mode='0x05000000',ordinary_AP_reference_transfer_path_skips_this_row=True,
            original_tomco_mode='0x07000000',tomco_reaches_file_query_boundary_only=True,
            full_FX3_normal_loader_or_DmmCfg_data_arrival_proved=False,physical_buffer_RAW_or_full_ISP_obtained=False,flashable_package_produced=False),
        scope='Only read original reference SRAM and FX3 components. Two independent reference-code fragments use untouched original FX3 table rows as explicit analytical inputs. They are not a reconstructed actual AP boot. No boot metadata or helper replies supplied; no ROM/key derivation, source updater/script, device, USB, physical PCIe transfer, CPU maintenance or storage write.')
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(marker_values_match=True,destination_addresses_match=True,original_rows=[dict(path=x['original_FX3_row']['path'],boundary=x['AP_reference_fragment']['boundary']) for x in rows],static_windows=len(windows),actual_transfer_proved=False)))
if __name__=='__main__':main()
