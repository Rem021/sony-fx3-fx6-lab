"""Static FX3 phase audit. No original instructions, USB or helper execution."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,struct
from elftools.dwarf.callframe import FDE

H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
spec=importlib.util.spec_from_file_location('cooperator252',B/'stage149-normal-cooperator-and-NIN-checkpoint/normal_cooperator.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
obj,core=module.images()
functions=[core.function(n) for n in ['NinThread','_Z9SerializePFiPhmEPvm','_Z9CmdDecodePtPh']]
frames={f['initial_location']:f['address_range'] for f in core.elf.get_dwarf_info().EH_CFI_entries() if isinstance(f,FDE)}
at=0xb19c;size=frames[at];functions.append(dict(name='local transport-state helper',VA=hex(at),bytes=size,sha256=sha256(core.read(at,size)).hexdigest(),instructions=core.instructions(at,size)))
ins={int(i['pc'],16):i for f in functions for i in f['instructions']}
expected={0xbc68:'bl #0xa980',0xbc88:'bl #0xac90',0xbc94:'bl #0xa980',0xbcb0:'bl #0xa580',
 0xbcb4:'mov x1, x23',0xbe6c:'bl #0xa580',0xbea4:'blr x2',0xbf2c:'blr x2',0xbf30:'bl #0xa340',
 0xbf4c:'bl #0xaa70',0xbf64:'cmn w19, #1',0xbf68:'b.eq #0xbc60',
 0xbf70:'and w0, w0, #0xfffffffd',0xbf78:'cmp w0, #5',
 0xb324:'blr x21',0xb328:'add w1, w0, #6',0xb32c:'tst w1, #0xfffffffd',0xb330:'b.ne #0xb35c',
 0xb350:'bl #0xac90',0xb358:'b #0xb350',0xb35c:'cmp w0, #0',0xb360:'b.ge #0xb38c',
 0xb380:'bl #0xac90',0xb388:'b #0xb380',0xb38c:'b.eq #0xb39c',0xb398:'b.hs #0xb3c4',
 0xb3b8:'bl #0xac90',0xb3c0:'b #0xb3b8',0xb3cc:'b #0xb318',0x15b90:'and w1, w1, #0xff'}
for pc,asm in expected.items():assert ins[pc]['asm']==asm,(hex(pc),ins[pc])
jump_raw=core.read(0x1694c,14);jump={n:0xbce8+4*d for n,d in enumerate(struct.unpack('<7h',jump_raw),1)}
assert jump=={1:0xbce8,2:0xc01c,3:0xbd44,4:0xc01c,5:0xbe28,6:0xc01c,7:0xbe28}
special=[n for n in range(-100,1) if (((n+6)&0xffffffff)&0xfffffffd)==0];assert special==[-6,-4]
reference=B/'stage145-initial-MSC-native-route/work/official-kernel-reference/linux-kernel/drivers/usb/gcore/usb_gcore_setup.c'
ref=reference.read_bytes();text=ref.decode('utf-8',errors='replace');start=text.index('static int setup_class_specific(struct g_core_drv *g_core,');end=text.index('static int setup_vendor_specific(',start)
snippet=text[start:end];assert 'config    == cfg_num' in snippet and 'interface == in_num' in snippet and 'func_drv->class' in snippet
report=dict(status='STATIC_PHASE_AND_CANCELLATION_BOUNDARIES_VERIFIED_NOT_LIVE_ADMISSION',
 core_sha256=sha256(core.raw).hexdigest(),functions=functions,checked_instructions=len(expected),
 command_jump_table=dict(VA='0x1694c',raw_hex=jump_raw.hex(),targets={str(k):hex(v)for k,v in jump.items()}),
 newly_scoped_findings=[
  'Command1 challenge enters0xbce8. Commands5 and7 both enter completion0xbe28; a future probe must forbid both, not merely document no command5.',
  'Serialize does not return ordinary error codes on callback failure: -6/-4, other negative, zero or over-size results enter cancellation/testcancel/yield loops.',
  'Positive short progress accumulates until requested length; no local time deadline is present in this function. The underlying callback blocking behavior is not proved.',
  'A challenge-only host exchange omits the ordinary completion branch, but this does not establish STOP handling, callback unblocking, cancellation or thread exit.',
  'Reference class dispatch selects configuration/interface and calls a class callback; the class response carries no NIN thread-termination record. GET_MAX_LUN may be auxiliary readiness evidence, not sole service-exit proof.'
 ],
 correction_to_unpublished_hypothesis='Do not describe Serialize failure as returning stale data into CmdDecode: its observed failure branches loop pending cancellation instead of returning.',
 final_response_before_history_calls=dict(final_serialize='0xbe6c',regist_haspi_callback='0xbea4',normal_completion_callback='0xbf2c',tlog_presence='0xbf30',tlog_update='0xbf4c',mode_write='0xc044'),
 phase_impact=[
  dict(phase='START',effect='stop-other-driver/event path already pinned in245; state change possible',scope='not a metadata query'),
  dict(phase='CMD1 challenge',effect='ordinary challenge response path, no direct jump to completion branch',scope='does not establish no effects in other threads or exceptional shutdown'),
  dict(phase='CMD3 digest',effect='updates authentication round state, including failure state',scope='not part of challenge-only proposal'),
  dict(phase='CMD5 or CMD7 completion',effect='completion branch, normal callback and conditional history/mode paths',scope='excluded from challenge-only proposal'),
  dict(phase='STOP',effect='asynchronous stop/cancel path from137/139',scope='host completion alone not camera thread completion'),
  dict(phase='MSC class response',effect='protocol/class readiness only',scope='not a thread-completion receipt')],
 class_reference=dict(path=str(reference.relative_to(R)),sha256=sha256(ref).hexdigest(),version='official FX3 Ver700 reference, not exact702 build',source_excerpt=snippet),
 instruction_or_kernel_execution=False,new_camera_or_cache_admin_operations=0,
 old251_host_return_scope_still_passed=True,Sony_live_scope_approved=False,first_flash_released=False)
with (H/'phase-impact-audit.json').open('x')as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status=report['status'],complete_original_functions=len(functions),checked_instructions=len(expected),special_negative_returns=special,command5_and7_same_completion_branch=True,live_operations=0)))
