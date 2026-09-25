; SPDX-License-Identifier: GPL-2.0-or-later
; Short-idle control with no media replacement or break input.
; The separate mediaidle fixture checks the accepted unknown-media policy.
bits 16
cpu 8086
org 100h
%include "macros.inc"
start:
        push cs
        pop ds
        push cs
        pop es
        mov dx, file_name
        xor cx, cx
        mov ah, 3ch
        DOS 17001
        CARRY_CLEAR
        mov [handle], ax
        OK
        mov bx, ax
        mov cx, 4
        mov dx, payload
        mov ah, 40h
        DOS 17002
        EQUAL_AX 4
        mov bx, [handle]
        mov ah, 68h
        DOS 17003
        SUCCESS
        mov bx, [handle]
        mov ax, 4400h
        DOS 17004
        SUCCESS
        call save_report
        mov ah, 2ch
        int 21h
        mov [second], dh
        mov word [outer], 256
        xor bp, bp
.wait:
        mov ah, 2ch
        int 21h
        sub dh, [second]
        jnc .elapsed
        add dh, 60
.elapsed:
        cmp dh, 8
        jae .ready
        dec bp
        jnz .wait
        dec word [outer]
        jnz .wait
        jmp failure
.ready:
        mov bx, [handle]
        mov ax, 4400h
        DOS 17005
        SUCCESS
        mov bx, [handle]
        xor cx, cx
        xor dx, dx
        mov ax, 4200h
        DOS 17006
        EQUAL_AX 0
        mov bx, [handle]
        mov cx, 4
        mov dx, buffer
        mov ah, 3fh
        DOS 17007
        EQUAL_AX 4
        cmp word [buffer], 'LI'
        jne failure
        cmp word [buffer+2], 'VE'
        jne failure
        mov bx, [handle]
        mov ah, 3eh
        DOS 17008
        SUCCESS
        jmp passed
handle: dw 0
second: db 0
outer: dw 0
payload: db 'LIVE'
buffer: times 4 db 0
file_name: db 'IDLEFILE.DAT',0
result_name: db 'IDLEFILE.RES',0
%include "harness.inc"
