; SPDX-License-Identifier: GPL-2.0-or-later
; Original bounded nested EXEC and process/resource lifetime conformance.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%define M15_FAILURE_HOOK save_chain
%define M15_CHAIN_NAME 'PROCESS.MCB'
%macro EXEC_CHILD 1
        mov dx, child_name
        mov bx, exec_block
        mov ax, 4b00h
        DOS %1
%endmacro
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        mov bx, 1000h
        mov ah, 4ah
        DOS 10001
        SUCCESS
        mov ah, 62h
        DOS 10002
        mov [psp], bx
        mov ax, cs
        cmp ax, bx
        jne failure
        mov [exec_block+4], ax
        mov [exec_block+8], ax
        mov [exec_block+12], ax
        OK
        mov ah, 52h
        DOS 10003
        mov es, [snapshot+20]
        mov ax, [es:bx-2]
        mov [arena_first], ax
        push cs
        pop es
        OK
        mov bx, 16
        mov ah, 48h
        DOS 10004
        CARRY_CLEAR
        mov [exec_block], ax
        mov es, ax
        xor di, di
        mov si, environment
        mov cx, environment_end-environment
        rep movsb
        push cs
        pop es
        OK
        mov dx, file_name
        xor cx, cx
        mov ah, 3ch
        DOS 10005
        EQUAL_AX 5
        mov bx, 5
        mov dx, payload
        mov cx, 6
        mov ah, 40h
        DOS 10006
        EQUAL_AX 6
        mov dx, nul_name
        mov ax, 3d82h
        DOS 10007
        EQUAL_AX 6
        mov ax, 3523h
        DOS 10008
        mov [vector23], bx
        mov ax, [snapshot+20]
        mov [vector23+2], ax
        OK
        mov ax, 3524h
        DOS 10009
        mov [vector24], bx
        mov ax, [snapshot+20]
        mov [vector24+2], ax
        OK
        mov bx, 0ffffh
        mov ah, 48h
        DOS 10010
        ERROR 8
        mov [largest], bx
        call walk_arena
        mov ax, [own_blocks]
        mov [base_owned], ax
        call save_chain
        call save_report
%assign cycle_case 10011
%rep 16
        mov bx, 5
        xor cx, cx
        xor dx, dx
        mov ax, 4200h
        DOS cycle_case
        EQUAL_AX 0
        EXEC_CHILD cycle_case+1
        SUCCESS
        mov ah, 4dh
        DOS cycle_case+2
        ; AH:AL are documented; CF is not a function error indicator.
        cmp ax, 2ah
        jne failure
        OK
        mov bx, 5
        xor cx, cx
        xor dx, dx
        mov ax, 4201h
        DOS cycle_case+3
        EQUAL_AX 2
        EQUAL_DX 0
        mov ax, 3523h
        DOS cycle_case+4
        cmp bx, [vector23]
        jne failure
        mov ax, [snapshot+20]
        cmp ax, [vector23+2]
        jne failure
        OK
        mov ax, 3524h
        DOS cycle_case+5
        cmp bx, [vector24]
        jne failure
        mov ax, [snapshot+20]
        cmp ax, [vector24+2]
        jne failure
        OK
        mov bx, 0ffffh
        mov ah, 48h
        DOS cycle_case+6
        ERROR 8
        cmp bx, [largest]
        jne failure
        call walk_arena
        mov ax, [own_blocks]
        cmp ax, [base_owned]
        jne failure
