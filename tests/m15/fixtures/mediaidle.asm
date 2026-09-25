; SPDX-License-Identifier: GPL-2.0-or-later
; Exercise the accepted M14 unknown-media lifetime and pathname recovery.
; A bounded idle interval is a candidate-specific trigger, not a DOS timer ABI.
; No Ctrl-C, medium replacement, native status acknowledgement or state patch.
bits 16
cpu 8086
org 100h
%include "macros.inc"
start:
        push cs
        pop ds
        push cs
        pop es
        mov dx, file_name
        xor cx, cx
        mov ah, 3ch
        DOS 19001
        CARRY_CLEAR
        mov [handle], ax
        OK
        mov bx, ax
        mov cx, 4
        mov dx, initial
        mov ah, 40h
        DOS 19002
        EQUAL_AX 4
        mov bx, [handle]
        mov ah, 68h
        DOS 19003
        SUCCESS
        mov bx, [handle]
        mov ah, 3eh
        DOS 19004
        SUCCESS
        mov dx, file_name
        mov ax, 3d00h
        DOS 19005
        CARRY_CLEAR
        mov [handle], ax
        OK
        ; Public FreeDOS SFT layout: observe the stale bit without issuing
        ; another native change query.
        mov bx, ax
        mov ax, 1220h
        int 2fh
        jc failure
        xor bx, bx
        mov bl, [es:di]
        mov ax, 1216h
        int 2fh
        jc failure
        mov [sft_ptr], di
        mov [sft_ptr+2], es
        push cs
        pop es
        call save_report
        mov ah, 2ch
        int 21h
        mov [second], dh
        mov word [outer], 256
        xor bp, bp
.wait:
        mov ah, 2ch
        int 21h
        sub dh, [second]
        jnc .elapsed
        add dh, 60
.elapsed:
        cmp dh, 32
        jae .ready
        dec bp
        jnz .wait
        dec word [outer]
        jnz .wait
        jmp failure
.ready:
        mov bx, [handle]
        mov dx, buffer
        mov cx, 4
        mov ah, 3fh
        DOS 19006
        ERROR 6
        cmp word [buffer], 0cccch
        jne failure
        cmp word [buffer+2], 0cccch
        jne failure
        cmp word [guard], 0a55ah
        jne failure
        les di, [sft_ptr]
        test word [es:di+5], 2000h
        jz failure
        push cs
        pop es
        mov bx, [handle]
        mov ah, 3eh
        DOS 19007
        ERROR 6
        les di, [sft_ptr]
        cmp word [es:di], 0
        jne failure
        push cs
        pop es
        mov bx, [handle]
        mov dx, buffer
        mov cx, 4
        mov ah, 3fh
        DOS 19008
        ERROR 6
        mov dx, file_name
        mov ax, 3d02h
        DOS 19009
        CARRY_CLEAR
        mov [handle], ax
        OK
        mov bx, ax
        mov dx, buffer
        mov cx, 4
        mov ah, 3fh
        DOS 19010
        EQUAL_AX 4
        cmp word [buffer], 'LI'
        jne failure
        cmp word [buffer+2], 'VE'
        jne failure
        mov bx, [handle]
        xor cx, cx
        xor dx, dx
        mov ax, 4200h
        DOS 19011
        EQUAL_AX 0
        mov bx, [handle]
        mov dx, replacement
        mov cx, 4
        mov ah, 40h
        DOS 19012
        EQUAL_AX 4
        mov bx, [handle]
        mov ah, 68h
        DOS 19013
        SUCCESS
        mov bx, [handle]
        mov ah, 3eh
        DOS 19014
        SUCCESS
        jmp passed
handle: dw 0
sft_ptr: dd 0
second: db 0
outer: dw 0
initial: db 'LIVE'
replacement: db 'DONE'
buffer: times 4 db 0cch
guard: dw 0a55ah
file_name: db 'IDLESAFE.DAT',0
result_name: db 'MEDIAIDL.RES',0
%include "harness.inc"
