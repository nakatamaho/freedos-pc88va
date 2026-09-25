; SPDX-License-Identifier: GPL-2.0-or-later
; Actual Ctrl-C, line editing, file break policy and child abort/recovery.
; Historical context: DOS 5 Programmer's Reference INT23 and functions 07/08/0A/33/3F; preserve FreeDOS behavior.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%define M15_FAILURE_HOOK restore_state
%define M15_CHAIN_NAME 'BREAK.MCB'
start:
        push cs
        pop ds
        push cs
        pop es
        mov bx, 1000h
        mov ah, 4ah
        DOS 16001
        SUCCESS
        mov ah, 62h
        DOS 16002
        mov [psp], bx
        mov ax, cs
        cmp ax, bx
        jne failure
        mov [exec_block+4], ax
        mov [exec_block+8], ax
        mov [exec_block+12], ax
        OK
        mov ah, 52h
        DOS 16003
        mov es, [snapshot+20]
        mov ax, [es:bx-2]
        mov [arena_first], ax
        push cs
        pop es
        OK
        mov ax, 3523h
        DOS 16004
        mov [vector23], bx
        mov ax, [snapshot+20]
        mov [vector23+2], ax
        mov byte [vector_saved], 1
        OK
        mov ax, 3300h
        DOS 16005
        mov [original_break], dl
        OK
        xor dx, dx
        mov ax, 3301h
        DOS 16006
        OK
        mov dx, handler
        mov ax, 2523h
        DOS 16007
        OK
        mov dx, file_name
        xor cx, cx
        mov ah, 3ch
        DOS 16008
        CARRY_CLEAR
        mov [handle], ax
        OK
        mov bx, ax
        mov dx, payload
        mov cx, 4
        mov ah, 40h
        DOS 16009
        EQUAL_AX 4
        mov bx, [handle]
        xor cx, cx
        xor dx, dx
        mov ax, 4200h
        DOS 16010
        EQUAL_AX 0
        call save_report
        mov bx, [handle]
        mov dx, buffer
        xor cx, cx
        mov ah, 3fh
        DOS 16036
        EQUAL_AX 0
        mov ah, 07h
        DOS 16011
        EQUAL_AL 3
        cmp word [break_count], 0
        jne failure
        mov ah, 08h
        DOS 16012
        EQUAL_AL 'k'
        cmp word [break_count], 1
        jne failure
        mov bx, [handle]
        mov dx, buffer
        xor cx, cx
        mov ah, 3fh
        DOS 16037
        EQUAL_AX 0
        mov ah, 01h
        DOS 16013
        EQUAL_AL 'm'
        cmp word [break_count], 2
        jne failure
        mov bx, [handle]
        mov dx, buffer
        xor cx, cx
        mov ah, 3fh
        DOS 16038
        EQUAL_AX 0
        mov dx, line
        mov ah, 0ah
        DOS 16014
        cmp byte [line+1], 2
        jne failure
        cmp word [line+2], 'AD'
        jne failure
        cmp byte [line+4], 13
        jne failure
        cmp word [line_guard], 0a55ah
        jne failure
        cmp word [break_count], 3
        jne failure
        OK
        mov bx, [handle]
        mov dx, buffer
        xor cx, cx
        mov ah, 3fh
        DOS 16039
        EQUAL_AX 0
        call save_report
        mov bx, [handle]
        mov dx, buffer
        xor cx, cx
        mov ah, 3fh
        DOS 16040
        EQUAL_AX 0
        mov ah, 07h
        DOS 16015
        EQUAL_AL 'a'
        call queue_wait
        mov bx, [handle]
        mov dx, buffer
        mov cx, 1
        mov ah, 3fh
        DOS 16016
        EQUAL_AX 1
        cmp byte [buffer], 'F'
        jne failure
        cmp word [break_count], 3
        jne failure
        mov ah, 07h
        DOS 16017
        EQUAL_AL 3
        mov ah, 07h
        DOS 16018
        EQUAL_AL 'b'
        call queue_wait
        mov dl, 1
        mov ax, 3301h
        DOS 16019
        OK
        mov bx, [handle]
        mov dx, buffer
        mov cx, 1
        mov ah, 3fh
        DOS 16020
        EQUAL_AX 1
        cmp byte [buffer], 'I'
        jne failure
        cmp word [break_count], 4
        jne failure
        cmp word [handler_functions], 0108h
        jne failure
        cmp word [handler_functions+2], 3f0ah
        jne failure
        xor dx, dx
        mov ax, 3301h
        DOS 16021
        OK
        mov bx, [handle]
        mov ah, 3eh
        DOS 16022
        SUCCESS
        xor bx, bx
        mov ax, 4400h
        DOS 16023
        CARRY_CLEAR
        xor dh, dh
        mov [input_mode], dx
        OK
        or dl, 20h
        mov ax, 4401h
        DOS 16024
        SUCCESS
        mov byte [mode_changed], 1
        mov bx, 0
        mov dx, buffer
        mov cx, 1
        mov ah, 3fh
        DOS 16025
        EQUAL_AX 1
        cmp byte [buffer], 3
        jne failure
        cmp word [break_count], 4
        jne failure
        mov dx, [input_mode]
        mov bx, 0
        mov ax, 4401h
        DOS 16026
        SUCCESS
        mov byte [mode_changed], 0
        mov dx, [vector23]
        mov ds, [vector23+2]
        mov ax, 2523h
        DOS 16027
        OK
        mov dl, [original_break]
        mov ax, 3301h
        DOS 16028
        OK
        mov ax, 3523h
        DOS 16029
        call check_vector
        OK
        mov bx, 0ffffh
        mov ah, 48h
        DOS 16030
        ERROR 8
        mov [largest], bx
        call walk_arena
        call save_chain
        call save_report
        mov dx, child_name
        mov bx, exec_block
        mov ax, 4b00h
        DOS 16031
        SUCCESS
        mov ah, 4dh
        DOS 16032
        cmp ah, 1
        jne failure
        OK
        mov ax, 3523h
        DOS 16033
        call check_vector
        OK
        mov bx, 0ffffh
        mov ah, 48h
        DOS 16034
        ERROR 8
        cmp bx, [largest]
        jne failure
        call walk_arena
        call save_chain
        mov dx, 80h
        mov ah, 1ah
        DOS 16035
        OK
        jmp passed
