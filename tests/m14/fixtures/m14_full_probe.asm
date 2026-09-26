; SPDX-License-Identifier: GPL-2.0-or-later
; M14 capacity probe.  The command tail selects R (root directory) or D
; (data area); the media is disposable and is inspected after the run.
bits 16
cpu 8086
org 100h

start:
        mov ax, cs
        mov ds, ax
        mov es, ax
        xor cx, cx
        mov cl, [80h]
        mov si, 81h
.skip_space:
        or cx, cx
        jz fail
        cmp byte [si], ' '
        je .space
        cmp byte [si], 9
        jne .mode
.space:
        inc si
        dec cx
        jmp .skip_space
.mode:
        cmp byte [si], 'D'
        je data_full
        cmp byte [si], 'd'
        je data_full
        cmp byte [si], 'R'
        je root_full
        cmp byte [si], 'r'
        jne fail

root_full:
        xor ax, ax
        mov [counter], ax
.root_next:
        mov ax, [counter]
        mov di, root_name+1
        mov bx, 1000
        call decimal_digit
        mov bx, 100
        call decimal_digit
        mov bx, 10
        call decimal_digit
        ; The third decimal_digit call leaves the units remainder in AX.
        add al, '0'
        mov [root_name+4], al
        mov dx, root_name
        xor cx, cx
        mov ah, 3ch
        int 21h
        jc root_exhausted
        mov [handle], ax
        call close_file
        inc word [counter]
        cmp word [counter], 220
        jb .root_next
        jmp fail

root_exhausted:
        ; alloc_find_free returns DE_TOOMANY for a full fixed root. Other
        ; failures (including protection) must not manufacture full success.
        cmp ax, 4
        jne fail
        cmp word [counter], 0
        je fail
        mov dx, first_root_name
        mov ah, 41h
        int 21h
        jc fail
        mov dx, root_name
        xor cx, cx
        mov ah, 3ch
        int 21h
        jc fail
        mov [handle], ax
        mov bx, ax
        mov dx, recovered_data
        mov cx, 4
        mov ah, 40h
        int 21h
        jc fail
        cmp ax, 4
        jne fail
        call close_file
        mov dx, root_pass
        jmp pass

data_full:
        mov dx, data_name
        xor cx, cx
        mov ah, 3ch
        int 21h
        jc fail
        mov [handle], ax
        xor ax, ax
        mov [counter], ax
.data_next:
        mov bx, [handle]
        mov dx, data_buffer
        mov cx, 1024
        mov ah, 40h
        int 21h
        jc fail
        cmp ax, 1024
        jb data_exhausted
        ja fail
        inc word [counter]
        cmp word [counter], 1400
        jb .data_next
        jmp fail

data_exhausted:
        ; rwblock reports disk-full as a successful short/zero write. Require
        ; progress, then another write must complete zero bytes while full.
        cmp word [counter], 0
        je fail
        mov bx, [handle]
        mov dx, data_buffer
        mov cx, 1024
        mov ah, 40h
        int 21h
        jc fail
        or ax, ax
        jnz fail
        call close_file
        ; Truncate one cluster through the ordinary zero-length write, then
        ; append one cluster and close. The saved image remains full, and the
        ; released allocation must actually be usable by a subsequent write.
        mov dx, data_name
        mov ax, 3d02h
        int 21h
        jc fail
        mov [handle], ax
        mov bx, ax
        mov ax, 4202h
        mov cx, 0ffffh
        mov dx, -1024
        int 21h
        jc fail
        xor cx, cx
        mov dx, data_buffer
        mov ah, 40h
        int 21h
        jc fail
        or ax, ax
        jnz fail
        mov cx, 1024
        mov dx, data_buffer
        mov ah, 40h
        int 21h
        jc fail
        cmp ax, 1024
        jne fail
        call close_file
        mov dx, data_pass
        jmp pass

decimal_digit:
        xor dx, dx
        div bx
        add al, '0'
        stosb
        mov ax, dx
        ret

close_file:
        mov bx, [handle]
        mov ah, 3eh
        int 21h
        jc fail
        ret

pass:
        mov ah, 09h
        int 21h
        mov ax, 4c00h
        int 21h

fail:
        mov dx, fail_message
        mov ah, 09h
        int 21h
        mov ax, 4c01h
        int 21h

handle dw 0
counter dw 0
root_name db 'R0000.TXT', 0
first_root_name db 'R0000.TXT', 0
recovered_data db 'ROOT'
data_name db 'DATAFULL.BIN', 0
data_buffer times 1024 db 'D'
root_pass db 'M14FULL:ROOT:PASS', 13, 10, '$'
data_pass db 'M14FULL:DATA:PASS', 13, 10, '$'
fail_message db 'M14FULL:FAIL', 13, 10, '$'
