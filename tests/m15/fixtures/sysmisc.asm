; SPDX-License-Identifier: GPL-2.0-or-later
; Allocation/DPB queries, caller-owned BPB translation and reversible state.
; DOS allocation fields are checked against the public FAT12 fixture geometry.
; FreeDOS 33FC changes the default for new PSPs, not the actual kernel version.
; See FreeDOS VERSION discussion (2004-06-24/25) and DOS 5 PSP version field.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%define M15_FAILURE_HOOK restore_state
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        mov dl, 1
        mov ah, 36h
        DOS 22001
        cmp ax, 1
        jne failure
        cmp cx, 1024
        jne failure
        cmp dx, 1269
        jne failure
        OK
        mov ah, 1bh
        DOS 22002
        call check_allocation
        OK
        mov dl, 1
        mov ah, 1ch
        DOS 22003
        call check_allocation
        OK
        mov dl, 26
        mov ah, 1ch
        DOS 22004
        EQUAL_AL 0ffh
        mov ah, 1fh
        DOS 22005
        EQUAL_AL 0
        mov [dpb_ptr], bx
        mov ax, [snapshot+18]
        mov [dpb_ptr+2], ax
        mov es, ax
        cmp word [es:bx+2], 1024
        jne failure
        cmp byte [es:bx], 0
        jne failure
        push cs
        pop es
        mov dl, 1
        mov ah, 32h
        DOS 22006
        EQUAL_AL 0
        cmp bx, [dpb_ptr]
        jne failure
        mov ax, [snapshot+18]
        cmp ax, [dpb_ptr+2]
        jne failure
        mov dl, 26
        mov ah, 32h
        DOS 22007
        EQUAL_AL 0ffh
        mov si, bpb
        mov bp, translated
        mov ah, 53h
        DOS 22008
        cmp word [translated+2], 1024
        jne failure
        cmp word [translated+4], 0
        jne failure
        cmp word [translated+6], 1
        jne failure
        cmp byte [translated+8], 2
        jne failure
        cmp word [translated+9], 192
        jne failure
        cmp word [translated+11], 11
        jne failure
        cmp word [translated+13], 1270
        jne failure
        cmp word [translated+15], 2
        jne failure
        cmp word [translated+17], 5
        jne failure
        cmp byte [translated+23], 0feh
        jne failure
        cmp byte [translated+24], 0
        jne failure
        cmp word [translated-2], 0a55ah
        jne failure
        cmp word [translated+40], 05aa5h
        jne failure
        OK
        mov bx, 1000h
        mov ah, 4ah
        DOS 22022
        SUCCESS
        mov bx, 16
        mov ah, 48h
        DOS 22023
        CARRY_CLEAR
        mov [copy_psp], ax
        OK
        mov dx, ax
        mov ah, 26h
        DOS 22024
        mov es, [copy_psp]
        ; Function 26 copies the PSP, adjusts its memory-end segment, and
        ; refreshes vector fields. This fixture has not changed those vectors.
        mov ax, [copy_psp]
        add ax, 16
        cmp ax, [es:6]
        jne failure
        xor si, si
        xor di, di
        mov cx, 3
        repe cmpsw
        jne failure
        add si, 2                 ; Offset 06h is adjusted, not copied.
        add di, 2
        mov cx, 124
        repe cmpsw
        jne failure
        mov ax, [es:40h]
        mov [old_default], ax
        push cs
        pop es
        OK
        mov ax, 3000h
        DOS 22009
        mov [old_version], ax
        OK
        mov ax, 3306h
        DOS 22010
        mov [actual_version], bx
        OK
        mov bx, 0505h
        mov ax, 33fch
        DOS 22011
        mov byte [version_changed], 1
        OK
        mov dx, [copy_psp]
        mov ah, 26h
        DOS 22025
        mov es, [copy_psp]
        cmp word [es:40h], 0505h
        jne failure
        push cs
        pop es
        OK
        mov bx, [copy_psp]
        mov ah, 50h
        DOS 22026
        OK
        mov ax, 3000h
        DOS 22027
        cmp ax, 0505h
        jne failure
        OK
        mov bx, cs
        mov ah, 50h
        DOS 22028
        OK
        mov ax, 3000h
        DOS 22012
        cmp ax, [old_version]
        jne failure
        OK
        mov ax, 3306h
        DOS 22013
        cmp bx, [actual_version]
        jne failure
        OK
        mov bx, [old_default]
        mov ax, 33fch
        DOS 22014
        mov byte [version_changed], 0
        OK
        mov ax, 3000h
        DOS 22015
        cmp ax, [old_version]
        jne failure
        OK
        mov dx, [copy_psp]
        mov ah, 26h
        DOS 22029
        mov es, [copy_psp]
        mov ax, [es:40h]
        cmp ax, [old_default]
        jne failure
        push cs
        pop es
        OK
        mov es, [copy_psp]
        mov ah, 49h
        DOS 22030
        SUCCESS
        mov word [copy_psp], 0
        mov dx, old_name
        mov ax, 5e00h
        DOS 22016
        CARRY_CLEAR
        mov [old_number], cx
        cmp word [old_name+16], 0a55ah
        jne failure
        OK
        mov dx, new_name
        mov cx, 0123h
        mov ax, 5e01h
        DOS 22017
        SUCCESS
        mov byte [name_changed], 1
        mov dx, name_buffer
        mov ax, 5e00h
        DOS 22018
        CARRY_CLEAR
        cmp cx, 0123h
        jne failure
        mov si, new_name
        mov di, name_buffer
        mov cx, 16
        repe cmpsb
        jne failure
        cmp word [name_buffer+16], 05aa5h
        jne failure
        OK
        mov dx, old_name
        mov cx, [old_number]
        mov ax, 5e01h
        DOS 22019
        SUCCESS
        mov byte [name_changed], 0
        mov dx, name_buffer
        mov ax, 5e00h
        DOS 22020
        CARRY_CLEAR
        cmp cx, [old_number]
        jne failure
        mov si, old_name
        mov di, name_buffer
        mov cx, 16
        repe cmpsb
        jne failure
        OK
        mov ah, 0dh
        DOS 22021
        OK
        jmp passed
