; SPDX-License-Identifier: GPL-2.0-or-later
; Historical context: Microsoft MS-DOS Encyclopedia, System Call 41H; preserve FreeDOS behavior.
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
        mov dx, file_name
        xor cx, cx
        mov ah, 3ch
        DOS 1090
        jc failure
        mov [handle], ax
        OK
        mov bx, [handle]
        mov ah, 3eh
        DOS 1091
        SUCCESS
        mov dx, file_name
        mov ah, 41h
        DOS 1092
        SUCCESS
        mov dx, file_name
        mov ah, 41h
        DOS 1093
        ERROR 2
        mov dx, missing_path
        mov ah, 41h
        DOS 1094
        ERROR 3
        jmp passed
handle: dw 0
file_name: db 'DELQA.TMP',0
missing_path: db 'M15NODIR\DELQA.TMP',0
result_name: db 'DELQA.RES',0
%include "harness.inc"
