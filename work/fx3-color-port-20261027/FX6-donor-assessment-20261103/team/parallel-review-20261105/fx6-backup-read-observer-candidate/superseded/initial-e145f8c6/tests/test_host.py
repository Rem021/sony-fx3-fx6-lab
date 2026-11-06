#!/usr/bin/env python3
"""No-QEMU fixture tests for the two-key observer. Fake RSP is explicitly fake."""
import hashlib,importlib.util,json,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent; CORE=HERE/'observer/observer_core.py'
spec=importlib.util.spec_from_file_location('core',CORE); core=importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
CP=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic')
SERIAL=CP/'runs/cp-bind-66ed0f78/serial.log'; APP=CP/'grm-fbinit/appFw-future-skip.so'
checks=[]
def check(n,f):f();checks.append(n)
def mapping():return core.choose_appfw(SERIAL.read_bytes(),APP)
class Image:
 def __init__(self,base,corrupt=None,reads=None):self.base=base;self.corrupt=corrupt;self.reads=reads or {}
 def virtual_read(self,a,n):
  if a in self.reads:return self.reads[a]
  va=a-self.base; segs=core.elf_loads(APP)
  seg=next((s for s in segs if s['va']<=va and va+n<=s['va']+s['filesz']),None)
  if seg is None:raise ValueError('unmapped read')
  b=bytearray(APP.read_bytes()[seg['fileoff']+va-seg['va']:seg['fileoff']+va-seg['va']+n])
  if self.corrupt is not None and a<=self.corrupt<a+n:b[self.corrupt-a]^=1
  return bytes(b)
def fake(m,key='0x02cf0214',entry=True,ret=True,wrong_pc=False,wrong_frame=False,wrong_lr=False,readfail=False):
 k=next(x for x in core.KEYS if x['name']==key);bias=m['ap']['bias'];fp=0x7ed3d12290;buf=fp+k['slot_off'];tls=0x7f5cfff740
 class F:
  def __init__(self):self.cmd=[];self.regs_ret=False;self.tid='241'
  def command(self,x):self.cmd.append(x);return 'OK'
  def select_thread(self,s):return self.tid
  def regs(self):
   r=[0]*33;r[29]=fp
   if not self.regs_ret:
    r[0]=buf;r[30]=bias+k['return_va'];r[32]=bias+k['thunk_va']
    if wrong_lr:r[30]+=4
    if wrong_pc:r[32]+=4
   else:
    r[0]=0xfffffc03;r[32]=bias+k['return_va'];r[29]=fp+(8 if wrong_frame else 0)
   return tuple(r)
  def virtual_read(self,a,n):
   if readfail:raise ValueError('read failed')
   if a==bias+k['thunk_va']:return bytes.fromhex(k['thunk_word'])
   if a==bias+k['return_va']:return bytes.fromhex(k['return_word'])
   if a==buf:return b'\x01\x00\x00\x00' if not self.regs_ret else b'\x16\x16\x16\x16'
   # identity reads
   va=a-bias;segs=core.elf_loads(APP);seg=next((s for s in segs if s['va']<=va and va+n<=s['va']+s['filesz']),None)
   if not seg:raise ValueError('unmapped')
   return APP.read_bytes()[seg['fileoff']+va-seg['va']:seg['fileoff']+va-seg['va']+n]
 f=F();o=core.Observer(m,f,lambda:tls);return f,o,k
def positive():
 assert core.sha(APP)==core.APPFW_SHA256
 m=mapping();assert m['pid']==237 and m['ap']['bias']==0x7ed3ccc000 and m['epoch']==5
 core.verify_live_identity(Image(m['ap']['bias']),m['ap']['bias'],APP)
 f,o,k=fake(m);o.arm();assert len(o.bp)==2
 o.on_stop('T05thread:241;');assert o.entry and len(o.bp)==2
 f.regs_ret=True
 out=o.on_stop('T05thread:241;');r=out['record'];assert r['key']=='0x02cf0214' and r['return_w0_hex']=='0xfffffc03' and r['before_hex']=='01000000' and r['after_hex']=='16161616';assert len(o.bp)==1 and '0x02cf0218' not in o.done
check('current_epoch5_mapping_and_entry_return_capture',positive)
def second_key():
 m=mapping();f,o,k=fake(m,key='0x02cf0218');o.arm();o.on_stop('T05thread:241;');f.regs_ret=True;out=o.on_stop('T05thread:241;');assert out['record']['key']=='0x02cf0218' and out['record']['before_hex']=='01000000' and out['record']['after_hex']=='16161616' and len(o.bp)==1 and '0x02cf0214' not in o.done
