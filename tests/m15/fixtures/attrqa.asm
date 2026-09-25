; SPDX-License-Identifier: GPL-2.0-or-later
; Historical context: Microsoft MS-DOS Encyclopedia, Section V, Function 43H; preserve FreeDOS behavior.
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
        mov dx, missing_file
        mov ax, 4300h
        DOS 1095
        ERROR 2
        mov dx, missing_path
        mov ax, 4300h
        DOS 1096
        ERROR 3
        mov dx, missing_file
        xor cx, cx
        mov ax, 4301h
        DOS 1097
        ERROR 2
        mov dx, missing_path
        xor cx, cx
        mov ax, 4301h
        DOS 1098
        ERROR 3
        mov dx, file_name
        mov ax, 4300h
        DOS 1099
        CARRY_CLEAR
        EQUAL_CX 20h
        OK
        mov dx, file_name
        mov cx, 20h
        mov ax, 4301h
        DOS 1100
        CARRY_CLEAR
        EQUAL_CX 20h
        OK
        mov dx, file_name
        mov ax, 4300h
        DOS 1101
        CARRY_CLEAR
        EQUAL_CX 20h
        OK
        jmp passed
missing_file: db 'M15ATR00.XYZ',0
missing_path: db 'M15NODIR\ATTRQA.DAT',0
file_name: db 'ATTRQA.COM',0
result_name: db 'ATTRQA.RES',0
%include "harness.inc"
