.section .text
.global _start
.type _start,%function
_start:
    bl fx3_isolated_collector_core
    cmp w0, #10
    mov w1, #42
    csel w0, w1, w0, eq
    mov x8, #93
    svc #0
    b .
.size _start, .-_start
.section .note.GNU-stack,"",%progbits
