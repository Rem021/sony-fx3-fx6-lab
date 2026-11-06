.text
.p2align 2
.globl _ccmp_eq
; w0=actual, w1=capacity, w2=flag. Return 1 iff b.eq would be taken.
_ccmp_eq:
    cmp w0, w1
    ccmp w2, #1, #0, gt
    b.eq 1f
    mov w0, #0
    ret
1:
    mov w0, #1
    ret
