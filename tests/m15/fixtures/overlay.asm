; SPDX-License-Identifier: GPL-2.0-or-later
; Original flat overlay: no PSP and no DOS termination.
bits 16
cpu 8086
org 0
        mov ax, 0a17eh
        mov bx, cs
        retf
        times 64-($-$$) db 0
