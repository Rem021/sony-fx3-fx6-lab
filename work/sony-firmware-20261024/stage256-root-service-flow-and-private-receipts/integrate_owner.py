"""Adapt pinned own copies only. No launch, privilege, cache or USB action."""
from pathlib import Path
H=Path(__file__).resolve().parent
def change(name,old,new):
    p=H/name;t=p.read_text();assert old in t,(name,old[:100]);p.write_text(t.replace(old,new,1))
change('owner_iokit.c','#include "target_binding.h"','#include "target_binding.h"\n#include "service_flow.h"\n#include "iokit_adapter.h"\n#include "service_profile.h"')
change('owner_iokit.c','    int device_open, interface_open;','    int device_open, interface_open;\n    uint32_t transferred;\n    fx3_service_flow *flow;')
for function in ['release_interface','return_driver','close_device']:
    marker=f'static int32_t {function}(void *opaque) {{\n    native_owner *p=opaque;'
    change('owner_iokit.c',marker,marker+'\n    if(p->transferred)return p->flow && p->flow->finished && !p->flow->retained?0:(int32_t)kIOReturnNotReady;')
change('owner_iokit.c','static int32_t run_session(void *opaque) {','#include "flow_native.inc"\nstatic int32_t run_session(void *opaque) {')
change('owner_iokit.c','    native_owner *p=opaque;if(!p->channel)return -1;','    native_owner *p=opaque;if(!p->channel || p->channel->scope!=2)return -1;\n    return run_service_flow(p);\n#if 0 /* Preserved status-only implementation, not used by this scope. */')
change('owner_iokit.c','static int cleanup_allowed(void *opaque) {return fx3_channel_cleanup_allowed(&((native_owner *)opaque)->runtime);}', '#endif\n}\nstatic int cleanup_allowed(void *opaque) {native_owner *p=opaque;return !p->flow || !p->flow->taken || (p->flow->finished && !p->flow->retained && !p->flow->journal->failed);}')
# Closing brace of the disabled old function belongs inside the #if0 block.
change('owner_iokit.c','c->protocol_scope>1','c->protocol_scope!=2')
change('owner_iokit.c','channel->scope!=1','channel->scope!=2')
change('owner_iokit.c','    free(owner);\n    return result;','    free(owner->flow);free(owner);\n    return result;')
change('owner_fixture.c','#include <unistd.h>','#include <unistd.h>\n#include <stdlib.h>\n#include "service_flow.h"\nint fx3_fixture_service_run(fx3_service_flow *,fx3_owner_result *,fx3_owner_control *,const fx3_owner_config *,uint32_t);')
change('owner_fixture.c','fault_op,fault; } fixture;','fault_op,fault; fx3_service_flow *flow;fx3_owner_config config; } fixture;')
change('owner_fixture.c','static int32_t release_(void *p) {','static int32_t release_(void *p) { if(f.flow && f.flow->taken)return f.flow->finished && !f.flow->retained?0:-1;')
change('owner_fixture.c','static int32_t return_(void *p) {','static int32_t return_(void *p) { if(f.flow && f.flow->taken)return f.flow->driver_returned?0:-1;')
change('owner_fixture.c','static int32_t close_(void *p) {','static int32_t close_(void *p) { if(f.flow && f.flow->taken)return f.flow->objects_disposed?0:-1;')
change('owner_fixture.c','    (void)unused;(void)hit(P_SESSION);','    (void)unused;(void)hit(P_SESSION);\n    f.flow=calloc(1,sizeof(*f.flow));if(!f.flow)return -1;\n    int flow_rc=fx3_fixture_service_run(f.flow,f.result,f.control,&f.config,f.option);if(f.flow->driver_returned)f.captured=0;return flow_rc;\n#if 0')
change('owner_fixture.c','static int clean_(void *unused) {(void)unused;return fx3_channel_cleanup_allowed(&f.runtime);}', '#endif\n}\nstatic int clean_(void *unused) {(void)unused;return !f.flow || !f.flow->taken || (f.flow->finished && !f.flow->retained && !f.flow->journal->failed);}')
change('owner_fixture.c','    f.result=r;f.control=control;','    f.config=*c;f.result=r;f.control=control;')
change('owner_entry_main.c','#include "helper_hello.h"','#include "helper_hello.h"\n#include "service_flow.h"\n#include "service_profile.h"')
change('owner_entry_main.c','    /* No general native release. A fixed root-private permit is required below. */','    /* This candidate has no approved SERVICE profile or grant. */\n    if(!FX3_SERVICE_PROFILE_READY)return denied("service_profile_not_fixed_no_live_release",77);')
change('owner_entry_main.c','generation=17,.scope=1','generation=17,.scope=2')
change('owner_entry_main.c','channel.path=argv[4];channel.scope=1;','channel.path=argv[4];channel.scope=2;')
change('owner_entry_main.c','work_deadline=started_ns+2000000000ull;final_deadline=started_ns+3000000000ull;','work_deadline=started_ns+10000000000ull;final_deadline=started_ns+12000000000ull;')
change('owner_entry_main.c','        ran=1;private_return=fx3_owner_run_with_channel','''        fx3_flow_journal journal={.fd=-1};char journal_path[4096];
#ifdef FX3_ENTRY_FIXTURE
        int path_n=snprintf(journal_path,sizeof(journal_path),"%s.flow",lease);
#else
        int path_n=snprintf(journal_path,sizeof(journal_path),"%s/private-flow.bin",FX3_ROOT_GRANT_DIR);
#endif
        int journal_ready=path_n>0 && (size_t)path_n<sizeof(journal_path) && !fx3_flow_journal_open(&journal,&channel,&hello,journal_path);
        if(journal_ready)fx3_flow_install_journal(&journal);
        ran=journal_ready;private_return=journal_ready?fx3_owner_run_with_channel''')
