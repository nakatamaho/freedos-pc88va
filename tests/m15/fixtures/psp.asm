; SPDX-License-Identifier: GPL-2.0-or-later
; Candidate observation of the undocumented child-PSP constructor.
; This probes owned memory, inherited state, and restoration without claiming
; a historical compatibility contract for INT 21h/AH=55h.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%define M15_FAILURE_HOOK save_chain
%define M15_CHAIN_NAME 'PSP.MCB'
start:
        push cs
        pop ds
        push cs
        pop es
        cld

        mov ah, 62h
        DOS 5501
        mov [psp], bx
        mov ax, cs
        cmp bx, ax
        jne failure
        mov [parent_psp], bx
        mov ax, [cs:2ch]
        mov [parent_env], ax
        OK

        ; Keep the original parent tail and install a distinctive 128-byte
        ; value so the child copy can be checked exactly and then restored.
        mov si, 80h
        mov di, tail_backup
        mov cx, 64
        rep movsw
        mov si, tail_expected
        mov di, 80h
        mov cx, 64
        rep movsw

        mov bx, 1000h
        mov ah, 4ah
        DOS 5502
        SUCCESS
        mov ah, 52h
        DOS 5503
        mov es, [snapshot+20]
        mov ax, [es:bx-2]
        mov [arena_first], ax
        push cs
        pop es
        OK
        call walk_arena
        mov ax, [own_blocks]
        mov [base_owned], ax

        mov bx, 20h
        mov ah, 48h
        DOS 5504
        CARRY_CLEAR
        mov [child_psp], ax
        dec ax
        mov es, ax
        cmp word [es:3], 20h
        jne failure
        mov ax, [parent_psp]
        cmp [es:1], ax
        jne failure
        push cs
        pop es
        OK

        mov dx, temp_file
        xor cx, cx
        mov ah, 3ch
        DOS 5505
        CARRY_CLEAR
        mov [file_handle], ax
        cmp ax, 20
        jae failure
        OK
        mov bx, [file_handle]
        mov dx, payload
        mov cx, 1
        mov ah, 40h
        DOS 5506
        EQUAL_AX 1
        mov bx, [file_handle]
        xor cx, cx
        xor dx, dx
        mov ax, 4200h
        DOS 5507
        EQUAL_AX 0
        EQUAL_DX 0

        ; DX is the caller-owned PSP segment. SI is the end segment stored at
        ; PSP:0002h by this implementation, not a paragraph count.
        mov dx, [child_psp]
        mov si, dx
        add si, 20h
        mov ah, 55h
        DOS 5508
        OK

        mov ah, 62h
        DOS 5509
        cmp bx, [child_psp]
        jne failure
        OK

        mov es, [child_psp]
        mov ax, [parent_psp]
        cmp [es:16h], ax
        jne failure
        mov ax, [child_psp]
        add ax, 20h
        cmp [es:02h], ax
        jne failure
        mov ax, [parent_env]
        cmp [es:2ch], ax
        jne failure
        cmp word [es:32h], 20
        jne failure
        cmp word [es:34h], 18h
        jne failure
        mov ax, [child_psp]
        cmp [es:36h], ax
        jne failure
        cmp word [es:38h], 0
        jne failure
        mov ax, [parent_psp]
        cmp [es:3ah], ax
        jne failure
        mov si, tail_expected
        mov di, 80h
        mov cx, 64
        repe cmpsw
        jne failure
        mov bx, [file_handle]
        add bx, 18h
        mov al, [es:bx]
        mov [child_file_slot], al
        mov ax, [parent_psp]
        mov es, ax
        mov ax, [es:34h]
        mov [parent_table_off], ax
        mov ax, [es:36h]
        mov [parent_table_seg], ax
        mov ax, [parent_table_seg]
        mov es, ax
        mov bx, [parent_table_off]
        add bx, [file_handle]
        mov al, [es:bx]
        cmp al, [child_file_slot]
        jne failure

        mov bx, [file_handle]
        mov ah, 3eh
        DOS 5510
        SUCCESS
        mov es, [child_psp]
        mov bx, [file_handle]
        add bx, 18h
        cmp byte [es:bx], 0ffh
        jne failure
        mov bx, [parent_psp]
        mov ah, 50h
        DOS 5511
        OK
        mov ah, 62h
        DOS 5512
        cmp bx, [parent_psp]
        jne failure
        OK

        mov bx, [file_handle]
        mov dx, readback
        mov cx, 1
        mov ah, 3fh
        DOS 5513
        EQUAL_AX 1
        mov al, [readback]
        cmp al, [payload]
        jne failure
        OK

        ; Restore caller state before closing inherited storage and releasing
        ; the PSP allocation.
        mov si, tail_backup
        mov di, 80h
        mov cx, 64
        rep movsw
        mov bx, [file_handle]
        mov ah, 3eh
        DOS 5514
        SUCCESS
        mov dx, temp_file
        mov ah, 41h
        DOS 5515
        SUCCESS
        mov es, [child_psp]
        mov ah, 49h
        DOS 5516
        SUCCESS
        call walk_arena
        mov ax, [own_blocks]
        cmp ax, [base_owned]
        jne failure
        mov ah, 62h
        DOS 5517
        cmp bx, [parent_psp]
        jne failure
        OK
        call save_chain
        jmp passed

parent_psp: dw 0
parent_env: dw 0
child_psp: dw 0
file_handle: dw 0
parent_table_off: dw 0
parent_table_seg: dw 0
child_file_slot: db 0
payload: db 'Q'
readback: db 0
temp_file: db 'PSPTEMP.DAT',0
tail_backup: times 128 db 0
tail_expected: db 3,'ABC',13
        times 123 db 0a5h
result_name: db 'PSP.RES',0
%include "arena.inc"
%include "harness.inc"
