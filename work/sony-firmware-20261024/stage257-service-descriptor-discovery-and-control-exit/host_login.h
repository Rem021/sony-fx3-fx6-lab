#ifndef FX3_HOST_LOGIN_H
#define FX3_HOST_LOGIN_H
#include <Security/AuthSession.h>
#include <stdint.h>

typedef struct {
    int auid_return, audit_return;
    OSStatus security_return;
    uint32_t audit_uid, audit_record_uid, audit_session;
    SecuritySessionId security_session;
    SessionAttributeBits attributes;
} fx3_host_login;

void fx3_host_login_read(fx3_host_login *value);
int fx3_host_login_valid(const fx3_host_login *value,uint32_t console_uid);
void fx3_host_login_print_json(const fx3_host_login *value);
#endif