handler:
        push bx
        mov bx, [cs:break_count]
        cmp bx, 4
        jae .count
        mov [cs:handler_functions+bx], ah
.count:
        inc word [cs:break_count]
        pop bx
        iret
queue_wait:
        ; The VA keyboard is polled, not a firmware queue. Wait until the
        ; non-consuming IOCTL status has actually latched the Ctrl-C key.
        ; AH=0Bh checks break even with BREAK OFF and is unsuitable here.
        mov word [wait_high], 256
        xor bp, bp
.next:
        xor bx, bx
        mov ax, 4406h
        int 21h
        jc failure
        cmp al, 0ffh
        je .done
        dec bp
        jnz .next
        dec word [wait_high]
        jnz .next
        jmp failure
.done:
        ret
check_vector:
        cmp bx, [vector23]
        jne failure
        mov ax, [snapshot+20]
        cmp ax, [vector23+2]
        jne failure
        ret
restore_state:
        push cs
        pop ds
        ; A failed BREAK OFF case can leave Ctrl-C latched. Discard it before
        ; restoring the parent's break policy and writing the failure record.
        mov ax, 0c00h
        int 21h
        cmp byte [mode_changed], 0
        je .vector
        mov dx, [input_mode]
        xor bx, bx
        mov ax, 4401h
        int 21h
.vector:
        cmp byte [vector_saved], 0
        je .done
        mov dl, [original_break]
        mov ax, 3301h
        int 21h
        mov dx, [vector23]
        mov ds, [vector23+2]
        mov ax, 2523h
        int 21h
.done:
        push cs
        pop ds
        push cs
        pop es
        ret
vector_saved: db 0
vector23: dd 0
original_break: db 0
break_count: dw 0
handler_functions: times 4 db 0
input_mode: dw 0
mode_changed: db 0
handle: dw 0
largest: dw 0
wait_high: dw 0
buffer: db 0
line: db 8,0
        times 8 db 0cch
line_guard: dw 0a55ah
file_name: db 'BRKFILE.DAT',0
payload: db 'FILE'
exec_block: dw 0,tail,0,fcb,0,fcb,0
tail: db 0,13
fcb: db 0,'           '
        times 4 db 0
child_name: db 'BRKCHILD.COM',0
result_name: db 'BREAK.RES',0
%include "harness.inc"
%include "arena.inc"
