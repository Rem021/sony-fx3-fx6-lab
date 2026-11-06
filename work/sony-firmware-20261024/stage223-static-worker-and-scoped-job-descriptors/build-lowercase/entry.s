.section .text
.global _start
.type _start,%function
_start:
    bl fx3_boot_read_window
    mov x8, #93
    svc #0
    b .
.size _start, .-_start
.section .note.GNU-stack,"",%progbits
