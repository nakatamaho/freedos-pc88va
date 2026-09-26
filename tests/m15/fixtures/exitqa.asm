; SPDX-License-Identifier: GPL-2.0-or-later
; Return the single decimal command-tail parameter as a DOS exit status.
bits 16
cpu 8086
org 100h
start:
        push cs
        pop ds
        mov cl, [80h]
        xor ch, ch
        jcxz invalid
        mov si, 81h
.space:
        lodsb
        cmp al, ' '
        jne .digit
        loop .space
        jmp invalid
.digit:
        sub al, '0'
        cmp al, 9
        ja invalid
        mov ah, 4ch
        int 21h
invalid:
        mov ax, 4cffh
        int 21h
