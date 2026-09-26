; SPDX-License-Identifier: GPL-2.0-or-later
; Historical context: Microsoft MS-DOS Encyclopedia, System Calls 3C-46, 57, 5A/5B,
; and the accepted local FreeDOS extensions. Assertions check ordinary port
; behavior and guest state. Each invocation records the actual ABI result.
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
        mov dx, missing
        mov ax, 3d00h
        DOS 1001
        ERROR 2
        mov dx, file_name
        xor cx, cx
        mov ah, 3ch
        DOS 1002
        jc failure
        mov [h1], ax
        OK
        mov bx, [h1]
        mov cx, 8
        mov dx, payload
        mov ah, 40h
        DOS 1003
        EQUAL_AX 8
        mov bx, [h1]
        mov ax, 4201h
        xor cx, cx
        xor dx, dx
        DOS 1004
        EQUAL_AX 8
        EQUAL_DX 0
        mov bx, [h1]
        mov ah, 45h
        DOS 1005
        jc failure
        mov [h2], ax
        OK
        mov bx, [h2]
        mov ax, 4200h
        xor cx, cx
        mov dx, 2
        DOS 1006
        EQUAL_AX 2
        mov bx, [h1]
        mov cx, 2
        mov dx, buffer
        mov ah, 3fh
        DOS 1007
        EQUAL_AX 2
        cmp word [buffer], 'CD'
        jne failure
        mov bx, [h2]
        mov ah, 3eh
        DOS 1008
        SUCCESS
        mov bx, [h1]
        mov cx, 2
        mov dx, buffer
        mov ah, 3fh
        DOS 1009
        EQUAL_AX 2
        cmp word [buffer], 'EF'
        jne failure
        mov dx, file_name
        mov ax, 3d00h
        DOS 1010
        jc failure
        mov [h3], ax
        OK
        mov bx, [h3]
        mov cx, 1
        mov dx, buffer
        mov ah, 3fh
        DOS 1011
        EQUAL_AX 1
        cmp byte [buffer], 'A'
        jne failure
        mov bx, [h1]
        mov ax, 4201h
        xor cx, cx
        xor dx, dx
        DOS 1012
        EQUAL_AX 6
        mov bx, [h3]
        mov dx, payload
        mov cx, 1
        mov ah, 40h
        DOS 1013
        ERROR 5
        mov bx, [h1]
        mov cx, [h3]
        mov ah, 46h
        DOS 1014
        SUCCESS
        mov bx, [h3]
        mov cx, 8
        mov dx, buffer
        mov ah, 3fh
        DOS 1015
        EQUAL_AX 2
        cmp word [buffer], 'GH'
        jne failure
        mov bx, [h1]
        mov cx, 8
        mov dx, buffer
        mov ah, 3fh
        DOS 1016
        EQUAL_AX 0
        mov bx, [h3]
        mov ah, 3eh
        DOS 1017
        SUCCESS
        mov bx, [h1]
        mov ax, 4200h
        xor cx, cx
        mov dx, 4
        DOS 1018
        EQUAL_AX 4
        mov bx, [h1]
        xor cx, cx
        mov dx, payload
        mov ah, 40h
        DOS 1019
        EQUAL_AX 0
        mov bx, [h1]
        mov ax, 4202h
        xor cx, cx
        xor dx, dx
        DOS 1020
        EQUAL_AX 4
        mov bx, [h1]
        mov ah, 68h
        DOS 1021
        SUCCESS
        mov bx, [h1]
        mov ah, 6ah
        DOS 1022
        SUCCESS
        mov bx, [h1]
        mov ax, 5701h
        mov cx, (12<<11)|(34<<5)|28
        mov dx, ((2024-1980)<<9)|(2<<5)|29
        DOS 1023
        SUCCESS
        mov bx, [h1]
        mov ax, 5700h
        DOS 1024
        CARRY_CLEAR
        EQUAL_CX (12<<11)|(34<<5)|28
        EQUAL_DX ((2024-1980)<<9)|(2<<5)|29
        OK
        mov bx, [h1]
        mov ah, 3eh
        DOS 1025
        SUCCESS
        mov bx, [h1]
        mov ah, 3eh
        DOS 1026
        ERROR 6
        mov dx, file_name
        mov ax, 4301h
        mov cx, 1
        DOS 1027
        SUCCESS
        mov dx, file_name
        mov ax, 4300h
        DOS 1028
        CARRY_CLEAR
        test cx, 1
        jz failure
        OK
        mov dx, file_name
        mov ax, 3d02h
        DOS 1029
        ERROR 5
        mov dx, file_name
        mov ah, 41h
        DOS 1030
        ERROR 5
        mov dx, file_name
        mov ax, 4301h
        xor cx, cx
        DOS 1031
        SUCCESS
        mov dx, file_name
        mov ax, 3d03h
        DOS 1032
        ERROR 12
        mov dx, file_name
        mov ax, 3d01h
        DOS 1033
        jc failure
        mov [h1], ax
        OK
        mov bx, [h1]
        mov ah, 3fh
        mov cx, 1
        mov dx, buffer
        DOS 1034
        ERROR 5
        mov bx, [h1]
        mov ah, 3eh
        DOS 1035
        SUCCESS
        mov dx, file_name
        mov ah, 5bh
        xor cx, cx
        DOS 1036
        ERROR 80
        mov dx, second_name
        mov ah, 5bh
        xor cx, cx
        DOS 1037
        jc failure
        mov [h1], ax
        OK
        mov bx, [h1]
        mov ah, 3eh
        DOS 1038
        SUCCESS
        mov dx, second_name
        mov ah, 41h
        DOS 1039
        SUCCESS
        mov bx, 0ffffh
        mov ah, 3fh
        mov cx, 1
        mov dx, buffer
        DOS 1040
        ERROR 6
        mov bx, 0ffffh
        mov ah, 40h
        mov cx, 1
        mov dx, payload
        DOS 1041
        ERROR 6
        mov bx, 0ffffh
        mov ah, 45h
        DOS 1042
        ERROR 6
        mov bx, 0ffffh
        mov ah, 68h
        DOS 1043
        ERROR 6
        mov dx, file_name
        mov ax, 3d00h
        DOS 1044
        jc failure
        mov [h1], ax
        OK
        mov bx, [h1]
        mov ax, 4202h
        mov cx, 0ffffh
        mov dx, 0fffeh
        DOS 1045
        EQUAL_AX 2
        EQUAL_DX 0
        mov bx, [h1]
        mov ax, 4203h
        xor cx, cx
        xor dx, dx
        DOS 1046
        ERROR 1
        mov bx, [h1]
        mov cx, 4
        mov dx, buffer
        mov ah, 3fh
        DOS 1047
        EQUAL_AX 2
        cmp word [buffer], 'CD'
        jne failure
        cmp word [buffer-2], 0a55ah
        jne failure
        cmp word [buffer+16], 05aa5h
        jne failure
        mov bx, [h1]
        mov ah, 3eh
        DOS 1048
        SUCCESS
        mov dx, file_name
        xor cx, cx
        mov ah, 3ch
        DOS 1049
        jc failure
        mov [h1], ax
        OK
        mov bx, [h1]
        mov cx, 1
        mov dx, buffer
        mov ah, 3fh
        DOS 1050
        EQUAL_AX 0
        mov bx, 0ffffh
        mov cx, 0ffffh
        mov ah, 46h
        DOS 1053
        ERROR 6
        mov bx, [h1]
        mov ah, 3eh
        DOS 1051
        SUCCESS
        mov dx, missing_path
        xor cx, cx
        mov ah, 3ch
        DOS 1052
        ERROR 3
        jmp passed
h1: dw 0
h2: dw 0
h3: dw 0
file_name: db 'HND.DAT',0
second_name: db 'SECOND.DAT',0
missing: db 'NOFILE.XYZ',0
missing_path: db 'M15NODIR\CREATE.DAT',0
payload: db 'ABCDEFGH'
        dw 0a55ah
buffer: times 16 db 0cch
        dw 05aa5h
result_name: db 'HANDLES.RES',0
%include "harness.inc"
