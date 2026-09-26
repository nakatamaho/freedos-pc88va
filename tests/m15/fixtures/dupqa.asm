; SPDX-License-Identifier: GPL-2.0-or-later
; Historical context: Microsoft MS-DOS Encyclopedia, System Calls 45H and 46H; preserve FreeDOS behavior.
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
        mov dx, nul_name
        mov ax, 3d00h
        DOS 1060
        jc failure
        mov [h1], ax
        OK
        mov bx, [h1]
        mov ah, 45h
        DOS 1061
        jc failure
        mov [h2], ax
        OK
        mov bx, [h1]
        mov ah, 3eh
        DOS 1062
        SUCCESS
        mov bx, [h2]
        mov ah, 3fh
        mov cx, 1
        mov dx, buffer
        DOS 1063
        EQUAL_AX 0
        mov dx, nul_name
        mov ax, 3d00h
        DOS 1064
        jc failure
        mov [h3], ax
        OK
        mov bx, [h2]
        mov cx, [h3]
        mov ah, 46h
        DOS 1065
        SUCCESS
        mov bx, [h3]
        mov ah, 3fh
        mov cx, 1
        mov dx, buffer
        DOS 1066
        EQUAL_AX 0
        mov bx, [h2]
        mov ah, 3eh
        DOS 1067
        SUCCESS
        mov bx, [h3]
        mov ah, 3eh
        DOS 1068
        SUCCESS
        mov bx, 0ffffh
        mov ah, 45h
        DOS 1069
        ERROR 6
        mov bx, 0ffffh
        mov cx, 0ffffh
        mov ah, 46h
        DOS 1070
        ERROR 6
%assign duplicate_case 1071
%rep 15
        mov bx, 1
        mov ah, 45h
        DOS duplicate_case
        jc failure
        mov di, duplicate_case-1071
        shl di, 1
        mov [duplicate_handles+di], ax
        OK
%assign duplicate_case duplicate_case+1
%endrep
        mov bx, 1
        mov ah, 45h
        DOS 1086
        ERROR 4
        mov si, duplicate_handles
        mov cx, 15
.close_duplicates:
        push cx
        mov bx, [si]
        mov ah, 3eh
        int 21h
        pop cx
        jc failure
        add si, 2
        loop .close_duplicates
        jmp passed
h1: dw 0
h2: dw 0
h3: dw 0
duplicate_handles: times 15 dw 0
nul_name: db 'NUL',0
buffer: db 0
result_name: db 'DUPQA.RES',0
%include "harness.inc"