check_allocation:
        cmp al, 1
        jne failure
        cmp cx, 1024
        jne failure
        cmp dx, 1269
        jne failure
        mov es, [snapshot+18]
        cmp byte [es:bx], 0feh
        jne failure
        push cs
        pop es
        ret
restore_state:
        push cs
        pop ds
        mov bx, cs
        mov ah, 50h
        int 21h
        cmp word [copy_psp], 0
        je .version
        mov es, [copy_psp]
        mov ah, 49h
        int 21h
        mov word [copy_psp], 0
.version:
        cmp byte [version_changed], 0
        je .name
        mov bx, [old_default]
        mov ax, 33fch
        int 21h
.name:
        cmp byte [name_changed], 0
        je .done
        mov dx, old_name
        mov cx, [old_number]
        mov ax, 5e01h
        int 21h
.done:
        push cs
        pop es
        ret
dpb_ptr: dd 0
old_version: dw 0
old_default: dw 0
copy_psp: dw 0
actual_version: dw 0
version_changed: db 0
old_number: dw 0
name_changed: db 0
old_name: times 16 db 0cch
        dw 0a55ah
new_name: db 'M15LOCAL',0,0,0,0,0,0,0,0
name_buffer: times 16 db 0cch
        dw 05aa5h
bpb: dw 1024
        db 1
        dw 1
        db 2
        dw 192,1280
        db 0feh
        dw 2,8,2
        dd 0,0
        dw 0a55ah
translated: times 40 db 0cch
        dw 05aa5h
result_name: db 'SYSMISC.RES',0
%include "harness.inc"
