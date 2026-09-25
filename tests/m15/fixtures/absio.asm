; SPDX-License-Identifier: GPL-2.0-or-later
; Original DOS absolute-read ABI fixture; invalid-drive writes cannot mutate.
; The legacy interface leaves one FLAGS word; the packet uses a far buffer.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%define M15_ABSOLUTE_IO 1
%macro ABS 2
        mov byte [cs:absolute_interrupt], %1
        DOS %2
        mov byte [cs:absolute_interrupt], 0
%endmacro
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        mov ax, cs
        mov [packet+8], ax
        mov ax, 3000h
        DOS 8001
        OK
        call save_report
        mov ax, 00ffh
        mov bx, buffer_a
        mov cx, 1
        xor dx, dx
        ABS 25h, 8002
        ERROR 0201h
        call check_stack
        mov ax, 00ffh
        mov bx, buffer_a
        mov cx, 1
        xor dx, dx
        ABS 26h, 8003
        ERROR 0201h
        call check_stack
        xor ax, ax
        mov bx, buffer_a
        mov cx, 1
        xor dx, dx
        ABS 25h, 8004
        SUCCESS
        call check_stack
        ; The public supported FAT12 BPB defines logical-sector units.
        cmp word [buffer_a+11], 1024
        jne failure
        cmp byte [buffer_a+13], 1
        jne failure
        cmp word [buffer_a+14], 1
        jne failure
        cmp byte [buffer_a+16], 2
        jne failure
        cmp word [buffer_a+19], 1280
        jne failure
        xor ax, ax
        mov bx, packet
        mov cx, 0ffffh
        ABS 25h, 8005
        SUCCESS
        call check_stack
        mov si, buffer_a
        mov di, buffer_b
        mov cx, 1024
        repe cmpsb
        jne failure
        xor ax, ax
        mov bx, buffer_b
        mov cx, 1
        mov dx, 1279
        ABS 25h, 8006
        SUCCESS
        call check_stack
        xor ax, ax
        mov bx, buffer_b
        mov cx, 1
        mov dx, 1280
        ABS 25h, 8007
        jnc failure
        or ax, ax
        jz failure
        OK
        call check_stack
        cmp word [buffer_a-2], 0a55ah
        jne failure
        cmp word [buffer_a+1024], 05aa5h
        jne failure
        cmp word [buffer_b-2], 0a55ah
        jne failure
        cmp word [buffer_b+1024], 05aa5h
        jne failure
        jmp passed
check_stack:
        mov ax, [absolute_sp]
        add ax, 2
        cmp ax, [call_sp]
        jne failure
        ret
packet: dd 0
        dw 1, buffer_b, 0
        dw 0a55ah
buffer_a: times 1024 db 0cch
        dw 05aa5h, 0a55ah
buffer_b: times 1024 db 033h
        dw 05aa5h
result_name: db 'ABSIO.RES',0
%include "harness.inc"
