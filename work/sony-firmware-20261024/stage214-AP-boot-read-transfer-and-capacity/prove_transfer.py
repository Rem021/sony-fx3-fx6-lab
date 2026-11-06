"""Static capacity/register, optional crypto context and access-switch proof.

Does not execute target instructions or issue any command to any device.
"""
from pathlib import Path
from hashlib import sha256
import ast,json,struct
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;P=H.parent/'stage213-AP-eMMC-boot-asset-search';R=H.parents[2]
src=P/'originals/current-p3-initrd/kmod/emmc.ko';digest=sha256(src.read_bytes()).hexdigest()
assert digest=='14d17ea8065e3bc751a699dc644f00d247225640175d2957fb2a44bea39e5e4d'
assert sha256((P/'final-receipt.json').read_bytes()).hexdigest()=='ac310d1710a0d2be0eb6b1d2bc5733d9de0a4488a0839cc0b1e28386be60ebaf'
rels=json.loads((P/'driver-relocations-detailed.json').read_text());lookup={(r['section'],r['offset']):r for r in rels}
def dump(name,value):(H/name).open('x').write(json.dumps(value,indent=2)+'\n')
pins=[]
with src.open('rb') as f:
    e=ELFFile(f)
    def pin(label,section,lo,hi,note):
        s=e.get_section_by_name(section);assert 0<=lo<hi<=s['sh_size'];raw=s.data()[lo:hi]
        p=H/'pins'/f'{label}.bin';p.parent.mkdir(exist_ok=True);p.open('xb').write(raw)
        pins.append(dict(label=label,section=section,start=lo,end_exclusive=hi,
            file_offset=s['sh_offset']+lo,bytes=len(raw),sha256=sha256(raw).hexdigest(),raw=str(p.relative_to(R)),
            relocations=[r for r in rels if r['section']==section and lo<=r['offset']<hi],note=note))
        return raw
    pin('EXT_CSD_CMD8_request','.text',0xecc0,0xedac,'Builds one512B CMD8 read into cached response buffer; optional crypto argument cleared.')
    pin('EXT_CSD_cache_owner','.text',0xf058,0xf080,'state.bss+5c0 and cache pointer state+e8; invokes CMD8 helperecc0.')
    pin('boot_multiplier_copy','.text',0xf1ec,0xf20c,'Copies cached EXT_CSD bytee2 to state+dc.')
    pin('boot_capacity_getter','.text',0x145a0,0x145b8,'Unsigned byte state+dc shifted17, pointer relocated to.bss+5c0.')
    pin('sequence_optional_argument','.text',0x12f6c,0x12f84,'Passes original optional argument asx4 to lower read data helper10ec0.')
    pin('multi_read_request_context','.text',0x10fbc,0x10fd8,'Copies saved optional argument into request+10 before lower executor.')
    pin('single_read_request_context','.text',0x11110,0x11138,'CMD17 branch preserves same saved optional argument in request+10.')
    pin('executor_ops_data_call','.text',0xdeac,0xded0,'Calls sequence ops+10; bound by va_emmc_ops relocation.')
    pin('sequence_ops_data_pointer','.data',0xe0,0xe8,'Relocation va_emmc_exec_emmc_data_cmd.')
    pin('host_ops_initialization','.init.text',0x360,0x388,'Literal.data+8 plus30h selects.data+38 host operations at state+10.')
    pin('VA_to_host_data_call','.text',0x4d88,0x4da4,'Host operations+28 -> sdhci data command.')
    pin('host_ops_data_pointer','.data',0x38,0xa0,'Current table.data+38, data command at+28=.data60.')
    pin('host_optional_context_install','.text',0x3e98,0x3eb4,'Takes request+10 and installs it in host state+98 before exec_cmd.')
    pin('optional_callback_reset_skip','.text',0x2220,0x2240,'NULL host context skips optional reset callback+10.')
    pin('optional_callback_transfer_skip','.text',0x22e0,0x2304,'NULL host context skips optional transfer callback+18.')
    pin('optional_callback_wait_skip','.text',0x2670,0x2690,'NULL host context skips optional wait callback+20.')
    pin('partition_type_to_access','.text',0xd110,0xd178,'Switch dispatcher: selected kinds0/1/2 -> masks0/1/2;8/9 ->0.')
    table=pin('partition_type_jump_table','.rodata',2968,2978,'Ten signed relative branch bytes.')
    pin('partition_switch_set_retry_and_panic','.text',0xf618,0xf6f8,'Validates cached PARTITION_CONFIG, sets target access mask with CMD6, retries after error, panics on selected repeated failures.')
    pin('partition_switch_clear_previous','.text',0xf708,0xf73c,'Clears previous nonzero mask using mode2,indexB3 before setting target.')
    pin('CMD6_argument_builder','.text',0xe9e8,0xea70,'CMD6 index6; argument=(access<<24)|(index<<16)|(value<<8).')
    pin('CMD6_set_bits_wrapper','.text',0xeaa8,0xead0,'Uses access mode1,setbits; B3 index and mask supplied by caller.')
    pin('boot_configuration_upper_bits_guard','.text',0xeb88,0xebc0,'Requires (byte&f8)==8 in selected read call with repair flag0.')
    pin('boot_configuration_failure_panic','.text',0xec10,0xec20,'Selected invalid boot configuration guard path calls panic, not a normal read error.')
    def word(section,at):return struct.unpack_from('<I',e.get_section_by_name(section).data(),at)[0]
    w=word('.text',0xf204);assert (w&31)==1 and ((w>>5)&31)==1 and ((w>>10)&4095)==226
    w=word('.text',0xf208);assert (w&31)==1 and ((w>>5)&31)==19 and ((w>>10)&4095)==220
    w=word('.text',0x145a8);assert (w>>16)&63==47 and (w>>10)&63==7
    branches=[]
    for at,target in [(0x2224,0x2240),(0x22e4,0x2304),(0x2674,0x2798)]:
        w=word('.text',at);assert w>>24==0xb4 and (w&31)==0
        n=(w>>5)&0x7ffff;n=n-(1<<19) if n&(1<<18) else n
        assert at+4*n==target;branches.append(dict(offset=at,zero_register='x0',target=target))
    targets=[0xd154+int.from_bytes(bytes([x]),'little',signed=True)*4 for x in table]
    assert targets[:3]==[0xd168,0xd160,0xd158] and targets[8:]==[0xd168,0xd168]
    assert [word('.text',a) for a in [0xd168,0xd160,0xd158]]==[0x52800000,0x52800020,0x52800040]
    assert lookup[('.data',0xe0)]['symbol']=='va_emmc_exec_emmc_data_cmd'
    assert lookup[('.data',0x60)]['symbol']=='sdhci_emmc_exec_data_cmd'
    assert lookup[('.init.text',0x380)]['symbol_section']=='.data' and lookup[('.init.text',0x380)]['addend']==8
    assert lookup[('.text',0xf580)]['symbol_section']=='.bss' and lookup[('.text',0xf580)]['addend']==0x5c0
    assert lookup[('.text',0xf6e8)]['symbol']=='panic' and lookup[('.text',0xec1c)]['symbol']=='panic'

