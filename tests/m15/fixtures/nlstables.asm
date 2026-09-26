; SPDX-License-Identifier: GPL-2.0-or-later
; DOS 5 NLS pointer packets: documented lengths, ASCII ordering and guards.
; Tables are read-only; no non-ASCII input/display qualification is implied.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%macro TABLE 2
        mov byte [kind], %2
        call fill_packet
        mov bx, 0ffffh
        mov dx, 0ffffh
        mov cx, 5
        mov di, table
        mov ax, 6500h | %2
        DOS %1
        CARRY_CLEAR
        call check_table
        mov ax, [table+1]
        mov [previous], ax
        mov ax, [table+3]
        mov [previous+2], ax
        OK
        mov bx, 437
        mov dx, 1
        mov cx, 5
        mov di, table
        mov ax, 6500h | %2
        DOS %1+1
        CARRY_CLEAR
        call check_same
        OK
        call fill_packet
        mov bx, 0ffffh
        mov dx, 0ffffh
        mov cx, 4
        mov di, table
        mov ax, 6500h | %2
        DOS %1+2
        ERROR 1
        call check_untouched
        mov bx, 0ffffh
        mov dx, 0ffffh
        xor cx, cx
        mov di, table
        mov ax, 6500h | %2
        DOS %1+3
        ; Pinned FreeDOS kernel/nls.c returns DE_INVLDDATA (13) for CX=0.
        ERROR 13
        call check_untouched
        mov bx, 437
        mov dx, 0fffeh
        mov cx, 5
        mov di, table
        mov ax, 6500h | %2
        DOS %1+4
        ; FreeDOS syscall_MUX14 returns DE_INVLDFUNC (1) for an
        ; unavailable country/codepage package.
        ERROR 1
        call check_untouched
        mov bx, 0ffffh
        mov dx, 0ffffh
        mov cx, 5
        mov di, table
        mov ax, 6500h | %2
        DOS %1+5
        CARRY_CLEAR
        call check_same
        OK
%endmacro
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        mov ax, 6601h
        DOS 25001
        CARRY_CLEAR
        cmp bx, 437
        jne failure
        cmp dx, 437
        jne failure
        OK
        TABLE 25002, 2
        TABLE 25008, 4
        TABLE 25014, 5
        TABLE 25020, 6
        TABLE 25026, 7
        mov ax, 6300h
        DOS 25032
        cmp al, 0
        jne failure
        mov ax, [previous]
        add ax, 2
        cmp si, ax
        jne failure
        mov ax, [snapshot+18]
        cmp ax, [previous+2]
        jne failure
        mov es, ax
        cmp word [es:si], 0
        jne failure
        push cs
        pop es
        OK
        call fill_packet
        mov bx, 0ffffh
        mov dx, 0ffffh
        mov cx, 5
        mov di, table
        mov ax, 6503h
        DOS 25033
        ERROR 1
        call check_untouched
        jmp passed
fill_packet:
        mov word [table], 0cccch
        mov word [table+2], 0cccch
        mov byte [table+4], 0cch
        ret
check_same:
        mov ax, [table+1]
        cmp ax, [previous]
        jne failure
        mov ax, [table+3]
        cmp ax, [previous+2]
        jne failure
        jmp check_table
check_untouched:
        cmp word [table], 0cccch
        jne failure
        cmp word [table+2], 0cccch
        jne failure
        cmp byte [table+4], 0cch
        jne failure
        jmp check_guard
check_table:
        mov al, [kind]
        cmp [table], al
        jne failure
        mov bx, [table+1]
        mov es, [table+3]
        mov ax, es
        or ax, bx
        jz failure
        cmp byte [kind], 5
        je .filename
        cmp byte [kind], 6
        je .collation
        cmp byte [kind], 7
        je .dbcs
        cmp word [es:bx], 128
        jne failure
        jmp .done
.filename:
        xor ax, ax
        mov al, [es:bx+9]
        add ax, 8
        cmp [es:bx], ax
        jne failure
        cmp byte [es:bx+3], 'A'
        ja failure
        cmp byte [es:bx+4], 'Z'
        jb failure
        cmp byte [es:bx+7], 'A'
        jae failure
        xor cx, cx
        mov cl, [es:bx+9]
        add bx, 10
        xor dx, dx
.illegal:
        jcxz .illegal_done
        cmp byte [es:bx], ':'
        jne .next
        inc dx
.next:
        inc bx
        loop .illegal
.illegal_done:
        cmp dx, 1
        jne failure
        jmp .done
.collation:
        cmp word [es:bx], 256
        jne failure
        mov al, [es:bx+2+'A']
        cmp al, [es:bx+2+'B']
        jae failure
        cmp al, [es:bx+2+'a']
        jne failure
        mov al, [es:bx+2+'0']
        cmp al, [es:bx+2+'1']
        jae failure
        jmp .done
.dbcs:
        cmp word [es:bx], 0
        jne failure
        cmp word [es:bx+2], 0
        jne failure
.done:
        push cs
        pop es
check_guard:
        cmp word [table-2], 0a55ah
        jne failure
        cmp word [table+5], 05aa5h
        jne failure
        ret
kind: db 0
previous: dd 0
        dw 0a55ah
table: times 5 db 0cch
        dw 05aa5h
result_name: db 'NLSTABLE.RES',0
%include "harness.inc"