check('second_key_0x02cf0218_entry_return_capture',second_key)
def old_aslr():
 m=mapping();old=0x7ed2a91000
 class Empty:
  def virtual_read(self,a,n):raise ValueError('old ASLR address not current/unmapped')
 try:core.verify_live_identity(Empty(),old,APP)
 except ValueError:pass
 else:raise AssertionError('old address with empty mapping accepted')
 # The current mapping must come from the current serial, not the old constant.
 assert m['ap']['bias']!=old
check('old_ASLR_fixture_not_accepted_by_live_identity',old_aslr)
def bad_elf():
 m=mapping();bias=m['ap']['bias']
 for addr in (bias,bias+0x40,bias+core.KEYS[0]['thunk_va']):
  try:core.verify_live_identity(Image(bias,corrupt=addr),bias,APP)
  except ValueError:pass
  else:raise AssertionError(('corrupt_elf_word_accepted',hex(addr)))
check('wrong_ELF_PHDR_machine_word_rejected',bad_elf)
def wrong_lr_pc():
 for kw in ({'wrong_lr':True},{'wrong_pc':True}):
  m=mapping();f,o,k=fake(m,**kw)
  try:o.arm();o.on_stop('T05thread:241;')
  except ValueError:pass
  else:raise AssertionError(('bad_entry_accepted',kw))
check('wrong_entry_LR_or_PC_rejected',wrong_lr_pc)
def wrong_frame():
 m=mapping();f,o,k=fake(m);o.arm();o.on_stop('T05thread:241;')
 f.regs_ret=True
 # force wrong frame without changing key return
 orig=f.regs
 def regs2():
  r=list(orig());r[29]+=8;return tuple(r)
 f.regs=regs2
 try:o.on_stop('T05thread:241;')
 except ValueError:pass
 else:raise AssertionError('wrong frame accepted')
check('wrong_return_frame_rejected',wrong_frame)
def wrong_thread():
 m=mapping();f,o,k=fake(m);o.arm();o.on_stop('T05thread:241;');f.regs_ret=True;f.tid='999'
 try:o.on_stop('T05thread:999;')
 except ValueError:pass
 else:raise AssertionError('wrong TID accepted')
check('wrong_return_TID_rejected',wrong_thread)
def wrong_tls():
 m=mapping();f,o,k=fake(m);o.arm();o.on_stop('T05thread:241;');f.regs_ret=True;o.tls_reader=lambda:0xdead
 try:o.on_stop('T05thread:241;')
 except ValueError:pass
 else:raise AssertionError('wrong TLS accepted')
check('wrong_return_TLS_rejected',wrong_tls)
def wrong_return():
 m=mapping();f,o,k=fake(m);o.arm();o.on_stop('T05thread:241;');f.regs_ret=True
 orig=f.regs
 def regs2():
  r=list(orig());r[32]+=4;return tuple(r)
 f.regs=regs2
 try:o.on_stop('T05thread:241;')
 except ValueError:pass
 else:raise AssertionError('wrong return call accepted')
check('wrong_return_address_rejected',wrong_return)
def read_fail():
 m=mapping();f,o,k=fake(m,readfail=True)
 try:o.arm();o.on_stop('T05thread:241;')
 except ValueError:pass
 else:raise AssertionError('read failure accepted')
check('read_failure_rejected',read_fail)
def timeout():
 m=mapping();f,o,k=fake(m);o.arm();o.t0-=core.MAX_SECONDS+1
 try:o.on_stop('T05thread:241;')
 except TimeoutError:pass
 else:raise AssertionError('timeout accepted')
check('timeout_rejected',timeout)
def residual():
 m=mapping();f,o,k=fake(m);o.arm()
 class F:
  def command(self,x):return 'E22' if x.startswith('z1,') else 'OK'
 o.rsp=F();r=o.cleanup();assert not r['all_removed'] and r['residual'] and not r['guest_resumed'] and not r['writes_issued']
check('residual_breakpoint_cleanup_visible_no_resume',residual)
out={'status':'PASS_NO_QEMU_FAKE_RSP','fixture':'fake RSP + target serial map + target appFw bytes; NOT real CPU/menu','cases':checks,'count':len(checks),'core_sha256':hashlib.sha256(CORE.read_bytes()).hexdigest()}
(HERE/'tests/host-tests.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
