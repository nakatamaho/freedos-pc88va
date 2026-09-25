; SPDX-License-Identifier: GPL-2.0-or-later
; Original bounded ASCII filter for real FreeCOM redirection and pipelines.
bits 16
cpu 8086
org 100h
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        mov word [blocks_left], 1024
.read:
        xor bx, bx
        mov dx, buffer
        mov cx, 31
        mov ah, 3fh
        int 21h
        jc failed
        or ax, ax
        jz finished
        cmp ax, 31
        ja failed
        mov [count], ax
        mov cx, ax
        mov si, buffer
.upper:
        cmp byte [si], 'a'
        jb .next
        cmp byte [si], 'z'
        ja .next
        sub byte [si], 'a'-'A'
.next:
        inc si
        loop .upper
        mov bx, 1
        mov dx, buffer
        mov cx, [count]
        mov ah, 40h
        int 21h
        jc failed
        cmp ax, [count]
        jne failed
        dec word [blocks_left]
        jnz .read
failed:
        mov ax, 4c07h
        int 21h
finished:
        mov ax, 4c00h
        int 21h
blocks_left: dw 0
count: dw 0
        dw 0a55ah
buffer: times 31 db 0
        dw 05aa5h
