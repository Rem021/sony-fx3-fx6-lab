"""Bind source-file SIO/clock/time contracts. No original or guest code execution."""
from pathlib import Path
from hashlib import sha256
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
import json,struct
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
NP=B/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin';N=NP.read_bytes();NB=0xfe049000;assert sha256(N).hexdigest()=='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
RP=B/'stage204-public-AP-boot-reference/reference/emmc_boot/esram_0xfe040000.bin';A=RP.read_bytes();AB=0xfe040000;assert sha256(A).hexdigest()=='2e37d90bc8f489db13a0319a3e7f8f1e746921c380484147b922957af3e95d74'
KP=B/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/p3-main/vmlinux.bin';K=KP.read_bytes();assert sha256(K).hexdigest()=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
def word(d,base,a):return int.from_bytes(d[a-base:a-base+4],'little')
def branch(d,base,a):
    w=word(d,base,a);assert w&0xfc000000==0x94000000;n=w&0x3ffffff;return a+4*(n-(1<<26) if n&(1<<25) else n)
w=lambda a:word(N,NB,a)
# The configured file VA is from the package format, not an observed body PC.
format_path=NP.parent/'pformat_config.txt';fmt=format_path.read_text();assert 'load    = 0xFE049000' in fmt
# Current early transfer: SIO0+channel*4096, rate word and128-byte FIFO.
assert w(0xfe052358)==0x528a001d and w(0xfe052378)==0x72be201d
assert w(0xfe0523b4)==0x90000095 and w(0xfe0523e8)==0xb945cea8
assert w(0xfe0523f4)==0x53081d08 and w(0xfe0523f8)==0x11005129
assert w(0xfe052400)==0xb945cea8 and w(0xfe052408)==0x53103d08
assert w(0xfe052410)==0x12081d08 and w(0xfe052414)==0x11006129
assert w(0xfe052470)==0x32081be9 and w(0xfe052478)==0x321903e2
assert w(0xfe052494)==0x11003108 and w(0xfe0524a4)==0x11040340
assert w(0xfe0524e4)==0x11040101 and w(0xfe0524e8)==0x321903e2
# GPIO active assertion uses base+0x48, release base+0x44.
assert w(0xfe0523d0)==0x529a088a and w(0xfe0523d4)==0x72be202a
assert w(0xfe052450)==0x11001129 and w(0xfe052454)==0xb9000128
assert w(0xfe052524)==0xb9000128
# Exact timer entry and conversion are equal in the public reference.
T0,T1=0xfe05863c,0xfe058690;AT=0xfe05aad0
normalizer=N[T0-NB:T1-NB];assert len(normalizer)==84 and normalizer==A[AT-AB:AT-AB+84]
assert branch(N,NB,0xfe05cabc)==T0 and branch(A,AB,0xfe06241c)==AT
assert w(0xfe05864c)==0xd53be028 and w(0xfe058650)==0xd53be009
for a,value in [(0xfe058664,0xd2869b6a),(0xfe058668,0xf2baf6ca),(0xfe05866c,0xf2dbd04a),(0xfe058670,0xf2e8636a),(0xfe058674,0x9bca7d29),(0xfe058678,0xd352fd29),(0xfe05867c,0x9ac90908)]:assert w(a)==value
# LDR64-literal source for the startup MSR CNTFRQ_EL0.
for d,base in [(N,NB),(A,AB)]:
    ww=word(d,base,0xfe049028);assert ww&0xff000000==0x58000000
    imm=(ww>>5)&0x7ffff;imm=imm-(1<<19) if imm&(1<<18) else imm;target=0xfe049028+imm*4
    assert target==0xfe049600 and int.from_bytes(d[target-base:target-base+8],'little')==2000000
    assert word(d,base,0xfe04902c)==0xd51be005
magic=0x431bde82d7b634db;normalization_divisor=((2000000*magic)>>64)>>18;assert normalization_divisor==2
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.detail=True
for i in md.disasm(normalizer,T0):
    reads,writes=i.regs_access();assert not any(i.reg_name(r) in ['x0','w0'] for r in reads)
