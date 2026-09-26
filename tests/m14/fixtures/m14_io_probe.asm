; SPDX-License-Identifier: GPL-2.0-or-later
; Ordinary DOS multi-sector I/O for controlled external media interruption.
; Report actual returned flags/counts. A marker alone is not qualification.
bits 16
cpu 8086
org 100h

start:
        push cs
        pop ds
        mov dx, read_name
        mov ax, 3d00h
        int 21h
        jc setup_failed
        mov [read_handle], ax
        mov dx, write_name
        xor cx, cx
        mov ah, 3ch
        int 21h
        jc setup_failed
        mov [write_handle], ax
        mov dx, ready_message
        call print
        mov ah, 08h
        int 21h

        mov bx, [write_handle]
        mov dx, write_data
        mov cx, 4096
        mov ah, 40h
        int 21h
        mov [result], ax
        mov dx, write_count
        jnc .write_report
        mov dx, write_error
.write_report:
        call report
        mov bx, [write_handle]
        mov ah, 3eh
        int 21h
        mov [result], ax
        mov dx, close_ok
        jnc .close_report
        mov dx, close_error
.close_report:
        call report

        ; This second handle was opened before the interrupted operation.
        mov bx, [read_handle]
        mov dx, read_data
        mov cx, 64
        mov ah, 3fh
        int 21h
        mov [result], ax
        mov dx, read_count
        jnc .read_report
        mov dx, read_error
.read_report:
        call report
        mov bx, [read_handle]
        mov ah, 3eh
        int 21h
        mov ax, 4c00h
        int 21h

setup_failed:
        mov dx, setup_error
        call print
        mov ax, 4c02h
        int 21h

print:
        mov ah, 09h
        int 21h
        ret

report:
        call print
        mov bx, [result]
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
        mov dx, newline
        call print
        ret

read_handle dw 0
write_handle dw 0
result dw 0
read_name db 'MEDIAID.TXT', 0
write_name db 'IOFAULT.DAT', 0
ready_message db 'M14IO:READY', 13, 10, '$'
setup_error db 'M14IO:SETUP-FAIL', 13, 10, '$'
write_count db 'M14IO:WRITE-COUNT=', '$'
write_error db 'M14IO:WRITE-ERROR=', '$'
close_ok db 'M14IO:CLOSE-OK=', '$'
close_error db 'M14IO:CLOSE-ERROR=', '$'
read_count db 'M14IO:OLD-READ-COUNT=', '$'
read_error db 'M14IO:OLD-READ-ERROR=', '$'
newline db 13, 10, '$'
write_data times 4096 db 'W'
read_data times 64 db 0
