/* AArch64 ELF startup contract: pass loader fini and initial argc/argv to
   pinned guest __libc_start_main. This helper has no constructors/destructors. */
.text
.global _start
.type _start,%function
_start:
 mov x29, #0
 mov x30, #0
 mov x5, x0
 ldr x1, [sp]
 add x2, sp, #8
 mov x6, sp
 adrp x0, main
 add x0, x0, :lo12:main
 adrp x3, helper_init
 add x3, x3, :lo12:helper_init
 mov x4, x3
 bl __libc_start_main
 brk #0
.type helper_init,%function
helper_init:
 ret
.section .note.GNU-stack,"",%progbits
