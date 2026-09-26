; SPDX-License-Identifier: GPL-2.0-or-later
; Bounded resident child, retained only until the disposable session reboots.
bits 16
cpu 8086
org 100h
start:
        push cs
        pop ds
        mov es, [2ch]
        mov ah, 49h
        int 21h
        jc failed
        mov word [2ch], 0
        mov word [marker], 6011h
        cmp byte [82h], '1'
        je .mode
        mov word [marker], 6022h
.mode:
        mov dx, handler
        mov ax, 2560h
        int 21h
        mov dx, quiet_handler
        mov ax, 2523h
        int 21h
        mov ax, 2524h
        int 21h
        cmp byte [82h], '1'
        jne .legacy
        mov dx, 30h
        mov ax, 312ah
        int 21h
.legacy:
        mov dx, 300h
        int 27h
failed:
        mov ax, 4cffh
        int 21h
handler:
        mov ax, [cs:marker]
        iret
quiet_handler:
        iret
marker: dw 0
%if ($-$$+100h)>300h
%error Resident code exceeds its declared kept extent
%endif
