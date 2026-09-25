; SPDX-License-Identifier: GPL-2.0-or-later
; DOS CON/NUL/file distinctions and IOCTL state and rejection behavior.
; MS-DOS references are background only; preserve the selected FreeDOS results.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%macro IOCTL 2
        mov bx, [handle]
        mov ax, 4400h | %1
        DOS %2
%endmacro
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        mov dx, nul_name
        mov ax, 3d02h
        DOS 9001
        CARRY_CLEAR
        mov [handle], ax
        OK
        IOCTL 0, 9002
        SUCCESS
        test dl, 80h
        jne failure
        OK
        mov bx, [handle]
        mov dx, buffer
        mov cx, 64
        mov ah, 3fh
        DOS 9003
        EQUAL_AX 0
        cmp byte [buffer], 0cch
        jne failure
        mov bx, [handle]
        mov dx, text
        mov cx, text_end-text
        mov ah, 40h
        DOS 9004
        EQUAL_AX text_end-text
        IOCTL 7, 9005
        CARRY_CLEAR
        EQUAL_AL 0ffh
        IOCTL 6, 9006
        CARRY_CLEAR
        EQUAL_AL 0ffh
        mov dx, buffer
        mov cx, 4
        IOCTL 2, 9007
        ERROR 1
        IOCTL 3, 9008
        ERROR 1
        mov cx, 0ffffh
        IOCTL 0ch, 9009
        ERROR_ANY
        mov cx, 0345h
        IOCTL 10h, 9010
        ERROR 1
        mov bx, [handle]
        mov ah, 3eh
        DOS 9011
        SUCCESS
        mov dx, con_name
        mov ax, 3d02h
        DOS 9012
        CARRY_CLEAR
        mov [handle], ax
        OK
        IOCTL 0, 9013
        CARRY_CLEAR
        test dl, 80h
        jz failure
        mov [old_mode], dl
        OK
        xor dh, dh
        or dl, 20h
        IOCTL 1, 9014
        SUCCESS
        IOCTL 0, 9015
        CARRY_CLEAR
        test dl, 20h
        jz failure
        OK
        xor dh, dh
        and dl, 0dfh
        IOCTL 1, 9016
        SUCCESS
        IOCTL 0, 9017
        CARRY_CLEAR
        test dl, 20h
        jnz failure
        OK
        xor dh, dh
        mov dl, [old_mode]
        IOCTL 1, 9018
        SUCCESS
        mov dh, 1
        IOCTL 1, 9019
        ; Record the FreeDOS error code; only the failure result is required.
        ERROR_ANY
        IOCTL 0, 9020
        CARRY_CLEAR
        cmp dl, [old_mode]
        jne failure
        OK
        mov bx, [handle]
        mov ah, 3eh
        DOS 9021
        SUCCESS
        mov dx, file_name
        mov ax, 3d00h
        DOS 9022
        CARRY_CLEAR
        mov [handle], ax
        OK
        IOCTL 0, 9023
        CARRY_CLEAR
        test dl, 80h
        jnz failure
        test dx, 0ff80h
        jnz failure
        OK
        IOCTL 6, 9024
        CARRY_CLEAR
        EQUAL_AL 0ffh
        IOCTL 7, 9025
        CARRY_CLEAR
        ; Both documented values mean ready for an ordinary output file.
        cmp al, 0
        je .file_ready
        cmp al, 0ffh
        jne failure
.file_ready:
        OK
        xor dx, dx
        IOCTL 1, 9026
        ERROR 1
        mov bx, [handle]
        mov dx, buffer
        mov cx, 64
        mov ah, 3fh
        DOS 9027
        EQUAL_AX text_end-text
        mov si, text
        mov di, buffer
        mov cx, text_end-text
        repe cmpsb
        jne failure
        IOCTL 6, 9028
        CARRY_CLEAR
        EQUAL_AL 0
        mov bx, [handle]
        mov ah, 3eh
        DOS 9029
        SUCCESS
        mov bx, 1
        mov ax, 4408h
        DOS 9030
        EQUAL_AX 0
        mov bx, 1
        mov ax, 4409h
        DOS 9031
        ; DOS 4 requires file-sharing support for this query.
        ; Keep the provider-unavailable result explicit but continue collecting
        ; independent local-device cases; this out-of-profile row remains FAIL.
        ERROR_CONTINUE 1
        mov bx, 1
        mov ax, 440eh
        DOS 9032
        CARRY_CLEAR
        EQUAL_AL 0
        mov bx, 1
        mov ax, 440fh
        DOS 9033
        CARRY_CLEAR
        EQUAL_AL 0
        ; Invalid handles are rejected before touching request buffers.
%assign bad_case 9034
%rep 8
%if bad_case == 9034
%assign subfunc 0
%elif bad_case == 9035
%assign subfunc 1
%elif bad_case == 9036
%assign subfunc 2
%elif bad_case == 9037
%assign subfunc 3
%elif bad_case == 9038
%assign subfunc 6
%elif bad_case == 9039
%assign subfunc 7
%elif bad_case == 9040
%assign subfunc 0ah
%elif bad_case == 9041
%assign subfunc 0ch
%endif
        mov bx, 0ffffh
        mov ax, 4400h | subfunc
        mov dx, buffer
        mov cx, 1
        DOS bad_case
        ERROR 6
%assign bad_case bad_case+1
%endrep
        mov ax, 4412h
        DOS 9043
        ERROR 1
        mov bx, 26
        mov ax, 4408h
        DOS 9044
        ERROR 15
        mov bx, 26
        mov ax, 4409h
        DOS 9045
        ERROR 15
        mov bx, 1
        mov ax, 440ah
        DOS 9047
        ; The handle is valid, but the required network provider is absent.
        ; Retain any provider mismatch while finishing the guarded observations.
        ERROR_CONTINUE 1
        cmp word [buffer-2], 0a55ah
        jne failure
        cmp word [buffer+64], 05aa5h
        jne failure
        ; first_failure intentionally remains set for an unchecked provider
        ; mismatch. This fixture must therefore bypass `passed`.
        jmp finish
handle: dw 0
old_mode: db 0
nul_name: db 'NUL',0
con_name: db 'CON',0
file_name: db 'TYPEA.TXT',0
text: db 'M13-TYPE-A!',13,10
text_end:
        dw 0a55ah
buffer: times 64 db 0cch
        dw 05aa5h
result_name: db 'DEVICE.RES',0
%include "harness.inc"
