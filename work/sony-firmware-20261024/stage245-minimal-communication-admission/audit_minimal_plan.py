"""Evaluate a proposed probe from pinned file bytes; no USB or Sony execution."""
from pathlib import Path
from hashlib import sha256
import ast, io, json, struct, plistlib, subprocess
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T'
assert v.get('VolumeUUID','').upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def pin(path,expected):
    data=path.read_bytes();assert sha256(data).hexdigest()==expected
    return data,dict(path=str(path.relative_to(R)),bytes=len(data),sha256=expected)
raw,infra_pin=pin(B/'stage2/extraction/files/nflasha15/lib/libInfraUsbCmn.so',
                 '6caefd0677ee01cc6cdd54555f4422b03a86d12304c60f5372de18315bdd4396')
mod,module_pin=pin(B/'stage138-USB-stop-dispatch-and-Mac-ownership/original-components/kmod/usbg_sen.ko',
                  '1a7294dd9d3babde3f1e8cc2ac4aa12f54356f61995993bbc18ace095ed0cbf2')
public,public_pin=pin(B/'stage134-backup-reader-scope-and-service-extension/upstream/sony.py',
                     '53ffb4d9d49cb5146623fda2b66ecb137681a6fc9ab0c98d23a51e75128af97e')
e=ELFFile(io.BytesIO(raw));m=ELFFile(io.BytesIO(mod));sy=m.get_section_by_name('.symtab')
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
def read(va,n):
    s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz'])
    at=s['p_offset']+va-s['p_vaddr'];return raw[at:at+n]
cls=next(n for n in ast.parse(public.decode()).body if isinstance(n,ast.ClassDef) and n.name=='SonySenserAuthDevice')
values={n.targets[0].id:ast.literal_eval(n.value) for n in cls.body if isinstance(n,ast.Assign)
        and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('SONY_VendorRequest_StartSenser','SONY_VendorRequest_StopSenser')}
start=struct.pack('<BBHHH',0x43,*values['SONY_VendorRequest_StartSenser'],0)
stop=struct.pack('<BBHHH',0x43,*values['SONY_VendorRequest_StopSenser'],0)
assert start.hex()=='4301ff37aad70000' and stop.hex()=='430100c855280000'
assert read(0x1d460,16)==start+stop
native_symbols={s.name:s for s in e.get_section_by_name('.dynsym').iter_symbols()}
name='_ZN13CUsbGadgetSen9on_createEP7CUsbSvcP19CUSB_GADGET_REGINFOP19CUSB_GADGET_CREINFO'
s=native_symbols[name];assert (s['st_value'],s['st_size'])==(0x18cb4,224)
create=read(0x18cb4,224)
create_rows={i.address:dict(pc=i.address,word=i.bytes.hex(),asm=i.mnemonic+' '+i.op_str) for i in md.disasm(create,0x18cb4)}
for pc,text in [(0x18d10,'add x0, x0, #0x460'),(0x18d14,'ldp x2, x3, [x0]'),
                (0x18d1c,'stp x2, x3, [x0, #-0x80]!')]:assert create_rows[pc]['asm']==text
text=m.get_section_by_name('.text').data()[:0xc8]
rel={r['r_offset']:sy.get_symbol(r['r_info_sym']).name for r in m.get_section_by_name('.rela.text').iter_relocations()}
rows={i.address:dict(offset=i.address,word=i.bytes.hex(),asm=i.mnemonic+' '+i.op_str,relocation_symbol=rel.get(i.address)) for i in md.disasm(text,0)}
assert len(rows)==50
for pc,expected in [(0x2c,'mov x2, #8'),(0x3c,'cbz w0, #0x6c'),(0x44,'add x0, x19, #8'),
 (0x50,'cbz w0, #0x68'),(0x68,'mov w21, #1'),(0x78,'cbnz w0, #0xb4'),
 (0x84,'mov w4, #4'),(0x88,'mov w3, #7'),(0x90,'str w21, [x5, #-4]!'),
 (0x9c,'b #0x54'),(0x58,'mov w0, #2')]:assert rows[pc]['asm']==expected
for pc,target in [(0x34,'memcmp'),(0x4c,'memcmp'),(0x70,'usb_gadgetcore_stop_other_driver'),(0x98,'usb_event_add_queue')]:assert rows[pc]['relocation_symbol']==target

plan=dict(schema='fx3-minimal-communication-proposal-v1',
 purpose='Review only: one challenge request without authentication digest, file commands, upload or firmware write.',
 initial_identity=dict(VID=0x054c,PID=0x0da1,mode='MSC',actual_current_device_not_queried=True),
 proposed_operations=[
  dict(index=1,operation='START',kind='control_out',setup_hex=start.hex(),data_bytes=0),
  dict(index=2,operation='REQUEST_ONE_CHALLENGE',kind='bulk_out',bytes=516,header_hex='fffe0000',zero_payload_bytes=512),
  dict(index=3,operation='RECEIVE_ONE_CHALLENGE',kind='bulk_in',bytes=516,accepted_reference_codes=[2,8]),
  dict(index=4,operation='STOP',kind='control_out',setup_hex=stop.hex(),data_bytes=0)],
 proposed_global_budget_ms=10000,proposed_per_native_call_timeout_ms=1000,
 time_limits_are_checks_not_a_way_to_interrupt_blocked_calls=True,
 max_native_transfers=4,digest_command3_permitted=False,final_auth_command5_permitted=False,
 file_select_GET_DMM_upload_or_firmware_commands_permitted=False,
 arbitrary_payload_interface=False,automatic_retries_resets_kills_or_mode_fallback=False,
 guarantee_no_mode_or_driver_state_change=False,
 executable_or_approved=False,export_as_live_tool=False,
 entry_success_criterion='requires exact device state evidence; USB ACK or matching VID/PID alone is insufficient',
 exit_success_criterion='requires actual worker/session ending and driver ownership return; STOP return alone is insufficient',
 ambiguity='retain UNKNOWN; no extra request or fabricated completion based only on timeout/error')
decision=dict(status='REJECT_NO_MODE_CHANGE_MINIMAL_SENSER_PROPOSAL',milestone=2,milestone_complete=False,
 new_feature_or_real_camera_acceptance=False,
 reason='The very first START matches the saved FX3 Senser headers and enters a callback that calls stop_other_driver before trying to enqueue an event. Both START and STOP share this path; this proposal cannot meet a no-driver-state-change contract.',
 facts_reused_not_new_runtime_discovery=['stage138 configured headers and callback','stage145 error/side-effect boundary','stage146 saved kernel boundary'],
 inference='Restricting later commands or omitting authentication digests does not remove the initial control-request effects.',
 protocol_codes2_8_are_reference_not_current_FX3_MSC_proof=True,
 exact_current_body_callback_registration_queue_completion_or_USB_wire_status_verified=False,
 current_host_backend_native_release=False,
 host_only_prerequisite=dict(plan='stage195-root-host-validation-plan/README.md',
  fixed_bundle_sha256='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0',
  executed=False,scope='host-only; no IOKit/USB/Sony backend',
  not_a_camera_approval=True,not_reapproved_or_requested_by_this_batch=True),
 next_real_validation='Host-side cross-UID identity and protected-receipt validation is prepared but remains unexecuted. Actual camera work would then need a separate fixed scope acknowledging possible driver/session effects and verified return handling.',
 stop_this_offline_branch='Do not generate more scenarios for this same no-mode-change proposal. Reconsider only after new host/body evidence or a genuinely different bounded interface exists.',
 new_camera_USB_cache_admin_auth_or_firmware_operations=0,previous_model_tests_repeated=0,
 persistent_write_release=False)
evidence=dict(status='SAVED_HEADERS_AND_CALLBACK_REBOUND_TO_THE_REJECTED_PROPOSAL',
 sources=[infra_pin,module_pin,public_pin],public_AST_only=True,
 configured_header_VA=0x1d460,configured_headers_hex=(start+stop).hex(),
 creation_function=dict(name=name,VA=0x18cb4,bytes=224,sha256=sha256(create).hexdigest(),instructions=list(create_rows.values())),
 kernel_callback=dict(section='.text',offset=0,bytes=len(text),sha256=sha256(text).hexdigest(),instructions=list(rows.values())),
 original_Sony_Linux_glibc_or_downloaded_camera_code_executed=False,
 reuses_prior_static_findings_for_new_admission_decision_not_new_hardware_proof=True)
for name,value in [('probe-plan.json',plan),('decision.json',decision),('source-binding.json',evidence)]:
    with (H/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status=decision['status'],plan_operations=len(plan['proposed_operations']),new_model_or_camera_tests=0)))
