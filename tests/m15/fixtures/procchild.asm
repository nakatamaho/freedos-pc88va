; SPDX-License-Identifier: GPL-2.0-or-later
; Original child checks PSP/tail/FCBs/environment/handles, then nests EXEC.
bits 16
cpu 8086
org 100h
start:
        mov bx, cs
        mov dx, ds
        cmp bx, dx
        jne failed
        mov dx, es
        cmp bx, dx
        jne failed
        mov bx, 1000h
        mov ah, 4ah
        int 21h
        jc failed
        cld
        cmp word [0], 20cdh
        jne failed
        mov ax, [16h]
        or ax, ax
        jz failed
        mov dx, cs
        cmp ax, dx
        je failed
        mov ah, 62h
        int 21h
        mov ax, cs
        cmp bx, ax
        jne failed
        mov ah, 2fh
        int 21h
        cmp bx, 80h
        jne failed
        mov ax, es
        mov dx, cs
        cmp ax, dx
        jne failed
        cmp byte [80h], 9
        jne failed
        cmp byte [8ah], 13
        jne failed
        mov si, 82h
        mov di, tail_suffix
        mov cx, 8
        repe cmpsb
        jne failed
        mov si, 5dh
        mov di, fcb_names
        mov cx, 11
        repe cmpsb
        jne failed
        mov si, 6dh
        mov cx, 11
        repe cmpsb
        jne failed
        mov es, [2ch]
        xor di, di
        mov si, environment
        mov cx, environment_end-environment
        repe cmpsb
        jne failed
        push cs
        pop es
        mov bx, 5
        mov dx, buffer
        mov cx, 2
        mov ah, 3fh
        int 21h
        jc failed
        cmp ax, 2
        jne failed
        cmp word [buffer], 'ab'
        jne failed
        mov bx, 6
        mov dx, buffer
        mov cx, 1
        mov ah, 3fh
        int 21h
        jnc failed
        cmp ax, 6
        jne failed
        mov bx, 5
        mov ah, 3eh
        int 21h
        jc failed
        mov dx, break_handler
        mov ax, 2523h
        int 21h
        mov dx, critical_handler
        mov ax, 2524h
        int 21h
        cmp byte [81h], 'L'
        je legacy20
        cmp byte [81h], 'Z'
        je legacy00
        cmp byte [81h], 'N'
        jne failed
        mov ax, cs
        mov [exec_block+4], ax
        mov [exec_block+8], ax
        mov [exec_block+12], ax
        mov dx, grandchild
        mov bx, exec_block
        mov ax, 4b00h
        int 21h
        jc failed
        mov ah, 4dh
        int 21h
        cmp ax, 7
        jne failed
        mov ax, 4c2ah
        int 21h
legacy20:
        int 20h
legacy00:
        xor ah, ah
        int 21h
failed:
        mov ax, 4c7fh
        int 21h
break_handler:
        iret
critical_handler:
        mov al, 3
        iret
tail_suffix: db ' one two'
fcb_names: db 'FIRST   TXTSECOND  BIN'
environment: db 'M15VAR=VALUE',0,0
environment_end:
grandchild: db 'EXITQA.COM',0
tail: db 2,' 7',13
exec_block: dw 0, tail, 0, 5ch, 0, 6ch, 0
        times 8 db 0
buffer: times 2 db 0
