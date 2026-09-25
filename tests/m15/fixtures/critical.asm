; SPDX-License-Identifier: GPL-2.0-or-later
; Real CON critical-error retry/fail/abort, with no DOS logging in callbacks.
; Historical context: DOS 5 Programmer's Reference INT24, functions 3F/44/4B/4D/59; FreeDOS baseline governs.
; Frontend sequence: F1, R, F1, K, F1. F1 is outside the ASCII CON profile.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%define M15_FAILURE_HOOK restore_state
%define M15_CHAIN_NAME 'CRITICAL.MCB'
start:
        push cs
        pop ds
        push cs
        pop es
        mov ax, 3300h
        int 21h
        mov [original_break], dl
        xor dx, dx
        mov ax, 3301h
        int 21h
        mov bx, 1000h
        mov ah, 4ah
        DOS 18001
        SUCCESS
        mov ah, 62h
        DOS 18002
        mov [psp], bx
        mov ax, cs
        cmp ax, bx
        jne failure
        mov [exec_block+4], ax
        mov [exec_block+8], ax
        mov [exec_block+12], ax
        OK
        mov ah, 52h
        DOS 18003
        mov es, [snapshot+20]
        mov ax, [es:bx-2]
        mov [arena_first], ax
        push cs
        pop es
        OK
        mov ax, 3524h
        DOS 18004
        mov [vector24], bx
        mov ax, [snapshot+20]
        mov [vector24+2], ax
        mov byte [vector_saved], 1
        OK
        mov dx, handler
        mov ax, 2524h
        DOS 18005
        OK
        xor bx, bx
        mov ax, 4400h
        DOS 18006
        CARRY_CLEAR
        xor dh, dh
        mov [input_mode], dx
        OK
        or dl, 20h
        mov ax, 4401h
        DOS 18007
        SUCCESS
        mov byte [mode_changed], 1
        call save_report
        mov byte [response], 1
        xor bx, bx
        mov dx, buffer
        mov cx, 1
        mov ah, 3fh
        DOS 18008
        EQUAL_AX 1
        cmp byte [buffer], 'R'
        jne failure
        cmp word [buffer_guard], 0a55ah
        jne failure
        cmp word [critical_count], 1
        jne failure
        cmp word [bad_response], 0
        jne failure
        mov ax, [critical_records]
        and ah, 91h
        cmp ah, 90h
        jne failure
        mov byte [response], 3
        mov byte [buffer], 0cch
        xor bx, bx
        mov dx, buffer
        mov cx, 1
        mov ah, 3fh
        DOS 18009
        ERROR 5
        cmp byte [buffer], 0cch
        jne failure
        cmp word [buffer_guard], 0a55ah
        jne failure
        cmp word [critical_count], 2
        jne failure
        cmp word [bad_response], 0
        jne failure
        xor bx, bx
        mov ax, 5900h
        DOS 18010
        cmp ax, 21
        jne failure
        cmp bh, 2
        jne failure
        cmp bl, 7
        jne failure
        cmp ch, 4
        jne failure
        OK
        xor bx, bx
        mov dx, buffer
        mov cx, 1
        mov ah, 3fh
        DOS 18011
        EQUAL_AX 1
        cmp byte [buffer], 'K'
        jne failure
        mov dx, [input_mode]
        mov ax, 4401h
        DOS 18012
        SUCCESS
        mov byte [mode_changed], 0
        mov ax, 3524h
        DOS 18013
        call check_handler
        OK
        mov bx, 0ffffh
        mov ah, 48h
        DOS 18014
        ERROR 8
        mov [largest], bx
        call walk_arena
        call save_chain
        call save_report
        mov byte [mode_changed], 1
        mov dx, child_name
        mov bx, exec_block
        mov ax, 4b00h
        DOS 18015
        SUCCESS
        mov ah, 4dh
        DOS 18016
        cmp ah, 2
        jne failure
        OK
        ; The child changed the shared CON mode. Restore the original mode
        ; explicitly; DOS termination restores handles, not shared modes.
        xor bx, bx
        mov dx, [input_mode]
        mov ax, 4401h
        DOS 18017
        SUCCESS
        mov byte [mode_changed], 0
        mov ax, 3524h
        DOS 18018
        call check_handler
        OK
        mov bx, 0ffffh
        mov ah, 48h
        DOS 18019
        ERROR 8
        cmp bx, [largest]
        jne failure
        call walk_arena
        call save_chain
        mov dx, 80h
        mov ah, 1ah
        DOS 18020
        OK
        mov dx, [vector24]
        mov ds, [vector24+2]
        mov ax, 2524h
        DOS 18021
        OK
        mov ax, 3524h
        DOS 18022
        cmp bx, [vector24]
        jne failure
        mov ax, [snapshot+20]
        cmp ax, [vector24+2]
        jne failure
        OK
        xor bx, bx
        mov ax, 4400h
        DOS 18023
        CARRY_CLEAR
        and dx, 00ffh
        cmp dx, [input_mode]
        jne failure
        OK
        mov dl, [original_break]
        mov ax, 3301h
        int 21h
        jmp passed
handler:
        push bx
        mov bx, [cs:critical_count]
        cmp bx, 2
        jae .bad
        shl bx, 1
        shl bx, 1
        shl bx, 1
        mov [cs:critical_records+bx], ax
        mov [cs:critical_records+bx+2], di
        mov [cs:critical_records+bx+4], bp
        mov [cs:critical_records+bx+6], si
        inc word [cs:critical_count]
        mov al, [cs:response]
        cmp al, 1
        jne .fail
        test ah, 10h
        jz .bad
        jmp short .done
.fail:
        test ah, 08h
        jnz .done
.bad:
        mov word [cs:bad_response], 1
        mov al, 2
.done:
        pop bx
        iret
check_handler:
        cmp bx, handler
        jne failure
        mov ax, [snapshot+20]
        mov dx, cs
        cmp ax, dx
        jne failure
        ret
restore_state:
        push cs
        pop ds
        mov dl, [original_break]
        mov ax, 3301h
        int 21h
        cmp byte [mode_changed], 0
        je .vector
        xor bx, bx
        mov dx, [input_mode]
        mov ax, 4401h
        int 21h
.vector:
        cmp byte [vector_saved], 0
        je .done
        mov dx, [vector24]
        mov ds, [vector24+2]
        mov ax, 2524h
        int 21h
.done:
        push cs
        pop ds
        push cs
        pop es
        ret
vector24: dd 0
vector_saved: db 0
mode_changed: db 0
input_mode: dw 0
original_break: db 0
response: db 0
critical_count: dw 0
bad_response: dw 0
critical_records: times 16 db 0
buffer: db 0cch
buffer_guard: dw 0a55ah
largest: dw 0
exec_block: dw 0,tail,0,fcb,0,fcb,0
tail: db 0,13
fcb: db 0,'           '
        times 4 db 0
child_name: db 'CRITKID.COM',0
result_name: db 'CRITICAL.RES',0
%include "harness.inc"
%include "arena.inc"
