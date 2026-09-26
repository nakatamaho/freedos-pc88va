; SPDX-License-Identifier: GPL-2.0-or-later
; Historical context: DOS 5 Programmer's Reference: 26h, 50h, 51h, 4B01h, 4B03h and LOAD; preserve FreeDOS behavior.
; Load-only children are inspected then explicitly closed/freed without entry.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%define M15_FAILURE_HOOK restore_parent
%define M15_CHAIN_NAME 'LOADMODE.MCB'
%macro LOADCASE 3
        mov dx, %2
        mov bx, load_block
        mov ax, 4b01h
        DOS %1
        SUCCESS
        mov ah, 62h
        DOS %1+1
        mov [child_psp], bx
        mov es, bx
        cmp word [es:0], 20cdh
        jne failure
        mov ax, [psp]
        cmp [es:16h], ax
        jne failure
        cmp byte [es:80h], 2
        jne failure
        cmp word [es:81h], ' 7'
        jne failure
        cmp byte [es:83h], 13
        jne failure
        mov ax, [es:2ch]
        or ax, ax
        jz failure
        mov [child_env], ax
        mov ax, bx
%if %3
        add ax, 10h
        cmp word [load_block+18], 0
        jne failure
%else
        cmp word [load_block+18], 100h
        jne failure
%endif
        cmp [load_block+20], ax
        jne failure
        cmp [load_block+16], ax
        jne failure
%if %3
        mov es, ax
        cmp [es:32], ax
        jne failure
%endif
        mov es, [load_block+16]
        mov bx, [load_block+14]
        cmp word [es:bx], 0       ; Valid default drives => initial AX zero.
        jne failure
        push cs
        pop es
        OK
        ; Loading cloned standard handles. Release those references while
        ; the child remains current; a bare memory free would leak SFT refs.
        mov word [close_index], 0
%%close:
        mov es, [child_psp]
        mov bx, [close_index]
        cmp byte [es:bx+18h], 0ffh
        je %%next
        mov ah, 3eh
        int 21h
        jc failure
%%next:
        inc word [close_index]
        cmp word [close_index], 20
        jb %%close
        push cs
        pop es
        mov bx, [psp]
        mov ah, 50h
        DOS %1+2
        OK
        mov ah, 51h
        DOS %1+3
        cmp bx, [psp]
        jne failure
        OK
        mov dx, 80h
        mov ah, 1ah
        DOS %1+4
        OK
        mov dx, [vector22]
        mov ds, [vector22+2]
        mov ax, 2522h
        DOS %1+5
        OK
        mov es, [child_env]
        mov ah, 49h
        DOS %1+6
        SUCCESS
        mov es, [child_psp]
        mov ah, 49h
        DOS %1+7
        SUCCESS
        mov bx, 0ffffh
        mov ah, 48h
        DOS %1+8
        ERROR 8
        cmp bx, [largest]
        jne failure
        call walk_arena
        call save_chain
