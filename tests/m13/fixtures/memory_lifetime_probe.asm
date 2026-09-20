; SPDX-License-Identifier: GPL-2.0-or-later
; Acquire, overwrite, verify, and release the largest DOS-owned free block.
; The probe owns its complete COM image and stack after shrinking itself.
bits 16
cpu 8086
org 100h
start:
    cli
    mov ax, cs
    mov ss, ax
    mov sp, stack_top
    sti
    mov ds, ax
    mov es, ax
    mov bx, (program_end - $$ + 100h + 15) / 16
    mov ah, 4ah
    int 21h
    jc fail
    mov bx, 0ffffh
    mov ah, 48h
    int 21h
    jnc fail
    cmp ax, 8
    jne fail
    or bx, bx
    jz fail
    mov [paragraphs], bx
    mov ah, 48h
    int 21h
    jc fail
    mov [block], ax
    mov dx, ax
    add ax, [paragraphs]
    jc free_fail
    mov bp, [paragraphs]
    mov ax, 0a55ah
    cld
fill:
    mov es, dx
    xor di, di
    mov cx, 8
    rep stosw
    inc dx
    dec bp
    jnz fill
    mov dx, [block]
    mov bp, [paragraphs]
verify:
    mov es, dx
    xor di, di
    mov cx, 8
    repe scasw
    jne free_fail
    inc dx
    dec bp
    jnz verify
    mov es, [block]
    mov ah, 49h
    int 21h
    jc fail
    mov dx, passed
    mov ah, 9
    int 21h
    mov ax, 4c33h
    int 21h
free_fail:
    mov es, [block]
    mov ah, 49h
    int 21h
fail:
    mov dx, failed
    mov ah, 9
    int 21h
    mov ax, 4c50h
    int 21h
paragraphs dw 0
block dw 0
passed db 'MEM-LIFETIME-OK', 13, 10, '$'
failed db 'MEM-LIFETIME-FAIL', 13, 10, '$'
align 16, db 0
    times 256 db 0
stack_top:
program_end:
