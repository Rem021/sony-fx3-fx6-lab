/* Compiled against sealed264's reader; it must reject the recovery extension. */
#include "global_guard.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(int argc,char **argv){
    assert(argc==2 && geteuid()!=0);uint8_t nonce[16];memset(nonce,'Z',16);
    fx3_global_guard g={.fd=-1};int rc=fx3_global_begin(&g,argv[1],(uint32_t)getuid(),nonce,"legacy-unapproved-next");
    assert(rc==G_INVALID);printf("legacy reader rejects v2:%d\n",rc);return 0;
}