source_lines=[]
for path,needles in [('GPL/include/linux/mmc/mmc.h',['EXT_CSD_BOOT_MULT','EXT_CSD_PART_CONFIG\t','MMC_SWITCH_MODE_SET_BITS','MMC_SWITCH_MODE_CLEAR_BITS']),
                     ('GPL/drivers/mmc/core/mmc.c',['part_size = ext_csd[EXT_CSD_BOOT_MULT] << 17;'])]:
    for i,text in enumerate((H/path).read_text().splitlines(),1):
        if any(n in text for n in needles):source_lines.append(dict(path=path,line=i,text=text))
assert len(source_lines)==5
proof=dict(status='STATIC_BOOT_CAPACITY_SOURCE_AND_SELECTED_READ_CRYPTO_CONTEXT_BOUND',
    source=str(src.relative_to(R)),source_sha256=digest,raw_ranges=pins,source_lines=source_lines,
    capacity=dict(source_register='EXT_CSD[226] BOOT_MULT',state_cache_offset='0xdc',
        bytes_formula='unsignedEXT_CSD[226]<<17',actual_body_value=None,
        CMD8_response_and_standard_register_mapping_bound=True),
    read_view=dict(boot_descriptor_optional_context_null_basis='stage213 AP-storage-contract-proof.json',
        single_and_multi_read_preserve_null_context=True,
        sequence_and_host_function_pointer_tables_bound=True,
        controller_optional_reset_transfer_wait_callbacks_skipped_when_null=True,
        skip_branches=branches,software_path_scope='Selected boot block read omits the identified eMMC decrypt callbacks; ordinary DMA address-mapping callbacks still exist.',
        actual_body_bytes_or_end_to_end_raw_restore_verified=False,
        arbitrary_driver_aliases_or_hardware_crypto_absence_proven=False,
        all_boot_components_plaintext_claimed=False),
    access_switch=dict(software_kind_access_mask={0:0,1:1,2:2,8:0,9:0},register='EXT_CSD[179] PARTITION_CONFIG',
        clears_previous_mask_with_mode=2,sets_target_mask_with_mode=1,
        command_index=6,selected_masks_only_affect_low3bits=True,
        selected_guard_requires_upper_bits='(PARTITION_CONFIG &0xf8)==8',
        access_selection_state_may_change_during_file_read=True,
        error_paths_include_kernel_panic=True,explicit_previous_partition_restoration_after_read_proven=False,
        automatic_recovery_or_power_cycle_effect_proven=False),
    raw_word_checks=9,relocation_checks=6,
    limits=['All paths are static conditions in official7.02 main modules, not measured current p1/body behavior.',
        'No command sequence has been sent; predicted register masks are not actual card receipts.',
        'No claim entire read operation is state-free, or all error paths return normally.',
        'Selected optional decrypt callbacks are closed; actual byte view, restoration and independent entry require their own evidence.'],
    Sony_code_or_guest_execution=False,root_or_device_operations=0,persistent_write_release=False)
