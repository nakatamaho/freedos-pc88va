; SPDX-License-Identifier: GPL-2.0-or-later
; Abort from a real CON device error; the parent checks termination type 2.
bits 16
cpu 8086
org 100h
        push cs
        pop ds
        mov dx, handler
        mov ax, 2524h
        int 21h
        xor bx, bx
        mov ax, 4400h
        int 21h
        xor dh, dh
        or dl, 20h
        mov ax, 4401h
        int 21h
        mov dx, buffer
        mov cx, 1
        mov ah, 3fh
        int 21h
        mov ax, 4ceeh
        int 21h
handler:
        mov al, 2
        iret
buffer: db 0
