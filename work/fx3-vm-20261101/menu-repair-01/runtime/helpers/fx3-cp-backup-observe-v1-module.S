.section .modinfo,"a"
.asciz "license=GPL"
.asciz "author=FX3 VM compatibility model"
.asciz "depends=osal_uipc"
.asciz "vermagic=4.9.337-scel+ SMP preempt mod_unload aarch64"
.section .gnu.linkonce.this_module,"aw"
.balign 64
.global __this_module
.type __this_module,%object
__this_module:
.zero 24
.asciz "fx3_cp_backup_observe_v1"
.zero 0x158-(.-__this_module)
.quad init_module
.zero 0x2b8-(.-__this_module)
.quad cleanup_module
.zero 0x300-(.-__this_module)
.size __this_module, .-__this_module
