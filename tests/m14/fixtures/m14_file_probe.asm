; SPDX-License-Identifier: GPL-2.0-or-later
; M14 ordinary DOS file-operation probe.  Every mutation is issued through
; the documented INT 21h handle/path services; host transcripts are not used
; as a substitute for the on-media checks.
bits 16
cpu 8086
org 100h

start:
        mov ax, cs
        mov ds, ax
        mov es, ax

        ; Create, write, zero-write, seek/overwrite, and extend a file.
        mov dx, file_name
        xor cx, cx
        mov ah, 3ch
        int 21h
        jc fail
        mov [handle], ax
        mov bx, ax
        mov dx, pattern
        mov cx, 1024
        mov ah, 40h
        int 21h
        jc fail
        cmp ax, 1024
        jne fail

        ; At EOF a zero-length write keeps the length. At other offsets it
        ; truncates/extends instead, so this case must remain at EOF.
        mov bx, [handle]
        xor cx, cx
        mov dx, pattern
        mov ah, 40h
        int 21h
        jc fail
        or ax, ax
        jnz fail

        ; Overwrite four bytes at offset 100.
        mov bx, [handle]
        mov ah, 42h
        xor al, al
        xor cx, cx
        mov dx, 100
        int 21h
        jc fail
        mov dx, overwrite
        mov cx, 4
        mov ah, 40h
        int 21h
        jc fail
        cmp ax, 4
        jne fail

        ; Seek beyond EOF and write one byte, extending the file to 2048.
        mov bx, [handle]
        mov ah, 42h
        xor al, al
        xor cx, cx
        mov dx, 2047
        int 21h
        jc fail
        mov dx, extend_byte
        mov cx, 1
        mov ah, 40h
        int 21h
        jc fail
        cmp ax, 1
        jne fail
        ; FreeDOS does not promise zero-filled holes without WRITEZEROS.
        ; Fill the gap explicitly after exercising the beyond-EOF extension,
        ; so every final byte has an independent deterministic expectation.
        mov bx, [handle]
        mov ah, 42h
        xor al, al
        xor cx, cx
        mov dx, 1024
        int 21h
        jc fail
        mov dx, gap_data
        mov cx, 1023
        mov ah, 40h
        int 21h
        jc fail
        cmp ax, 1023
        jne fail
        call close_file

        ; Reopen/read the persisted bytes and validate both the overwrite and
        ; the sparse extension boundary.
        mov dx, file_name
        xor al, al
        mov ah, 3dh
        int 21h
        jc fail
        mov [handle], ax
        mov bx, ax
        mov dx, read_buffer
        mov cx, 2048
        mov ah, 3fh
        int 21h
        jc fail
        cmp ax, 2048
        jne fail
        mov si, pattern
        mov di, read_buffer
        mov cx, 100
        repe cmpsb
        jne fail
        cmp byte [read_buffer+100], 'Z'
        jne fail
        cmp byte [read_buffer+101], 'Z'
        jne fail
        cmp byte [read_buffer+102], 'Z'
        jne fail
        cmp byte [read_buffer+103], 'Z'
        jne fail
        mov si, pattern+104
        mov di, read_buffer+104
        mov cx, 920
        repe cmpsb
        jne fail
        mov si, gap_data
        mov di, read_buffer+1024
        mov cx, 1023
        repe cmpsb
        jne fail
        cmp byte [read_buffer+2047], 'E'
        jne fail
        call close_file

        ; Rename and delete through the DOS path service.
        mov dx, file_name
        mov di, renamed_file
        mov ah, 56h
        int 21h
        jc fail
        mov dx, renamed_file
        mov ah, 41h
        int 21h
        jc fail

        ; Create/read/delete a zero-length file.
        mov dx, zero_file
        xor cx, cx
        mov ah, 3ch
        int 21h
        jc fail
        mov [handle], ax
        mov bx, ax
        xor cx, cx
        mov dx, pattern
        mov ah, 40h
        int 21h
        jc fail
        or ax, ax
        jnz fail
        call close_file
        mov dx, zero_file
        xor al, al
        mov ah, 3dh
        int 21h
        jc fail
        mov [handle], ax
        mov bx, ax
        mov dx, read_buffer
        mov cx, 1
        mov ah, 3fh
        int 21h
        jc fail
        or ax, ax
        jnz fail
        call close_file
        mov dx, zero_file
        mov ah, 41h
        int 21h
        jc fail

        ; Exercise mkdir, nested create, rename, read, delete, and rmdir.
        mov dx, subdir
        mov ah, 39h
        int 21h
        jc fail
        mov dx, nested_file
        xor cx, cx
        mov ah, 3ch
        int 21h
        jc fail
        mov [handle], ax
        mov bx, ax
        mov dx, nested_data
        mov cx, 4
        mov ah, 40h
        int 21h
        jc fail
        cmp ax, 4
        jne fail
        call close_file
        mov dx, nested_file
        mov di, nested_renamed
        mov ah, 56h
        int 21h
        jc fail
        mov dx, nested_renamed
        xor al, al
        mov ah, 3dh
        int 21h
        jc fail
        mov [handle], ax
        mov bx, ax
        mov dx, read_buffer
        mov cx, 4
        mov ah, 3fh
        int 21h
        jc fail
        cmp ax, 4
        jne fail
        cmp word [read_buffer], 'NE'
        jne fail
        cmp word [read_buffer+2], 'ST'
        jne fail
        call close_file
        mov dx, nested_renamed
        mov ah, 41h
        int 21h
        jc fail
        mov dx, subdir
        mov ah, 3ah
        int 21h
        jc fail

        mov dx, pass_message
        mov ah, 09h
        int 21h
        mov ax, 4c00h
        int 21h

close_file:
        mov bx, [handle]
        mov ah, 3eh
        int 21h
        jc fail
        ret

fail:
        mov dx, fail_message
        mov ah, 09h
        int 21h
        mov ax, 4c01h
        int 21h

handle dw 0
file_name db 'M14A.DAT', 0
renamed_file db 'M14B.DAT', 0
zero_file db 'M14ZERO.TXT', 0
subdir db 'M14SUB', 0
nested_file db 'M14SUB\NEST.TXT', 0
nested_renamed db 'M14SUB\RENAMED.TXT', 0
pattern times 1024 db 'A'
gap_data times 1023 db 'B'
overwrite db 'ZZZZ'
extend_byte db 'E'
nested_data db 'NEST'
read_buffer times 2048 db 0
pass_message db 'M14FILE:PASS', 13, 10, '$'
fail_message db 'M14FILE:FAIL', 13, 10, '$'
