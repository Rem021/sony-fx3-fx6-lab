.section .text
.global _start
.type _start,%function
_start:
    mov x0, #53
    mov x1, #5001
    mov x2, #321
    mov x3, #777
    bl fx3_proc_anchor_observer
    mov x8, #93
    svc #0
    b .
.size _start, .-_start
.section .note.GNU-stack,"",%progbits