change('owner_entry_main.c','(&config,&private_result,&f->control,&channel);','(&config,&private_result,&f->control,&channel):FX3_DENIED;')
change('owner_entry_main.c','        atomic_store_explicit(&context.finished,1,memory_order_release);','        if(journal_ready && fx3_flow_journal_close(&journal))atomic_store(&frame_io.failed,1);\n        fx3_flow_install_journal(NULL);\n        atomic_store_explicit(&context.finished,1,memory_order_release);')
change('host_transport.c','c->scope!=1)return -1; /* no live authentication release */','c->scope!=2)return -1; /* entry additionally requires a new fixed service permit/profile */')
change('owner_receipt.c','memcpy(p,"FX3RCPT1",8);','memcpy(p,"FX3RCPT2",8);')
change('owner_receipt.c','put32(p+8,1);','put32(p+8,2);')
change('entry_shared.h','#define FX3_ENTRY_SCHEMA 3u','#define FX3_ENTRY_SCHEMA 4u')
change('entry_shared.h','#define FX3_ENTRY_SCOPE 0x55534232u','#define FX3_ENTRY_SCOPE 0x53564332u')
change('status_permit.c','"FX3STATUSPERM1"','"FX3SERVICEPERM1"')
change('status_permit.c','0x53544154','0x53564332')
change('receipt_receiver.py',"GRANT_ID='fx3-702-owner-status-20261030-12'","GRANT_ID='fx3-702-service-candidate-20261031-01'")
change('receipt_receiver.py',"data[:8]!=b'FX3RCPT1'","data[:8]!=b'FX3RCPT2'")
change('receipt_receiver.py','(1,BYTES,4)','(2,BYTES,4)')
change('receipt_receiver.py'," or r['wire_pending'] or r['vendor_attempted']:"," or r['wire_pending']:")
change('receipt_receiver.py',"status='HOST_RETURN_OBSERVED' if native==0 else 'HOST_ABORT_RETURN_OBSERVED'","status='HOST_RETURN_CAMERA_STATE_UNVERIFIED' if r['vendor_attempted'] else ('HOST_RETURN_OBSERVED' if native==0 else 'HOST_ABORT_RETURN_OBSERVED')")
change('supervisor.py',"fx3-fixture-ipc250","fx3-fixture-ipc256")
change('supervisor.py',"        self.ops=[(1,b''),(6,b''),(5,b'')]","        self.ops=[]\n        return\n        self.ops=[(1,b''),(6,b''),(5,b'')]")
change('supervisor.py','        if len(data)==676:','        if len(data)==512:\n            raw_file(self.directory/("flow-%04d.bin"%len(self.flow_frames)),data)\n            self.flow_state.accept(data)\n            self.flow_frames.append(data)\n            return\n        if len(data)==676:')
change('supervisor.py','        self.receipt=value','        if value["result"]["vendor_attempted"] and value["phase"]=="COMPLETE" and not self.flow_state.complete:\n            raise R.Rejected("complete vendor result lacks complete flow chain")\n        self.receipt=value')
change('supervisor.py','            if self.total_bytes>8192:','            if self.total_bytes>300000:')
change('supervisor.py','(160,676,1024)','(160,512,676,1024)')
change('supervisor.py','        self.hello=self.receiver.accept_hello(data)','        self.hello=self.receiver.accept_hello(data)\n        from flow_receiver import FlowReceiver\n        self.flow_state=FlowReceiver(self.verified.identity,self.frame.nonce,R.GRANT_ID)\n        self.flow_frames=[]')
change('fixed_launch.py','    # This check precedes any cache query, job creation, Terminal or sudo.','    raise R.Rejected("service candidate has no fixed profile or new live approval; no staging")\n    # Preserved old renderer is unreachable.')
t=(H/'entry_target.h').read_text().replace('fx3-702-owner-status-20261030-12','fx3-702-service-candidate-20261031-01').replace('stage250-corrected-owner-status12-package','stage256-root-service-flow-and-private-receipts').replace('fx3-fixture-ipc250','fx3-fixture-ipc256')
(H/'entry_target.h').write_text(t)
t=(H/'target_binding.h').read_text();t=t[:t.index('static const unsigned char FX3_FIXED_NONCE')]+'''static const unsigned char FX3_FIXED_NONCE[16]={0};
static const unsigned char FX3_FIXED_PRIVACY_KEY[32]={0};
static inline int fx3_target_registry_permitted(uint64_t id,unsigned captured){return captured || id==FX3_CACHED_REGISTRY_ID;}
#endif
''';t=t.replace('4295003368ull','0ull');(H/'target_binding.h').write_text(t)
print('own root entry, source transfer, flow receipts and fixture supervisor integrated; live entry remains closed')
