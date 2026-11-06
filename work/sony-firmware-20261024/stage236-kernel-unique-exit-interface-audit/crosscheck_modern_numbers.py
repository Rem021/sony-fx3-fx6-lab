"""Modern numbering source is an explanation, never an FX3 ABI substitute."""
from pathlib import Path
from hashlib import sha256
import json,re
H=Path(__file__).resolve().parent
c=json.loads((H/'modern-number-source-capture.json').read_text());p=H/c['path'];raw=p.read_bytes()
assert len(raw)==c['bytes'] and sha256(raw).hexdigest()==c['sha256']
a=json.loads((H/'kernel-interface-audit.json').read_text());assert a['native_syscall_count']==291
rows=[]
for name,n in [('pidfd_send_signal',424),('pidfd_open',434),('pidfd_getfd',438)]:
    assert re.search(r'^#define __NR_'+name+r' '+str(n)+r'$',raw.decode(),re.M)
    assert n>=a['native_syscall_count']
    rows.append(dict(name=name,modern_v6_1_generic_number=n,outside_saved_FX3_native_dispatch=True))
r=dict(status='PASS',modern_reference=c,rows=rows,source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
       saved_FX3_audit_sha256=sha256((H/'kernel-interface-audit.json').read_bytes()).hexdigest(),
       absence_of_all_vendor_custom_equivalent_interfaces_proven=False,syscalls_or_device_operations=0)
(H/'modern-number-crosscheck.json').open('x').write(json.dumps(r,indent=2)+'\n')
print('PASS: three modern generic syscall numbers exceed saved native dispatch bound')
