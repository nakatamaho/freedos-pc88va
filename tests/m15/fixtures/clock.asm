; SPDX-License-Identifier: GPL-2.0-or-later
; DOS date/time semantics, bounded progression, and calendar rollover.
; Run only with a disposable emulator configuration and persistence copy.
; Historical context: Microsoft MS-DOS Encyclopedia, INT 21h/2Ah-2Dh and 57h; FreeDOS baseline is the port reference.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%macro SETDATE 5
        mov cx, %2
        mov dx, (%3 << 8) | %4
        mov ah, 2bh
        DOS %1
        EQUAL_AL %5
%endmacro
%macro DATEIS 5
        mov ah, 2ah
        DOS %1
        cmp cx, %2
        jne failure
        cmp dx, (%3 << 8) | %4
        jne failure
        EQUAL_AL %5
%endmacro
%macro SETTIME 6
        mov cx, (%2 << 8) | %3
        mov dx, (%4 << 8) | %5
        mov ah, 2dh
        DOS %1
        EQUAL_AL %6
%endmacro
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        mov ah, 2ah
        DOS 7001
        mov [original_year], cx
        mov [original_md], dx
        cmp al, 6
        ja failure
        OK
        mov ah, 2ch
        DOS 7002
        call valid_time
        mov [original_hm], cx
        mov [original_sh], dx
        OK
        SETDATE 7003, 2024, 2, 29, 0
        DATEIS 7004, 2024, 2, 29, 4
        SETDATE 7005, 2023, 2, 29, 0ffh
        SETDATE 7006, 2024, 0, 1, 0ffh
        SETDATE 7007, 2024, 13, 1, 0ffh
        SETDATE 7008, 2024, 4, 31, 0ffh
        SETDATE 7009, 2024, 1, 0, 0ffh
        SETDATE 7010, 1979, 12, 31, 0ffh
        SETDATE 7011, 2100, 1, 1, 0ffh
        DATEIS 7012, 2024, 2, 29, 4
        SETDATE 7013, 1980, 1, 1, 0
        DATEIS 7014, 1980, 1, 1, 2
        SETDATE 7015, 2099, 12, 31, 0
        DATEIS 7016, 2099, 12, 31, 4
        SETDATE 7017, 2024, 2, 28, 0
        SETTIME 7018, 12, 34, 56, 0, 0
        mov ah, 2ch
        DOS 7019
        call valid_time
        cmp cx, (12 << 8) | 34
        jne failure
        ; The native clock has second resolution; conversion may round down.
        cmp dh, 55
        jb failure
        cmp dh, 57
        ja failure
        OK
        SETTIME 7020, 24, 0, 0, 0, 0ffh
        SETTIME 7021, 12, 60, 0, 0, 0ffh
        SETTIME 7022, 12, 34, 60, 0, 0ffh
        SETTIME 7023, 12, 34, 56, 100, 0ffh
        mov ah, 2ch
        DOS 7024
        call valid_time
        cmp cx, (12 << 8) | 34
        jne failure
        OK
        SETTIME 7025, 23, 59, 58, 0, 0
        call wait_midnight
        mov ah, 2ch
        DOS 7026
        call valid_time
        cmp cx, 0
        jne failure
        cmp dh, 10
        ja failure
        OK
        DATEIS 7027, 2024, 2, 29, 4
        SETTIME 7028, 23, 59, 58, 0, 0
        call wait_midnight
        DATEIS 7029, 2024, 3, 1, 5
        SETDATE 7030, 2024, 12, 31, 0
        SETTIME 7031, 23, 59, 58, 0, 0
        call wait_midnight
        DATEIS 7032, 2025, 1, 1, 3
        ; Create a file under a known valid clock, then check its packed date.
        SETDATE 7033, 2024, 2, 29, 0
        SETTIME 7034, 12, 34, 56, 0, 0
        mov ah, 3ch
        xor cx, cx
        mov dx, file_name
        DOS 7035
        CARRY_CLEAR
        mov [handle], ax
        OK
        mov bx, ax
        mov ah, 40h
        mov dx, payload
        mov cx, payload_end-payload
        DOS 7036
        EQUAL_AX payload_end-payload
        mov bx, [handle]
        mov ah, 3eh
        DOS 7037
        SUCCESS
        mov ax, 3d00h
        mov dx, file_name
        DOS 7038
        CARRY_CLEAR
        mov [handle], ax
        OK
        mov bx, ax
        mov ax, 5700h
        DOS 7039
        CARRY_CLEAR
        cmp dx, ((2024-1980) << 9) | (2 << 5) | 29
        jne failure
        mov ax, cx
        and ax, 0ffe0h
        cmp ax, (12 << 11) | (34 << 5)
        jne failure
        and cx, 31
        cmp cx, 27
        jb failure
        cmp cx, 29
        ja failure
        OK
        mov bx, [handle]
        mov ah, 3eh
        DOS 7040
        SUCCESS
        mov cx, [original_year]
        mov dx, [original_md]
        mov ah, 2bh
        DOS 7041
        EQUAL_AL 0
        mov cx, [original_hm]
        mov dx, [original_sh]
        mov ah, 2dh
        DOS 7042
        EQUAL_AL 0
        jmp passed
valid_time:
        cmp ch, 23
        ja failure
        cmp cl, 59
        ja failure
        cmp dh, 59
        ja failure
        cmp dl, 99
        ja failure
        ret
wait_midnight:
        ; Record the checkpoint before a bounded potentially failing wait.
        call save_report
        mov word [poll_high], 64
        mov word [poll_low], 0
.poll:
        mov ah, 2ch
        int 21h
        call valid_time
        cmp ch, 0
        je .done
        dec word [poll_low]
        jnz .poll
        dec word [poll_high]
        jnz .poll
        jmp failure
.done:
        ret
original_year: dw 0
original_md: dw 0
original_hm: dw 0
original_sh: dw 0
poll_high: dw 0
poll_low: dw 0
handle: dw 0
file_name: db 'CLOCK.DAT',0
payload: db 'M15 clock and file timestamp',13,10
payload_end:
result_name: db 'CLOCK.RES',0
%include "harness.inc"
