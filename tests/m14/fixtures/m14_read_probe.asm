; SPDX-License-Identifier: GPL-2.0-or-later
; Fresh-boot DOS reread of every DATAFULL.BIN byte, including EOF and close.
; The independent checker binds the measured length to the saved full medium.
bits 16
cpu 8086
org 100h

start:
        push cs
        pop ds
        mov dx, filename
        mov ax, 3d00h
        int 21h
        jc failed
        mov [handle], ax
.read:
        mov bx, [handle]
        mov dx, buffer
        mov cx, 1024
        mov ah, 3fh
        int 21h
        jc failed
        cmp ax, 1024
        ja failed
        or ax, ax
        jz .eof
        add [total_low], ax
        adc word [total_high], 0
        jc failed
        mov cx, ax
        mov si, buffer
.check:
        lodsb
        cmp al, 'D'
        jne failed
        loop .check
        jmp .read
.eof:
        mov ax, [total_low]
        or ax, [total_high]
        jz failed
        mov bx, [handle]
        mov ah, 3eh
        int 21h
        jc failed
        mov dx, checked
        call print
        mov bx, [total_high]
        call hexword
        mov bx, [total_low]
        call hexword
        mov dx, newline
        call print
        mov ax, 4c00h
        int 21h

failed:
        mov dx, failure
        call print
        mov ax, 4c01h
        int 21h

print:
        mov ah, 09h
        int 21h
        ret

hexword:
        mov cx, 4
.digit:
        push cx
        mov cl, 4
        rol bx, cl
        mov dl, bl
        and dl, 0fh
        add dl, '0'
        cmp dl, '9'
        jbe .emit
        add dl, 'A' - '9' - 1
.emit:
        mov ah, 02h
        int 21h
        pop cx
        loop .digit
        ret

handle dw 0
total_low dw 0
total_high dw 0
filename db 'DATAFULL.BIN', 0
checked db 'M14READ:CHECKED-BYTES=', '$'
failure db 'M14READ:FAIL', 13, 10, '$'
newline db 13, 10, '$'
buffer times 1024 db 0