%endmacro
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        mov bx, 1000h
        mov ah, 4ah
        DOS 14001
        SUCCESS
        mov ah, 62h
        DOS 14002
        mov [psp], bx
        mov ax, cs
        cmp ax, bx
        jne failure
        mov [load_block+4], ax
        mov [load_block+8], ax
        mov [load_block+12], ax
        OK
        mov ah, 52h
        DOS 14003
        mov es, [snapshot+20]
        mov ax, [es:bx-2]
        mov [arena_first], ax
        push cs
        pop es
        OK
        mov ax, 3522h
        DOS 14004
        mov [vector22], bx
        mov ax, [snapshot+20]
        mov [vector22+2], ax
        OK
        mov bx, 0ffffh
        mov ah, 48h
        DOS 14005
        ERROR 8
        mov [largest], bx
        call walk_arena
        call save_chain
        LOADCASE 14006, com_name, 0
        LOADCASE 14015, mz_name, 1
        mov bx, 16
        mov ah, 48h
        DOS 14024
        CARRY_CLEAR
        mov [copy_psp], ax
        OK
        mov dx, ax
        mov ah, 26h
        DOS 14025
        mov es, [copy_psp]
        cmp word [es:0], 20cdh
        jne failure
        mov ax, [vector22]
        cmp [es:0ah], ax
        jne failure
        mov ax, [vector22+2]
        cmp [es:0ch], ax
        jne failure
        push cs
        pop es
        OK
        mov bx, [copy_psp]
        mov ah, 50h
        DOS 14026
        OK
        mov ah, 51h
        DOS 14027
        cmp bx, [copy_psp]
        jne failure
        OK
        mov bx, [psp]
        mov ah, 50h
        DOS 14028
        OK
        mov ah, 62h
        DOS 14029
        cmp bx, [psp]
        jne failure
        OK
        mov es, [copy_psp]
        mov ah, 49h
        DOS 14030
        SUCCESS
        mov bx, 0ffffh
        mov ah, 48h
        DOS 14031
        ERROR 8
        cmp bx, [largest]
        jne failure
        call walk_arena
        mov bx, 256
        mov ah, 48h
        DOS 14032
        CARRY_CLEAR
        mov [overlay_block], ax
        mov [overlay_block+2], ax
        mov [overlay_entry+2], ax
        mov es, ax
        xor di, di
        mov cx, 2048
        mov ax, 0cccch
        rep stosw
        push cs
        pop es
        OK
        mov dx, overlay_name
        mov bx, overlay_block
        mov ax, 4b03h
        DOS 14033
        CARRY_CLEAR
        call far [overlay_entry]
        cmp ax, 0a17eh
        jne failure
        cmp bx, [overlay_block]
        jne failure
        call guard_overlay
        OK
        mov ah, 62h
        DOS 14034
        cmp bx, [psp]
        jne failure
        OK
        mov dx, mz_name
        mov bx, overlay_block
        mov ax, 4b03h
        DOS 14035
        CARRY_CLEAR
        call far [overlay_entry]
        cmp ax, 5a3ch
        jne failure
        cmp bx, 3141h
        jne failure
        call guard_overlay
        OK
        inc word [overlay_block+2]
        mov dx, mz_name
        mov bx, overlay_block
        mov ax, 4b03h
        DOS 14036
        CARRY_CLEAR
        mov es, [overlay_block]
        mov ax, [overlay_block+2]
        cmp [es:32], ax
        jne failure
        push cs
        pop es
        call guard_overlay
        OK
        dec word [overlay_block+2]
        mov dx, missing
        mov bx, overlay_block
        mov ax, 4b03h
        DOS 14037
        ERROR 2
        call guard_overlay
        mov es, [overlay_block]
        mov ah, 49h
        DOS 14038
        SUCCESS
        mov bx, 0ffffh
        mov ah, 48h
        DOS 14039
        ERROR 8
        cmp bx, [largest]
        jne failure
        cmp word [load_guard], 0a55ah
        jne failure
        call walk_arena
        call save_chain
        jmp passed
guard_overlay:
        mov es, [overlay_block]
        cmp word [es:64], 0cccch
        jne failure
        cmp word [es:4094], 0cccch
        jne failure
        push cs
        pop es
        ret
restore_parent:
        push cs
        pop ds
        mov bx, [psp]
        or bx, bx
        jz .done
        mov ah, 50h
        int 21h
        mov dx, 80h
        mov ah, 1ah
        int 21h
        mov dx, [vector22]
        mov ds, [vector22+2]
        mov ax, 2522h
        int 21h
.done:
        push cs
        pop ds
        push cs
        pop es
        ret
largest: dw 0
vector22: dd 0
child_psp: dw 0
child_env: dw 0
copy_psp: dw 0
close_index: dw 0
overlay_block: dw 0,0
overlay_entry: dw 0,0
load_block: dw 0, tail,0, fcb,0, fcb,0, 0,0,0,0
load_guard: dw 0a55ah
tail: db 2,' 7',13
fcb: db 0,'           '
        times 4 db 0
com_name: db 'EXITQA.COM',0
mz_name: db 'OVLMZ.EXE',0
overlay_name: db 'OVERLAY.COM',0
missing: db 'NOOVL.EXE',0
result_name: db 'LOADMODE.RES',0
%include "harness.inc"
%include "arena.inc"
