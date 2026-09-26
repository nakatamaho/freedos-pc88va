; SPDX-License-Identifier: GPL-2.0-or-later
; Ordinary DOS open/dirty-handle exchange probe on disposable media only.
; Pause for a normal external exchange, then observe old-handle write/close.
bits 16
cpu 8086
org 100h

start:
        push cs
        pop ds
        mov dx, old_name
        xor cx, cx
        mov ah, 3ch
        int 21h
        jc fail
        mov [handle], ax
        mov bx, ax
        mov dx, before_data
        mov cx, 4
        mov ah, 40h
        int 21h
        jc fail
        cmp ax, 4
        jne fail
        mov dx, ready_message
        mov ah, 09h
        int 21h
        mov ah, 08h
        int 21h

        mov bx, [handle]
        mov dx, after_data
        mov cx, 1024
        mov ah, 40h
        int 21h
        mov [write_result], ax
        mov dx, rejected_message
        jc .write_observed
        mov byte [accepted], 1
        mov dx, accepted_message
.write_observed:
        mov ah, 09h
        int 21h
        mov bx, [handle]
        mov ah, 3eh
        int 21h
        mov [close_result], ax
        mov dx, close_error
        jc .close_observed
        mov dx, close_ok
.close_observed:
        mov ah, 09h
        int 21h
        ; This is only a guest observation. The independent check must also
        ; require B unchanged and a usable shell; no PASS is printed here.
        xor al, al
        mov al, [accepted]
        mov ah, 4ch
        int 21h
fail:
        mov dx, failed_message
        mov ah, 09h
        int 21h
        mov ax, 4c02h
        int 21h

handle dw 0
write_result dw 0
close_result dw 0
accepted db 0
old_name db 'OLD.DAT', 0
before_data db 'OLD!'
after_data times 1024 db 'X'
ready_message db 'M14SWAP:READY', 13, 10, '$'
rejected_message db 'M14SWAP:OLD-WRITE-REJECTED', 13, 10, '$'
accepted_message db 'M14SWAP:OLD-WRITE-ACCEPTED', 13, 10, '$'
close_ok db 'M14SWAP:CLOSE-RETURNED', 13, 10, '$'
close_error db 'M14SWAP:CLOSE-ERROR', 13, 10, '$'
failed_message db 'M14SWAP:SETUP-FAIL', 13, 10, '$'
