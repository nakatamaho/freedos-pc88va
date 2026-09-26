; SPDX-License-Identifier: GPL-2.0-or-later
; Actual CON input through ordinary frontend keyboard events.
; Supply klmLINE<Enter>, f without Enter, one Escape key, Z<Enter>, ABCDE<Enter>.
; Microsoft DOS 5 Programmer's Reference, functions 01/06-0C/44h.
bits 16
cpu 8086
org 100h
%include "macros.inc"
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        mov bx, 0
        mov ax, 4400h
        DOS 13001
        CARRY_CLEAR
        test dx, 80h
        jz failure
        OK
        mov ah, 0bh
        DOS 13002
        EQUAL_AL 0
        mov dl, 0ffh
        mov ah, 06h
        DOS 13003
        jnz failure
        OK
        mov bx, 0
        mov ax, 4406h
        DOS 13004
        EQUAL_AL 0
        mov ah, 07h
        DOS 13005
        EQUAL_AL 'k'
        mov ah, 08h
        DOS 13006
        EQUAL_AL 'l'
        mov ah, 01h
        DOS 13007
        EQUAL_AL 'm'
        mov dx, line
        mov ah, 0ah
        DOS 13008
        cmp byte [line+1], 4
        jne failure
        cmp word [line+2], 'LI'
        jne failure
        cmp word [line+4], 'NE'
        jne failure
        cmp byte [line+6], 13
        jne failure
        cmp word [line_guard], 0a55ah
        jne failure
        OK
        mov ah, 0bh
        DOS 13009
        EQUAL_AL 0
        mov ah, 07h
        DOS 13010
        EQUAL_AL 'f'
        ; Wait for one isolated key event without consuming it. A timed wait
        ; for a pasted string can race later characters still being typed;
        ; flushing promises to discard only input that has already arrived.
        mov word [wait_high], 256
        xor bp, bp
.wait:
        mov ah, 0bh
        int 21h
        cmp al, 0ffh
        je .queued
        dec bp
        jnz .wait
        dec word [wait_high]
        jnz .wait
        jmp failure
.queued:
        mov ah, 0bh
        DOS 13011
        EQUAL_AL 0ffh
        mov bx, 0
        mov ax, 4406h
        DOS 13012
        EQUAL_AL 0ffh
        mov ax, 0c00h
        DOS 13013
        OK
        mov ah, 0bh
        DOS 13014
        EQUAL_AL 0
        mov dl, 0ffh
        mov ah, 06h
        DOS 13015
        jnz failure
        OK
        mov ax, 0c07h
        DOS 13016
        EQUAL_AL 'Z'
        mov ah, 07h
        DOS 13017
        EQUAL_AL 13
        mov dx, bounded
        mov ah, 0ah
        DOS 13018
        cmp byte [bounded+1], 3
        jne failure
        cmp word [bounded+2], 'AB'
        jne failure
        cmp word [bounded+4], 0d43h
        jne failure
        cmp word [bounded_guard], 05aa5h
        jne failure
        OK
        mov ah, 0bh
        DOS 13019
        EQUAL_AL 0
        mov bx, 0
        mov ax, 4406h
        DOS 13020
        EQUAL_AL 0
        jmp passed
line: db 8,0
        times 8 db 0cch
line_guard: dw 0a55ah
bounded: db 4,0
        times 4 db 0cch
bounded_guard: dw 05aa5h
wait_high: dw 0
result_name: db 'CONKEY.RES',0
%include "harness.inc"
