.section .text
.global _start
.type _start,%function
_start:
    mov x0, #0x72000000
    mov x1, #256
    bl fx3_bridge_start
    mov x8, #93
    svc #0
    b .
.size _start, .-_start
.section .note.GNU-stack,"",%progbits
