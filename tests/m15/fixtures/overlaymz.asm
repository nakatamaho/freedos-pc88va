; SPDX-License-Identifier: GPL-2.0-or-later
; Original MZ overlay with one segment relocation; exactly 64 image bytes.
bits 16
cpu 8086
org 0
        dw 5a4dh, image_end, 1, 1, 3, 40h, 40h, 0, 400h, 0, 0, 0, 28, 0
        dw 32, 0
        times 48-($-$$) db 0
image:
        mov ax, cs
        cmp ax, [cs:32]
        jne invalid
        mov ax, 5a3ch
        mov bx, 3141h
        retf
invalid:
        xor ax, ax
        retf
        times 32-($-image) db 0
        dw 0
        times 64-($-image) db 0
image_end:
