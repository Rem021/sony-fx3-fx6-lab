#!/usr/bin/env python3
"""Read-only root-cause localization for model_api boot-screen asserts."""
import hashlib,importlib.util,json,struct
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'; OUT=Path(__file__).resolve().parent.parent/'receipts'
APP=CP/'grm-fbinit/appFw-future-skip.so'; DONOR=TEAM/'donor/nflasha15-files/lib/appFw.so'
BACKUP=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/lifecycle-repair/vmopt-20261103-reload-v1/Backup-generation4-fixed.bin')
FX6=TEAM/'donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin'; FX3=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin')
KEYS=[0x02cf01af,0x02cf0214,0x02cf0215,0x02cf0216,0x02cf0217,0x02cf0218,0x02cf0219]
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def member_bytes(cpio,target):
 with Path(cpio).open('rb') as f:
  while True:
   hd=f.read(110); assert len(hd)==110 and hd[:6]==b'070701'; ns=int(hd[94:102],16); fs=int(hd[54:62],16); n=f.read(ns).rstrip(b'\0'); f.read((4-(110+ns)%4)%4)
   if n==target:return f.read(fs)
   f.seek(fs,1); f.read((4-fs%4)%4)
   if n==b'TRAILER!!!':raise KeyError(target)
def keyvals(path):
 spec=importlib.util.spec_from_file_location('bk4',TEAM/'donor/backup-state-binding/parse_bk4.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 b=path.read_bytes(); out={}
 for k in KEYS:
  try:
   rec,end=m.read_record(b,0,k,require_checksum=True); s=rec['selected']; out[hex(k)]={q:s.get(q) for q in ('present','length','raw_hex','u32_le','property_index','attribute','data_file_offset')};out[hex(k)]['checksum']=rec['checksum_matches']
  except Exception as e:out[hex(k)]={'present':False,'error':repr(e)}
 return out
def asserts(run):
 lines=(run/'serial.log').read_text(errors='replace').splitlines()
 return [{'line':i,'text':l[:400]} for i,l in enumerate(lines,1) if 'assert at model_api' in l or 'Internal error: Oops' in l or 'assert at infra_wrapper_bb_procam_chaplin_base.cpp:1075' in l]
def markers(run):
 lines=(run/'serial.log').read_text(errors='replace').splitlines()
 return {k:sum(1 for l in lines if k in l) for k in ('FX3_AP89_SCREEN_CREATE','FX3_AP89_UUD_DECISION','FX3_MENU','FX3_MEDIA_START_BRANCH','FX3_PROFILE_FRAME')}
def main():
 b=APP.read_bytes(); d=DONOR.read_bytes(); start=0x11f6188; end=0x11f79f8
 # file offset == VMA for first load segment here
 region_app=b[start:end]; region_donor=d[start:end]
 txt=(OUT/'disasm-set_model_for_boot_screen.txt')
 val={'schema':'fx6-r50-boot-screen-contract-v1','appFw':{
  'target':str(APP),'target_sha256':h(APP),'donor':str(DONOR),'donor_sha256':h(DONOR),
  'text_vma':'0xb1a1f0','text_file_offset':'0xb1a1f0','function_vma_start':'0x11f6188','next_function_vma':'0x11f79f8',
  'function_region_sha256_target':hashlib.sha256(region_app).hexdigest(),'function_region_sha256_donor':hashlib.sha256(region_donor).hexdigest(),
  'function_region_identical':region_app==region_donor,'model_func_name_string_vma':'0x24c1500','model_file_string_vma':'0x24be0d8',
  'assert_logger':'0x2167784','assert_logger_return':'0x2167780 ret after printf/usleep; nonfatal logging call',
  'disassembly_receipt':str(txt)},
 'assert_sites':{
  '3147':{'vma':'0x11f72d8','file_offset':'0x11f72d8','condition':'local[b4] is neither 0 nor 1','load':'0x11f7230 ldr w0,[x29,#0xb4]; cbz -> mode1; cmp #1; b.ne assert','assert_args':'w1=0xc4b (3147), x0=model_api.cpp, x2=set_model_for_boot_screen; bl 0x2167784','then':'w20=0; b 0x11f7288; logger returns'},
  '3176':{'vma':'0x11f72a0','file_offset':'0x11f72a0','condition':'local[c4] is neither 0 nor 1','load':'0x11f7288 ldr w1,[x29,#0xc4]; 0 -> 0x11f72e8; 1 -> 0x11f7320; else assert','assert_args':'w1=0xc68 (3176), x0=model_api.cpp, x2=function; bl 0x2167784','then':'w0=0; b 0x11f7310/0x11f7320; logger returns'}},
 'backup_bindings':{'initialization':'0x11f675c [b0]=0; 0x11f6760-0x11f6768 sets [b4..c8]=1 before reads','reads':[
  {'buffer':'[x29,#0xb0]','key':'0x02cf01af','thunk':'0x2169770'}, {'buffer':'[x29,#0xb4]','key':'0x02cf0214','thunk':'0x2169784'}, {'buffer':'[x29,#0xb8]','key':'0x02cf0215','thunk':'0x2169798'}, {'buffer':'[x29,#0xbc]','key':'0x02cf0216','thunk':'0x21697ac'}, {'buffer':'[x29,#0xc0]','key':'0x02cf0217','thunk':'0x21697c0'}, {'buffer':'[x29,#0xc4]','key':'0x02cf0218','thunk':'0x21697d4'}, {'buffer':'[x29,#0xc8]','key':'0x02cf0219','thunk':'0x21697e8'}],
  'call':'each thunk tail-calls Backup_nread@plt with w2=4; appFw ignores w0 return','note':'slots initialized to 1 so a read that does not write remains 0/1 valid; target 4-byte values overwrite them'},
 'backup_values':{'target_66ed_setting_Backup.bin':{'sha256':h(BACKUP),'values':keyvals(BACKUP)},'fx6_chaplin_template':{'sha256':h(FX6),'values':keyvals(FX6)},'fx3_official_seed':{'sha256':h(FX3),'values':keyvals(FX3)},
  'target_cpio_member':{'name':'setting/Backup.bin','sha256':hashlib.sha256(member_bytes(CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio',b'setting/Backup.bin')).hexdigest()},
  'baseline_84db_cpio_member':{'name':'setting/Backup.bin','sha256':hashlib.sha256(member_bytes(CP/'guest-hybrid-fx6kernel-capid-grmreal45.cpio',b'setting/Backup.bin')).hexdigest()},
  'normal_contract':'FX6 template: keys 0x02cf0214/0x02cf0218 are length 1, raw 00/01; target image is length 4 raw 16161616/19191919, matching FX3 seed values; appFw reads 4 bytes and asserts when not 0/1.'},
 'serial':{'66ed':{'lines':asserts(CP/'runs/cp-bind-66ed0f78'),'markers':markers(CP/'runs/cp-bind-66ed0f78')},'84db':{'lines':asserts(CP/'runs/cp-bind-84db17c2'),'markers':markers(CP/'runs/cp-bind-84db17c2')},'9d_screen_create':markers(CP/'runs/cp-bind-9d22099a')['FX3_AP89_SCREEN_CREATE'],'9d_model_asserts':asserts(CP/'runs/cp-bind-9d22099a')},
 'facts':['set_model_for_boot_screen reads Backup keys 0x02cf0214/0x02cf0218 into slots b4/c4 with 4-byte capacity; asserts fire if values are not 0/1.','target and 84db both use setting/Backup.bin sha 92fe...; both have model_api asserts 3147/3176.','target Backup record has 0x02cf0214=16161616 and 0x02cf0218=19191919 (length4, checksum valid); FX6 template has 0x00/0x01 length1 at the same IDs.','target appFw function region is byte-identical to donor appFw at 0x11f6188..0x11f79f8; future::get patch at 0x2159c50 is elsewhere.','assert logger returns; serial continues after both asserts.'],
 'inference':['The two asserts are caused by FX3-format 4-byte backup values at the two keys, not by the later UPM Oops or CAPID path.','Normal boot-screen model contract is not met: Backup must provide FX6-compatible 0/1 values for these IDs / a compatible conversion.','The assert is nonfatal; whether invalid model state directly blocks screen is not proven.'],
 'unknown':['exact producer/writer that should initialize these two IDs at FX6 semantics','whether target Backup.bin 92fe is a rechecksummed FX3 seed or another FX3-compatible image','whether correcting these two values alone would allow screen/menu','downstream use of the fallback mode and whether other model asserts remain','visible pixel/menu/input evidence'],
 'minimum_unmet_contract':'For keys 0x02cf0214 and 0x02cf0218, Backup_nread must return values that represent 0/1; FX6 defaults are length-1 00/01. Target returns 4-byte 0x16161616/0x19191919 from the loaded Backup image, so both boot-screen enum asserts fire. This is a data/contract mismatch, not a missing marker.',
 'screen_causality':{'asserts_fatal':False,'assert_logger_returns':True,'execution_continues_after_asserts':True,'direct_screen_block_proven':False,'note':'Both asserts log and return; no direct branch/abort to screen failure. Marker absence is not proof that no pixel was painted and does not establish causality.'},
 'sufficient_for_next_fix':'Enough to localize the exact boot-screen model contract violation and select a functional repair target (Backup producer/format values at these keys). Not enough to claim a repair will boot/menu; runtime function values and screen/render/input evidence remain required.',
 'existing_index':{'backup_state_binding_README_sha256':hashlib.sha256((TEAM/'donor/backup-state-binding/README.md').read_bytes()).hexdigest(),'static_receipt_sha256':hashlib.sha256((TEAM/'donor/backup-state-binding/static-receipt.json').read_bytes()).hexdigest(),'parse_bk4_sha256':hashlib.sha256((TEAM/'donor/backup-state-binding/parse_bk4.py').read_bytes()).hexdigest(),'used':'existing Backup BK4 parser/static receipt; no new broad scan'}}
 (OUT/'boot-screen-contract.json').write_text(json.dumps(val,indent=2)+'\n');print(json.dumps({'function_identical':val['appFw']['function_region_identical'],'assert_sites':val['assert_sites'],'target_cpio_backup':val['backup_values']['target_cpio_member'],'84db_cpio_backup':val['backup_values']['baseline_84db_cpio_member'],'target_values':{k:val['backup_values']['target_66ed_setting_Backup.bin']['values'][k] for k in ('0x2cf0214','0x2cf0218')},'fx6_values':{k:val['backup_values']['fx6_chaplin_template']['values'][k] for k in ('0x2cf0214','0x2cf0218')},'receipt':str(OUT/'boot-screen-contract.json')},indent=2))
if __name__=='__main__':main()
