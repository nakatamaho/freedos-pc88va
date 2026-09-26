; SPDX-License-Identifier: GPL-2.0-or-later
; Historical context: DOS 5 reference: INT 27h, INT 21h/31h, 4Dh and vector restoration; preserve FreeDOS behavior.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%define M15_FAILURE_HOOK restore_vector
%define M15_CHAIN_NAME 'RESIDENT.MCB'
%macro VECTOR_MATCH 3
        mov ax, 3500h+%2
        DOS %1
        cmp bx, [%3]
        jne failure
        mov ax, [snapshot+20]
        cmp ax, [%3+2]
        jne failure
        OK
%endmacro
start:
        push cs
        pop ds
        push cs
        pop es
        mov bx, 1000h
        mov ah, 4ah
        DOS 15001
        SUCCESS
        mov ah, 62h
        DOS 15002
        mov [psp], bx
        mov ax, cs
        cmp ax, bx
        jne failure
        mov [exec_block+4], ax
        mov [exec_block+8], ax
        mov [exec_block+12], ax
        OK
        mov ah, 52h
        DOS 15003
        mov es, [snapshot+20]
        mov ax, [es:bx-2]
        mov [arena_first], ax
        push cs
        pop es
        OK
        mov ax, 3560h
        DOS 15004
        mov [vector60], bx
        mov ax, [snapshot+20]
        mov [vector60+2], ax
        mov byte [vector_saved], 1
        OK
        mov ax, 3523h
        DOS 15005
        mov [vector23], bx
        mov ax, [snapshot+20]
        mov [vector23+2], ax
        OK
        mov ax, 3524h
        DOS 15006
        mov [vector24], bx
        mov ax, [snapshot+20]
        mov [vector24+2], ax
        OK
        mov bx, 0ffffh
        mov ah, 48h
        DOS 15007
        ERROR 8
        call walk_arena
        call save_chain
        mov dx, child_name
        mov bx, exec_block
        mov ax, 4b00h
        DOS 15008
        SUCCESS
        mov ah, 4dh
        DOS 15009
        cmp ax, 032ah
        jne failure
        OK
        mov ax, 3560h
        DOS 15010
        mov ax, [snapshot+20]
        mov [resident1], ax
        cmp ax, [psp]
        je failure
        int 60h
        cmp ax, 6011h
        jne failure
        OK
        VECTOR_MATCH 15011, 23h, vector23
        VECTOR_MATCH 15012, 24h, vector24
        mov bx, 0ffffh
        mov ah, 48h
        DOS 15013
        ERROR 8
        call walk_arena
        call save_chain
        mov byte [tail+2], '2'
        mov dx, child_name
        mov bx, exec_block
        mov ax, 4b00h
        DOS 15014
        SUCCESS
        mov ah, 4dh
        DOS 15015
        ; Function 4Dh reports AH=03h, AL=00h after INT 27h.
        cmp ax, 0300h
        jne failure
        OK
        mov ax, 3560h
        DOS 15016
        mov ax, [snapshot+20]
        mov [resident2], ax
        cmp ax, [psp]
        je failure
        cmp ax, [resident1]
        je failure
        int 60h
        cmp ax, 6022h
        jne failure
        OK
        VECTOR_MATCH 15017, 23h, vector23
        VECTOR_MATCH 15018, 24h, vector24
        mov bx, 0ffffh
        mov ah, 48h
        DOS 15019
        ERROR 8
        call walk_arena
        call save_chain
        mov dx, [vector60]
        mov ds, [vector60+2]
        mov ax, 2560h
        DOS 15020
        OK
        VECTOR_MATCH 15021, 60h, vector60
        mov bx, 0ffffh
        mov ah, 48h
        DOS 15022
        ERROR 8
        call walk_arena
        call save_chain
        mov ah, 62h
        DOS 15023
        cmp bx, [psp]
        jne failure
        OK
        mov bx, 1
        mov ah, 45h
        DOS 15024
        CARRY_CLEAR
        mov [duplicate], ax
        OK
        mov bx, [duplicate]
        mov ah, 3eh
        DOS 15025
        SUCCESS
        mov dx, 80h
        mov ah, 1ah
        DOS 15026
        OK
        jmp passed
restore_vector:
        cmp byte [vector_saved], 0
        je .done
        mov dx, [vector60]
        mov ds, [vector60+2]
        mov ax, 2560h
        int 21h
.done:
        push cs
        pop ds
        push cs
        pop es
        ret
vector_saved: db 0
vector60: dd 0
vector23: dd 0
vector24: dd 0
resident1: dw 0
resident2: dw 0
duplicate: dw 0
exec_block: dw 0,tail,0,fcb,0,fcb,0
tail: db 2,' 1',13
fcb: db 0,'           '
        times 4 db 0
child_name: db 'RESCHILD.COM',0
result_name: db 'RESIDENT.RES',0
%include "harness.inc"
%include "arena.inc"
