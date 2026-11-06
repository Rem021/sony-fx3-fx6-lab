"""No GDB breakpoints or register reads; existing owned-RAM input only."""
import json
from gate_input101 import InputGate,valid_command
class KernelObserver:
 def __init__(self,run,gate,qmp,proof):
  self.run=run;self.gate=gate;self.qmp=qmp;self.points={};self.base=None;self.module_bases={};self.first_unfetched=None;self.removed=False;self.save()
 def install_uipc(self,base):self.module_bases['uipc']=base;self.save()
 def install_gpe(self,base):self.module_bases['gpe']=base;self.save()
 def install(self,base):self.base=base;self.save()
 def poll(self):return False
 def close(self):self.removed=True;self.save()
 def save(self):
  (self.run/'ap104-kernel-observations.json').write_text(json.dumps({'method':'AP104-light per msg_b27db37f09d2: zero GDB CPU breakpoints, zero GDB register reads; existing input and shutdown owned-RAM controls only','module_bases':{k:hex(v)for k,v in self.module_bases.items()},'backup_base_from_sysfs':None if self.base is None else hex(self.base),'installed_points':[],'records_count':0,'first_unfetched':None,'breakpoints_removed':self.removed,'original_words_unchanged':None,'original_word_check_scope':'Not applicable: no original code probes installed','native_completion_scope':'Passive SendDrawComp PLT caller site identifies original SyncCallback or Main failure; direct internal SyncCallback entry is not interposed','timing_limit':'Host stops promptly after observed original printk or native allocation -1018; guest may have executed further calls before host observed UART'},indent=2)+'\n')
