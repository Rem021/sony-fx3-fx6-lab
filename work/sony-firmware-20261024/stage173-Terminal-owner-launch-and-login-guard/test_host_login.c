#include "host_login.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    fx3_host_login good={.audit_uid=501,.audit_record_uid=501,.audit_session=100022,
        .security_session=100022,.attributes=sessionHasGraphicAccess|sessionHasTTY},bad;
    assert(fx3_host_login_valid(&good,501));
    assert(!fx3_host_login_valid(&good,0));
    assert(!fx3_host_login_valid(&good,502));
    bad=good;bad.audit_uid=0;assert(!fx3_host_login_valid(&bad,501));
    bad=good;bad.audit_uid=(uint32_t)-1;assert(!fx3_host_login_valid(&bad,501));
    bad=good;bad.audit_record_uid=0;assert(!fx3_host_login_valid(&bad,501));
    bad=good;bad.auid_return=-1;assert(!fx3_host_login_valid(&bad,501));
    bad=good;bad.audit_return=-1;assert(!fx3_host_login_valid(&bad,501));
    bad=good;bad.security_return=-1;assert(!fx3_host_login_valid(&bad,501));
    bad=good;bad.audit_session=0;assert(!fx3_host_login_valid(&bad,501));
    bad=good;bad.audit_session=(uint32_t)-1;assert(!fx3_host_login_valid(&bad,501));
    bad=good;bad.security_session++;assert(!fx3_host_login_valid(&bad,501));
    bad=good;bad.attributes&=~sessionHasGraphicAccess;assert(!fx3_host_login_valid(&bad,501));
    bad=good;bad.attributes&=~sessionHasTTY;assert(!fx3_host_login_valid(&bad,501));
    bad=good;bad.attributes|=sessionIsRemote;assert(!fx3_host_login_valid(&bad,501));
    puts("{\"state\":\"PASS_PURE_LOGIN_ADMISSION_FAULT_CASES\",\"checks\":15,\"self_or_root_identity_probed\":false,\"camera_operations\":0}");
    return 0;
}
