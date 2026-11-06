"""Derive a status-only owner candidate from own pinned sources; never run it."""
from pathlib import Path
from hashlib import sha256
import json,difflib
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
A=B/'stage194-supervised-fixed-launch';T=B/'stage195-root-host-validation-plan'
assert not (H/'source-origins.json').exists()
old=json.loads((A/'build-receipt-v2.json').read_text())
for x in old['sources']:assert sha256((A/x['path']).read_bytes()).hexdigest()==x['sha256']
approval=(T/'approval-bundle.json').read_bytes()
assert sha256(approval).hexdigest()=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
for x in json.loads(approval)['files']:
 data=(T/x['path']).read_bytes();assert len(data)==x['bytes'] and sha256(data).hexdigest()==x['sha256']
names=('owner_core.c owner_ipc.c entry_support.c owner_entry_main.c owner_channel.c iokit_wire.c native_session.c global_guard.c frame_io.c owner_receipt.c owner_iokit.c owner_fixture.c fake_iokit.c entry_shared.h entry_target.h owner_trial.h owner_channel.h iokit_wire.h native_session.h global_guard.h frame_io.h owner_receipt.h helper_hello.h host_login.h controller_ipc.py receipt_receiver.py supervisor.py fixed_launch.py').split()
origins=[]
for name in names+['helper_hello.c','host_login.c','host_transport.c','host_transport.h']:
 source=(T if name in ('helper_hello.c','host_login.c','host_transport.c','host_transport.h') else A)/name
 before=source.read_text();text=before
 if name=='host_transport.c':
  text=text.replace('#ifndef HOST_FIXTURE','#ifndef FX3_OWNER_CHANNEL_FIXTURE')
 if name=='host_transport.h':
  text=text.replace('    int fd;','    int fd;\n#ifdef FX3_OWNER_CHANNEL_FIXTURE\n    void (*before_request)(void *);\n    void *fixture;\n#endif')
 if name=='owner_channel.h':
  first=text.index('/* Private root-side config;');last=text.index('typedef struct {\n    fx3_io_context',first)
  text=text[:first]+'/* Shared base protocol is the HOST_ONLY transport validated in246. */\n#include "host_transport.h"\n'+text[last:]
 if name=='owner_channel.c':
  a=text.index('int fx3_channel_peer(');z=text.index('static int wait_fd(',a);text=text[:a]+text[z:]
  a=text.index('int fx3_channel_connect(');z=text.index('static int peer_callback(',a);text=text[:a]+text[z:]
  text=text.replace('!cfg || !owner || !report || !fx3_channel_peer(cfg)',
                    '!cfg || cfg->scope!=1 || !owner || !report || !fx3_channel_peer(cfg)')
  text=text.replace('if(cfg->scope==1 && op!=FX3S_OBSERVE && op!=FX3S_STATUS && op!=FX3S_END)',
                    'if(op!=FX3S_OBSERVE && op!=FX3S_STATUS && op!=FX3S_END)')
 if name=='owner_receipt.h':
  a=text.index('typedef struct {');z=text.index('/* Only private entry state',a);text=text[:a]+text[z:]
 if name=='owner_receipt.c':
  a=text.index('int fx3_receipt_peer_ack(');z=text.index('int fx3_receipt_send(',a);text=text[:a]+text[z:]
  text=text[:text.index('int fx3_receipt_send_bytes(')]
 if name=='owner_entry_main.c':
  text=text.replace('channel.path=argv[4];channel.scope=(option&4096)?2:1;','channel.path=argv[4];channel.scope=1;')
 if name=='supervisor.py':
  text=text.replace("ROOT/'work/ipc194'","Path('/private/tmp/fx3-fixture-ipc247')")
  text=text.replace("self.ops=[(1,b''),(5,b'')]","self.ops=[(1,b''),(6,b''),(5,b'')]")
 text=text.replace('fx3-702-supervised-owner-20261029-10','fx3-702-owner-status-20261030-11')
 text=text.replace('stage194-supervised-fixed-launch','stage247-shared-host-transport-owner-status')
 text=text.replace('/Volumes/KAFU2T/AI/Projects/Mac/work/ipc194/','/private/tmp/fx3-fixture-ipc247/')
 text=text.replace('build-receipt-v2.json','build-receipt.json')
 with (H/name).open('x') as f:f.write(text)
 origins.append(dict(path=name,source=str(source.relative_to(R)),source_sha256=sha256(before.encode()).hexdigest(),
                     candidate_sha256=sha256(text.encode()).hexdigest(),
                     diff=''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile=str(source.relative_to(R)),tofile=name))))
assert '#define FX3_NATIVE_RELEASED 0' in (H/'entry_target.h').read_text()
with (H/'source-origins.json').open('x') as f:json.dump(origins,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(own_source_files=len(origins),native_release=False,administrator_or_device_operations=0)))
