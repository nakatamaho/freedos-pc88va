; SPDX-License-Identifier: GPL-2.0-or-later
; DOS input flush/read function/subfunction calls and the valid one-byte line-buffer boundary.
; Each queue wait observes one isolated Escape key through ordinary input.
bits 16
cpu 8086
org 100h
%include "macros.inc"
start:
        push cs
        pop ds
        push cs
        pop es
        call queued
        mov dl, 0ffh
        mov ax, 0c06h
        DOS 21001
        jnz failure
        OK
        mov ah, 0bh
        DOS 21002
        EQUAL_AL 0
        call queued
        mov ax, 0c01h
        DOS 21003
        EQUAL_AL 'A'
        mov ah, 0bh
        DOS 21004
        EQUAL_AL 0
        call queued
        mov ax, 0c08h
        DOS 21005
        EQUAL_AL 'B'
        mov ah, 0bh
        DOS 21006
        EQUAL_AL 0
        call queued
        mov dx, line
        mov ax, 0c0ah
        DOS 21007
        cmp byte [line+1], 2
        jne failure
        cmp word [line+2], 'CD'
        jne failure
        cmp byte [line+4], 13
        jne failure
        cmp word [line_guard], 0a55ah
        jne failure
        OK
        call queued
        mov dl, '!'
        mov ax, 0c06h
        DOS 21008
        OK
        mov ah, 0bh
        DOS 21009
        EQUAL_AL 0
        call queued
        mov ax, 0cffh
        DOS 21010
        OK
        mov ah, 0bh
        DOS 21011
        EQUAL_AL 0
        mov dx, one
        mov ah, 0ah
        DOS 21013
        cmp byte [one+1], 0
        jne failure
        cmp byte [one+2], 13
        jne failure
        cmp word [one_guard], 0a55ah
        jne failure
        OK
        mov ah, 0bh
        DOS 21014
        EQUAL_AL 0
        jmp passed
queued:
        mov word [outer], 256
        xor bp, bp
.next:
        xor bx, bx
        mov ax, 4406h
        int 21h
        jc failure
        cmp al, 0ffh
        je .done
        dec bp
        jnz .next
        dec word [outer]
        jnz .next
        jmp failure
.done:
        ret
outer: dw 0
line: db 6,0
        times 6 db 0cch
line_guard: dw 0a55ah
one: db 1,0,0cch
one_guard: dw 0a55ah
result_name: db 'CONFLUSH.RES',0
%include "harness.inc"