# Caller timestamps precede assertion/release; thresholds are not pulse widths.
for a in [0xfe0523c4,0xfe05245c,0xfe052504,0xfe05252c]:assert branch(N,NB,a)==0xfe05cab8
assert w(0xfe052464)==0x7101951f and w(0xfe052534)==0x710fa51f
assert w(0xfe052454)==0xb9000128 and w(0xfe052524)==0xb9000128
# Current kernel SIO resource schema:40-byte IOMEM +40-byte IRQ +72-byte clock.
resources=[]
for ch in range(3):
    off=0x63f838+ch*152;raw=K[off:off+152];name=raw[:8].split(b'\0',1)[0].decode();pa,size,va=struct.unpack_from('<QQQ',raw,8)
    assert name==f'sio{ch}' and pa==0xf1005000+ch*4096 and size==4096 and not any(raw[80:152])
    resources.append(dict(channel=ch,record_offset=off,physical=hex(pa),bytes=size,clock_field_offset=80,clock_field_bytes=72,clock_field_all_zero=True))
# Bind fields with the actual current helper's dclk/dclksel offsets by keeping
# current code spans; absent descriptor values do not identify physical parent.
catalog_path=B/'stage146-original-kernel-symbol-and-vendor-route/work/kernel-symbol-catalog.json';catalog=json.loads(catalog_path.read_text())
md.detail=False;pins=[];pd=H/'pins';pd.mkdir()
def pin(path,raw,base,a,z,label,kind='code'):
    part=raw[a-base:z-base];assert len(part)==z-a
    out=pd/(label+'.txt');lines=[part.hex()] if kind=='data' else [f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}' for i in md.disasm(part,a)]
    out.open('x').write('\n'.join(lines)+'\n');pins.append(dict(source=str(path.relative_to(R)),source_sha256=sha256(raw).hexdigest(),base=hex(base),start=hex(a),end_exclusive=hex(z),bytes=z-a,sha256=sha256(part).hexdigest(),kind=kind,output=str(out.relative_to(R))))
for a,z,n,kind in [(0xfe052348,0xfe0523c8,'FX3-SIO-transaction-prefix','code'),(0xfe0523c8,0xfe052458,'FX3-SIO-rate-and-assert','code'),(0xfe052458,0xfe0524b8,'FX3-setup-delta-and-frame','code'),(0xfe0524b8,0xfe052508,'FX3-busy-RX-and-release-baseline','code'),(0xfe052508,0xfe052574,'FX3-release-hold-delta-and-teardown','code'),(0xfe05cab8,0xfe05cac8,'FX3-time-wrapper','code'),(T0,T1,'FX3-counter-normalization','code'),(0xfe049028,0xfe049030,'FX3-CNTFRQ-declaration','code'),(0xfe049600,0xfe049608,'FX3-CNTFRQ-literal','data')]:pin(NP,N,NB,a,z,n,kind)
for a,z,n,kind in [(AT,AT+84,'A7IV-identical-counter-normalization','code'),(0xfe062418,0xfe062428,'A7IV-time-wrapper','code'),(0xfe049028,0xfe049030,'A7IV-CNTFRQ-declaration','code'),(0xfe049600,0xfe049608,'A7IV-CNTFRQ-literal','data')]:pin(RP,A,AB,a,z,n,kind)
pin(KP,K,0,0x63f838,0x63fa00,'current-SIO-resource-descriptors','data')
for name in ['__udif_devio_hclk','__udif_devio_devclk','udif_change_clk']:
    row=next(r for r in catalog if r['name']==name and r['type']=='T');a=row['file_offset'];z=next(r['file_offset'] for r in catalog[row['index']+1:] if r['file_offset']>a);pin(KP,K,0,a,z,'current-'+name)
# Delimiter-selected source pins, no original compile/execution.
sourcepins=[]
def sourcepin(p,first,last,label):
    raw=p.read_bytes();lines=raw.splitlines(keepends=True);a=next(i for i,x in enumerate(lines) if first.encode() in x);z=next(i for i,x in enumerate(lines[a:],a) if last.encode() in x);part=b''.join(lines[a:z+1]);o=H/'source-pins'/(label+'.txt');o.parent.mkdir(exist_ok=True);o.open('xb').write(part);sourcepins.append(dict(source=str(p.relative_to(R)),source_sha256=sha256(raw).hexdigest(),start_line=a+1,end_line_inclusive=z+1,sha256=sha256(part).hexdigest(),output=str(o.relative_to(R))))
