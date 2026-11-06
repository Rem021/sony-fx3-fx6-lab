/* Self identity only; no audit setters, TCC API or USB/IOKit operation. */
#include "host_login.h"
#include <bsm/audit.h>
#include <stdio.h>
#include <string.h>

void fx3_host_login_read(fx3_host_login *v) {
    memset(v,0,sizeof(*v));
    au_id_t auid=(au_id_t)-1;
    auditinfo_addr_t audit;memset(&audit,0,sizeof(audit));
    v->auid_return=getauid(&auid);
    v->audit_return=getaudit_addr(&audit,sizeof(audit));
    v->security_return=SessionGetInfo(callerSecuritySession,&v->security_session,&v->attributes);
    v->audit_uid=(uint32_t)auid;
    v->audit_record_uid=(uint32_t)audit.ai_auid;
    v->audit_session=(uint32_t)audit.ai_asid;
}

int fx3_host_login_valid(const fx3_host_login *v,uint32_t uid) {
    return uid==501 && !v->auid_return && !v->audit_return && !v->security_return &&
        v->audit_uid==uid && v->audit_record_uid==uid && v->audit_session &&
        v->audit_session!=(uint32_t)-1 && v->audit_session==v->security_session &&
        (v->attributes&sessionHasGraphicAccess) && (v->attributes&sessionHasTTY) &&
        !(v->attributes&sessionIsRemote);
}

void fx3_host_login_print_json(const fx3_host_login *v) {
    printf(",\"host_login\":{\"schema\":1,\"getauid_return\":%d,\"getaudit_return\":%d,"
        "\"security_session_return\":%d,\"audit_uid\":%u,\"audit_record_uid\":%u,"
        "\"audit_session_id\":%u,\"security_session_id\":%u,\"security_session_attributes\":%u,"
        "\"has_graphic_access\":%s,\"has_tty\":%s,\"is_remote\":%s}",
        v->auid_return,v->audit_return,(int)v->security_return,
        v->audit_uid,v->audit_record_uid,v->audit_session,(unsigned)v->security_session,(unsigned)v->attributes,
        (v->attributes&sessionHasGraphicAccess)?"true":"false",
        (v->attributes&sessionHasTTY)?"true":"false",
        (v->attributes&sessionIsRemote)?"true":"false");
}
