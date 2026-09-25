; SPDX-License-Identifier: GPL-2.0-or-later
; Redirected character APIs, echo, line bounds, flush and parent-handle recovery.
; Historical context: Microsoft MS-DOS Programmer's Reference (1991), functions 01h-0Ch; preserve FreeDOS behavior.
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
        xor bx, bx
        mov ah, 45h
        DOS 12001
        CARRY_CLEAR
        mov [saved_input], ax
        OK
        mov bx, 1
        mov ah, 45h
        DOS 12002
        CARRY_CLEAR
        mov [saved_output], ax
        OK
        mov dx, input_name
        xor cx, cx
        mov ah, 3ch
        DOS 12003
        CARRY_CLEAR
        mov [temporary], ax
        OK
        mov bx, ax
        mov dx, input_data
        mov cx, input_end-input_data
        mov ah, 40h
        DOS 12004
        EQUAL_AX input_end-input_data
        mov bx, [temporary]
        mov ah, 3eh
        DOS 12005
        SUCCESS
        mov dx, output_name
        xor cx, cx
        mov ah, 3ch
        DOS 12006
        CARRY_CLEAR
        mov [temporary], ax
        OK
        mov bx, ax
        mov cx, 1
        mov ah, 46h
        DOS 12007
        SUCCESS
        mov bx, [temporary]
        mov ah, 3eh
        DOS 12008
        SUCCESS
        mov dx, input_name
        mov ax, 3d00h
        DOS 12009
        CARRY_CLEAR
        mov [temporary], ax
        OK
        mov bx, ax
        xor cx, cx
        mov ah, 46h
        DOS 12010
        SUCCESS
        mov bx, [temporary]
        mov ah, 3eh
        DOS 12011
        SUCCESS
        mov ah, 0bh
        DOS 12012
        EQUAL_AL 0ffh
        mov ah, 01h
        DOS 12013
        EQUAL_AL 'a'
        mov ah, 07h
        DOS 12014
        EQUAL_AL 'B'
        mov ah, 08h
        DOS 12015
        EQUAL_AL 'c'
        mov dl, '!'
        mov ah, 02h
        DOS 12016
        OK
        mov dl, '?'
        mov ah, 06h
        DOS 12017
        OK
        mov dx, string_data
        mov ah, 09h
        DOS 12018
        OK
        mov dl, 0ffh
        mov ah, 06h
        DOS 12019
        jz failure
        EQUAL_AL 'd'
        mov dx, line
        mov ah, 0ah
        DOS 12020
        cmp byte [line+1], 4
        jne failure
        cmp word [line+2], 'LI'
        jne failure
        cmp word [line+4], 'NE'
        jne failure
        cmp byte [line+6], 13
        jne failure
        cmp byte [line+7], 0cch
        jne failure
        OK
        ; Flushing console typeahead must not discard redirected file bytes.
        mov ax, 0c07h
        DOS 12021
        EQUAL_AL 'X'
        ; Function 0Ah requires a maximum buffer length from 1 through 255.
        mov dx, bounded_line
        mov ah, 0ah
        DOS 12023
        cmp byte [bounded_line+1], 3
        jne failure
        cmp word [bounded_line+2], 'AB'
        jne failure
        cmp word [bounded_line+4], 0d43h
        jne failure
        cmp word [bounded_line+6], 05aa5h
        jne failure
        OK
        xor bx, bx
        mov dx, buffer
        mov cx, 64
        mov ah, 3fh
        DOS 12024
        EQUAL_AX 0
        mov bx, [saved_input]
        xor cx, cx
        mov ah, 46h
        DOS 12025
        SUCCESS
        mov bx, [saved_output]
        mov cx, 1
        mov ah, 46h
        DOS 12026
        SUCCESS
        mov bx, [saved_input]
        mov ah, 3eh
        DOS 12027
        SUCCESS
        mov bx, [saved_output]
        mov ah, 3eh
        DOS 12028
        SUCCESS
        mov dx, output_name
        mov ax, 3d00h
        DOS 12029
        CARRY_CLEAR
        mov [temporary], ax
        OK
        mov bx, ax
        mov dx, buffer
        mov cx, 64
        mov ah, 3fh
        DOS 12030
        EQUAL_AX output_end-output_data
        mov si, output_data
        mov di, buffer
        mov cx, output_end-output_data
        repe cmpsb
        jne failure
        mov bx, [temporary]
        mov ah, 3eh
        DOS 12031
        SUCCESS
        xor bx, bx
        mov ax, 4400h
        DOS 12032
        CARRY_CLEAR
        test dx, 80h
        jz failure
        OK
        mov bx, 1
        mov ax, 4400h
        DOS 12033
        CARRY_CLEAR
        test dx, 80h
        jz failure
        cmp word [buffer_guard], 0a55ah
        jne failure
        cmp word [line_guard], 0a55ah
        jne failure
        OK
        jmp passed
saved_input: dw 0
saved_output: dw 0
temporary: dw 0
input_name: db 'CHARIN.DAT',0
output_name: db 'CHAROUT.DAT',0
input_data: db 'aBcdLINE',13,'XABCDE',13
input_end:
string_data: db 'TEXT$not printed'
output_data: db 'a!?TEXTLINE',13,'ABC',7,7,13
output_end:
line: db 8,0
        times 8 db 0cch
line_guard: dw 0a55ah
bounded_line: db 4,0
        times 4 db 0cch
        dw 05aa5h
buffer: times 64 db 0cch
buffer_guard: dw 0a55ah
result_name: db 'CONSOLE.RES',0
%include "harness.inc"
