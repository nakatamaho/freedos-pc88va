; SPDX-License-Identifier: GPL-2.0-or-later
; Request DOS's documented abort action by returning RETF with carry set.
bits 16
cpu 8086
org 100h
        push cs
        pop ds
        mov dx, abort_handler
        mov ax, 2523h
        int 21h
        mov ah, 08h
        int 21h
        mov ax, 4ceeh
        int 21h
abort_handler:
        stc
        retf