dump('AP-transfer-and-capacity-proof.json',proof)
examples=[]
for old in [0,1,2]:
    for new in [0,1,2]:
        steps=[]
        if old!=new:
            if old:steps.append(dict(mode=2,index=179,value=old,arg=hex((2<<24)|(179<<16)|(old<<8))))
            if new:steps.append(dict(mode=1,index=179,value=new,arg=hex((1<<24)|(179<<16)|(new<<8))))
        value=8|old
        for step in steps:value=(value&~step['value']) if step['mode']==2 else value|step['value']
        assert value==(8|new)
        examples.append(dict(previous_kind=old,target_kind=new,source_derived_commands=steps,
            expected_register_value_under_bit_operation_model=value,actual_device_test=False))
dump('access-switch-source-derived-examples.json',dict(scope='9 illustrative source-derived bit-operation examples; no target or guest execution',examples=examples))
candidate=dict(schema='fx3-AP-boot-read-candidate-refinement-v1',previous_candidate='../stage213-AP-eMMC-boot-asset-search/AP-boot-capture-contract-candidate.json',
    additions=['Capacity comes from EXT_CSD[226], not a model-wide constant.',
        'Selected software decrypt callbacks are omitted, but actual dump encoding and restore still require validation.',
        'Kernel read may select eMMC hardware partition through CMD6 and may panic on specified failures; include this in any concrete future device scope.',
        'No automatic claim of previous-partition restoration; unknown state must remain unknown after loss of receipts.'],
    executable=False,new_device_backend=False,camera_operation_authorized=False,actual_device_operations=0,persistent_write_release=False)
dump('AP-boot-read-candidate-refinement.json',candidate)
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
print(json.dumps(dict(raw_ranges=len(pins),source_lines=len(source_lines),raw_word_checks=9,relocation_checks=6,
    capacity_source='EXT_CSD[226]<<17',optional_crypto_callback_skip_branches=3,access_switch_examples=9,actual_device_operations=0)))
