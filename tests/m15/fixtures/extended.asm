; SPDX-License-Identifier: GPL-2.0-or-later
; Historical context: Microsoft MS-DOS Programmer's Reference (1991), functions 59h, 5Ah, 6Ch; FreeDOS baseline remains authoritative.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%macro OPENEX 5
        mov si, %2
        mov bx, %3
        mov cx, %4
        mov dx, %5
        mov ax, 6c00h
        DOS %1
%endmacro
%macro KEEP 1
        CARRY_CLEAR
        cmp cx, %1
        jne failure
        mov [handle], ax
        OK
%endmacro
%macro CLOSE 1
        mov bx, [handle]
        mov ah, 3eh
        DOS %1
        SUCCESS
%endmacro
%macro EXTERR 2
        xor bx, bx
        mov ax, 5900h
        DOS %1
        EQUAL_AX %2
        ; The taxonomy is documented; an implementation may recommend a
        ; different valid recovery action for the same underlying error.
        cmp bh, 1
        jb failure
        cmp bh, 13
        ja failure
        cmp bl, 1
        jb failure
        cmp bl, 7
        ja failure
        cmp ch, 1
        jb failure
        cmp ch, 5
        ja failure
        OK
%endmacro
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        OPENEX 11001, missing, 0, 0, 1
        ERROR 2
        EXTERR 11002, 2
        OPENEX 11003, file_name, 2, 2, 10h
        KEEP 2
        mov bx, [handle]
        mov dx, payload
        mov cx, 14
        mov ah, 40h
        DOS 11004
        EQUAL_AX 14
        mov bx, [handle]
        mov ah, 68h
        DOS 11005
        SUCCESS
        CLOSE 11006
        OPENEX 11007, file_name, 0, 1, 1
        KEEP 1
        mov bx, [handle]
        mov dx, buffer
        mov cx, 16
        mov ah, 3fh
        DOS 11008
        EQUAL_AX 14
        mov si, payload
        mov di, buffer
        mov cx, 14
        repe cmpsb
        jne failure
        mov bx, [handle]
        mov dx, payload
        mov cx, 1
        mov ah, 40h
        DOS 11009
        ERROR 5
        EXTERR 11010, 5
        CLOSE 11011
        mov dx, file_name
        mov ax, 4300h
        DOS 11012
        CARRY_CLEAR
        and cx, 1fh
        cmp cx, 2                 ; Opening did not apply its readonly attribute.
        jne failure
        OK
        ; Replacing a hidden file requires matching its hidden attribute.
        ; Microsoft DOS 4 CREATE/MakeNode checks MatchAttributes here;
        ; the ignored-attribute rule applies to opening without replacement.
        OPENEX 11013, file_name, 2, 2, 2
        KEEP 3
        mov bx, [handle]
        xor cx, cx
        xor dx, dx
        mov ax, 4202h
        DOS 11014
        EQUAL_AX 0
        EQUAL_DX 0
        mov bx, [handle]
        mov cx, 4
        mov dx, payload
        mov ah, 40h
        DOS 11015
        EQUAL_AX 4
        CLOSE 11016
        OPENEX 11017, file_name, 2, 0, 11h
        KEEP 1
        mov bx, [handle]
        mov cx, 16
        mov dx, buffer
        mov ah, 3fh
        DOS 11018
        EQUAL_AX 4
        cmp word [buffer], 'ex'
        jne failure
        cmp word [buffer+2], 'te'
        jne failure
        CLOSE 11019
        OPENEX 11020, file_name, 2, 2, 12h
        KEEP 3
        CLOSE 11021
        OPENEX 11022, new_open, 2, 0, 11h
        KEEP 2
        CLOSE 11023
        OPENEX 11024, new_truncate, 2, 0, 12h
        KEEP 2
        CLOSE 11025
        OPENEX 11026, missing, 2, 0, 3
        ERROR 1
        OPENEX 11027, missing, 2, 0, 20h
        ERROR 1
        OPENEX 11028, bad_path, 2, 0, 10h
        ERROR 3
        EXTERR 11029, 3
        mov dx, temp1
        mov cx, 2
        mov ah, 5ah
        DOS 11030
        CARRY_CLEAR
        mov [handle], ax
        mov si, temp1
        call check_temp_name
        OK
        mov bx, [handle]
        mov dx, payload
        mov cx, 14
        mov ah, 40h
        DOS 11031
        EQUAL_AX 14
        CLOSE 11032
        mov dx, temp2
        xor cx, cx
        mov ah, 5ah
        DOS 11033
        CARRY_CLEAR
        mov [handle], ax
        mov si, temp2
        call check_temp_name
        mov si, temp1
        mov di, temp2
        mov cx, 16
        repe cmpsb
        je failure
        OK
        CLOSE 11034
        mov dx, temp1
        mov ax, 3d00h
        DOS 11035
        CARRY_CLEAR
        mov [handle], ax
        OK
        mov bx, ax
        mov cx, 16
        mov dx, buffer
        mov ah, 3fh
        DOS 11036
        EQUAL_AX 14
        mov si, payload
        mov di, buffer
        mov cx, 14
        repe cmpsb
        jne failure
        CLOSE 11037
        mov dx, temp1
        mov ah, 41h
        DOS 11038
        SUCCESS
        mov dx, temp2
        mov ah, 41h
        DOS 11039
        SUCCESS
        mov dx, bad_temp
        xor cx, cx
        mov ah, 5ah
        DOS 11040
        ERROR 3
        EXTERR 11041, 3
        mov bx, 0ffffh
        mov ah, 68h
        DOS 11042
        ERROR 6
        EXTERR 11043, 6
        OPENEX 11044, file_name, 2, 0, 2
        ERROR 5
        EXTERR 11045, 5
        OPENEX 11046, file_name, 2, 2, 2
        KEEP 3
        CLOSE 11047
        cmp word [buffer_guard], 0a55ah
        jne failure
        cmp word [temp1_guard], 05aa5h
        jne failure
        cmp word [temp2_guard], 05aa5h
        jne failure
        cmp word [bad_guard], 05aa5h
        jne failure
        jmp passed
check_temp_name:
        cmp word [si], 'A:'
        jne failure
        cmp byte [si+2], 5ch
        jne failure
        add si, 3
        mov cx, 13
.scan:
        lodsb
        or al, al
        jz .found
        loop .scan
        jmp failure
.found:
        cmp cx, 13
        je failure
        ret
handle: dw 0
file_name: db 'EXT.DAT',0
new_open: db 'NEW11.DAT',0
new_truncate: db 'NEW12.DAT',0
missing: db 'NOEXT.DAT',0
bad_path: db 'MISSING\EXT.DAT',0
payload: db 'extended data',13
buffer: times 16 db 0cch
buffer_guard: dw 0a55ah
temp1: db 'A:\',0
        times 13 db 0cch
temp1_guard: dw 05aa5h
temp2: db 'A:\',0
        times 13 db 0cch
temp2_guard: dw 05aa5h
bad_temp: db 'A:\MISSING\',0
        times 13 db 0cch
bad_guard: dw 05aa5h
result_name: db 'EXTENDED.RES',0
%include "harness.inc"