%assign cycle_case cycle_case+7
%endrep
        mov ah, 4dh
        DOS 10123
        ; The preceding child result was already read; repeat-read contents are undefined.
        OK
        call rewind
        mov byte [tail+1], 'L'
        EXEC_CHILD 10124
        SUCCESS
        mov ah, 4dh
        DOS 10125
        cmp ax, 0
        jne failure
        OK
        call rewind
        mov byte [tail+1], 'Z'
        EXEC_CHILD 10126
        SUCCESS
        mov ah, 4dh
        DOS 10127
        cmp ax, 0
        jne failure
        OK
        mov dx, missing
        mov bx, exec_block
        mov ax, 4b00h
        DOS 10128
        ERROR 2
        mov dx, empty_name
        xor cx, cx
        mov ah, 3ch
        DOS 10129
        CARRY_CLEAR
        mov [temporary], ax
        OK
        mov bx, ax
        mov ah, 3eh
        DOS 10130
        SUCCESS
        mov dx, empty_name
        mov bx, exec_block
        mov ax, 4b00h
        DOS 10131
        ERROR 11
        mov dx, child_name
        mov bx, exec_block
        mov ax, 4b02h
        DOS 10132
        ERROR 1
        mov bx, 0ffffh
        mov ah, 48h
        DOS 10133
        ERROR 8
        mov ah, 48h
        DOS 10134
        CARRY_CLEAR
        mov [allocations], ax
        mov word [allocation_count], 1
        OK
        ; The largest block is not the whole arena. Consume every remaining
        ; free extent so that even a small COM cannot use another hole.
        call exhaust_arena
        call walk_arena
        mov byte [tail+1], 'N'
        EXEC_CHILD 10135
        ERROR 8
        mov es, [allocations]
        mov ah, 49h
        DOS 10136
        SUCCESS
        mov si, 1
.free_rest:
        cmp si, [allocation_count]
        jae .freed
        mov bx, si
        shl bx, 1
        mov es, [allocations+bx]
        mov ah, 49h
        int 21h
        jc failure
        inc si
        jmp .free_rest
.freed:
        push cs
        pop es
        mov bx, 0ffffh
        mov ah, 48h
        DOS 10137
        ERROR 8
        cmp bx, [largest]
        jne failure
        call walk_arena
        mov bx, 5
        mov ah, 3eh
        DOS 10138
        SUCCESS
        mov bx, 6
        mov ah, 3eh
        DOS 10139
        SUCCESS
        mov es, [exec_block]
        mov ah, 49h
        DOS 10140
        SUCCESS
        mov ah, 62h
        DOS 10141
        cmp bx, [psp]
        jne failure
        OK
        call walk_arena
        ; EXEC initializes the child's DTA. The termination contract restores
        ; the parent PSP and vectors, not an arbitrary parent's DTA pointer.
        ; Explicitly restore our buffer before any further DTA-based operation.
        mov dx, 80h
        mov ah, 1ah
        DOS 10142
        OK
        mov ah, 2fh
        DOS 10143
        cmp bx, 80h
        jne failure
        mov ax, [snapshot+20]
        cmp ax, [psp]
        jne failure
        OK
        mov dx, mz_name
        mov bx, exec_block
        mov word [exec_block], 0
        mov ax, 4b00h
        DOS 10144
        SUCCESS
        mov ah, 4dh
        DOS 10145
        cmp ax, 19
        jne failure
        OK
        call save_chain
        jmp passed
exhaust_arena:
        mov bx, 0ffffh
        mov ah, 48h
        int 21h
        jnc failure
        cmp ax, 8
        jne failure
        or bx, bx
        jz .done
        cmp word [allocation_count], 32
        jae failure
        mov ah, 48h
        int 21h
        jc failure
        mov di, [allocation_count]
        shl di, 1
        mov [allocations+di], ax
        inc word [allocation_count]
        jmp exhaust_arena
.done:
        ret
rewind:
        mov bx, 5
        xor cx, cx
        xor dx, dx
        mov ax, 4200h
        int 21h
        jc failure
        ret
largest: dw 0
temporary: dw 0
vector23: dd 0
vector24: dd 0
file_name: db 'PROC.DAT',0
nul_name: db 'NUL',0
missing: db 'ABSENT.COM',0
empty_name: db 'EMPTY.EXE',0
child_name: db 'PROCCH.COM',0
mz_name: db 'MZPROBE.EXE',0
allocation_count: dw 0
allocations: times 32 dw 0
payload: db 'abcdef'
environment: db 'M15VAR=VALUE',0,0
        dw 1
        db 'PROCESS.COM',0
environment_end:
tail: db 9,'N one two',13
fcb1: db 0,'FIRST   TXT'
        times 25 db 0
fcb2: db 0,'SECOND  BIN'
        times 25 db 0
exec_block: dw 0, tail, 0, fcb1, 0, fcb2, 0
        times 8 db 0
result_name: db 'PROCESS.RES',0
%include "arena.inc"
%include "harness.inc"