g=H/'reference-source/linux-kernel/drivers/udif/mach-cxd900xx'
sourcepin(g/'platform.c','/* SIO */','#endif /* !CONFIG_ARCH_CXD900XX_FPGA_V1_5 */','GPL-SIO-descriptors')
sourcepin(g/'include/mach/udif/clock.h','typedef struct UDIF_CLK_CTL','} UDIF_CLOCK;','GPL-clock-layout')
sourcepin(H/'reference-source/linux-kernel/include/linux/udif/device.h','typedef struct UDIF_CHANNELS','} UDIF_CHANNELS;','GPL-channel-layout')
sourcepin(H/'reference-source/linux-kernel/include/linux/udif/io.h','typedef struct UDIF_IOMEM','} UDIF_IOMEM;','GPL-IOMEM-layout')
sourcepin(H/'reference-source/linux-kernel/include/linux/udif/irq.h','typedef struct UDIF_INTRPT','} UDIF_INTRPT;','GPL-IRQ-layout')
rp=B/'stage205-FX3-hardware-profile-differences/reference/payloads/fastboot/src/darwin.c'
assert sha256(rp.read_bytes()).hexdigest()=='220ce98b18773a66df1aa499e2f9aa6e82dadb6a409d6130f65a5511d8088a1b'
sourcepin(rp,'#define CS_SETUP_US','#define CS_HOLD_US','reference-delay-claims')
sourcepin(B/'stage205-FX3-hardware-profile-differences/reference/payloads/fastboot/include/timer.h','#define TIMER0_HZ','#define TIMER0_TICKS_PER_US','reference-timer0-frequency-claim')
proof=dict(status='FX3_EARLY_SIO_TRANSACTION_AND_SHARED_COUNTER_CONTRACT_BOUND',
 current_NOR=dict(source=str(NP.relative_to(R)),sha256=sha256(N).hexdigest(),configured_file_base=hex(NB),config=str(format_path.relative_to(R)),config_sha256=sha256(format_path.read_bytes()).hexdigest(),actual_PC_observed=False,
    selected_transaction='0xfe052348',rate_input_address='0xfe0625cc',channel_input_address='0xfe0625d0',GPIO_bit_input_address='0xfe0625d4',GPIO_port_input_address='0xfe0625d8',
    frame_bytes=128,SIO_FIFO_offset=256,rate_register_offsets=[20,24],rate_input_initialization_or_current_value_proven=False),
 timing=dict(current_wrapper='0xfe05cab8',current_normalizer=hex(T0),reference_normalizer=hex(AT),full84B_equal=True,reads=['CNTPCT_EL0','CNTFRQ_EL0'],input_x0_unused=True,
    startup_CNTFRQ_literal=2000000,normalization_formula='CNTPCT / (((CNTFRQ * 0x431bde82d7b634db) >>64) >>18)',divisor_at_declared_2MHz=2,
    setup_counter_delta_threshold=101,hold_counter_delta_threshold=1001,baselines_precede_GPIO_edges=True,thresholds_are_not_actual_pin_pulse_widths=True,
    reference_payload_declared_setup_us=150,reference_payload_declared_hold_us=1200,reference_payload_timer0_claimed_Hz=4000000,actual_Timer0_rate_or_PIN_timing_proven=False),
 kernel_SIO_descriptors=resources,kernel_clock_contract_scope='SIO descriptors provide no nonzero hclk/dclk/dclksel settings; this does not prove physical clock absence or identify its parent',
 source_symbol_catalog=str(catalog_path.relative_to(R)),source_symbol_catalog_sha256=sha256(catalog_path.read_bytes()).hexdigest(),selected_original_ranges=pins,source_line_pins=sourcepins,
 SIO_parent_frequency_or_divider_formula_proven=False,current_early_rate3_or19_selected=False,
 limits=['Early loader rate field initialization is unresolved; reference source3 is not established as current FX3 rate','Physical CNTFRQ/Timer0/SIO clock rates and actual GPIO pulse widths were not measured','Image-byte and configured-address contracts are not proof of actual entry or installed same-body p1/ROM identity','No current-body backup, restore, persistent flash or MAIN recording acceptance'],
 Sony_code_or_guest_execution=False,root_or_device_operations=0)
(H/'early-link-and-time-proof.json').open('x').write(json.dumps(proof,indent=2)+'\n')
print(json.dumps(dict(original_ranges=len(pins),source_pins=len(sourcepins),timer84B_equal=True,CNTFRQ_declared=2000000,GPIO_pulse_width_proven=False,early_SIO_rate_value_proven=False,SIO_parent_Hz_proven=False,device_operations=0)))
