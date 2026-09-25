; SPDX-License-Identifier: GPL-2.0-or-later
; Allocation/resize/strategy and complete arena lifetime snapshots.
; Historical context: memory API material in the MS-DOS Encyclopedia; the project
; follows the selected FreeDOS allocator and preserves mapped native ownership.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%define M15_FAILURE_HOOK save_chain
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        ; The inherited COM stack is below 64 KiB, including the PSP.
        mov bx, 1000h
        mov ah, 4ah
        DOS 6001
        SUCCESS
        mov ah, 62h
        DOS 6002
        mov ax, cs
        cmp bx, ax
        jne failure
        mov [psp], bx
        OK
        mov ah, 52h
        DOS 6003
        mov es, [snapshot+20]
        mov ax, [es:bx-2]
        mov [arena_first], ax
        push cs
        pop es
        OK
        mov ax, 5800h
        DOS 6004
        CARRY_CLEAR
        cmp ax, 2
        ja failure
        mov [old_strategy], ax
        OK
        mov ax, 5801h
        xor bx, bx
        DOS 6005
        SUCCESS
        mov ax, 5800h
        DOS 6061
        EQUAL_AX 0
        mov bx, 0ffffh
        mov ah, 48h
        DOS 6006
        ERROR 8
        or bx, bx
        jz failure
        mov [largest], bx
        call walk_arena
        mov ax, [own_blocks]
        mov [base_owned], ax
        call save_chain
        mov bx, 16
        mov ah, 48h
        DOS 6007
        CARRY_CLEAR
        mov [block_a], ax
        call check_new_block
        OK
        call walk_arena
        mov ax, [own_blocks]
        sub ax, [base_owned]
        cmp ax, 1
        jne failure
        mov bx, 16
        mov ah, 48h
        DOS 6008
        CARRY_CLEAR
        mov [block_b], ax
        call check_new_block
        mov ax, [block_a]
        add ax, 17
        cmp ax, [block_b]
        jne failure
        OK
        call walk_arena
        mov es, [block_a]
        mov bx, 32
        mov ah, 4ah
        DOS 6009
        ERROR 8
        cmp bx, 16
        jne failure
        mov ax, [block_a]
        call check_new_block
        call walk_arena
        mov es, [block_b]
        mov ah, 49h
        DOS 6010
        SUCCESS
        call walk_arena
        mov es, [block_a]
        mov bx, 0ffffh
        mov ah, 4ah
        DOS 6011
        ERROR 8
        cmp bx, 16
        jbe failure
        ; DOS expands to the available adjoining extent even on this failure.
        mov ax, [block_a]
        dec ax
        mov es, ax
        cmp [es:3], bx
        jne failure
        mov ax, [psp]
        cmp [es:1], ax
        jne failure
        push cs
        pop es
        call walk_arena
        mov es, [block_a]
        mov bx, 16
        mov ah, 4ah
        DOS 6012
        SUCCESS
        mov ax, [block_a]
        call check_new_block
        call walk_arena
        mov es, [block_a]
        mov ah, 49h
        DOS 6013
        SUCCESS
        call walk_arena
        call check_owned
        mov bx, 0ffffh
        mov ah, 48h
        DOS 6014
        ERROR 8
        cmp bx, [largest]
        jne failure
        mov ax, 5801h
        mov bx, 1
        DOS 6015
        SUCCESS
        mov ax, 5800h
        DOS 6062
        EQUAL_AX 1
        mov bx, 16
        mov ah, 48h
        DOS 6016
        CARRY_CLEAR
        mov [block_a], ax
        call check_new_block
        OK
        call walk_arena
        mov es, [block_a]
        mov ah, 49h
        DOS 6017
        SUCCESS
        call walk_arena
        call check_owned
        mov ax, 5801h
        mov bx, 2
        DOS 6018
        SUCCESS
        mov bx, 16
        mov ah, 48h
        DOS 6019
        CARRY_CLEAR
        mov [block_a], ax
        call check_new_block
        OK
        call walk_arena
        mov es, [block_a]
        mov ah, 49h
        DOS 6020
        SUCCESS
        call walk_arena
        call check_owned
        mov ax, 5800h
        DOS 6022
        EQUAL_AX 2
        mov ax, 5802h
        DOS 6023
        CARRY_CLEAR
        EQUAL_AL 0
        mov ax, 5803h
        mov bx, 1
        DOS 6024
        ERROR 1
        mov ax, 5801h
        xor bx, bx
        DOS 6025
        SUCCESS
%assign cycle_case 6026
%rep 16
        mov bx, 16
        mov ah, 48h
        DOS cycle_case
        CARRY_CLEAR
        mov [block_a], ax
        call check_new_block
        OK
        call walk_arena
        mov es, [block_a]
        mov di, 0
        mov ax, 0a55ah
        mov cx, 128
        rep stosw
        xor di, di
        mov cx, 128
        repe scasw
        jne failure
        mov es, [block_a]
        mov ah, 49h
        DOS cycle_case+1
        SUCCESS
        call walk_arena
        call check_owned
%assign cycle_case cycle_case+2
%endrep
        mov ax, 5801h
        mov bx, [old_strategy]
        DOS 6058
        SUCCESS
        mov bx, 0ffffh
        mov ah, 48h
        DOS 6059
        ERROR 8
        cmp bx, [largest]
        jne failure
        call walk_arena
        call check_owned
        mov ah, 62h
        DOS 6060
        cmp bx, [psp]
        jne failure
        OK
        call save_chain
        jmp passed
check_owned:
        mov ax, [own_blocks]
        cmp ax, [base_owned]
        jne failure
        ret
check_new_block:
        dec ax
        mov es, ax
        cmp word [es:3], 16
        jne arena_failure
        mov ax, [psp]
        cmp [es:1], ax
        jne arena_failure
        push cs
        pop es
        ret
old_strategy: dw 0
largest: dw 0
block_a: dw 0
block_b: dw 0
result_name: db 'MEMORY.RES',0
%include "arena.inc"
%include "harness.inc"
