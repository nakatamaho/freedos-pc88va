; SPDX-License-Identifier: GPL-2.0-or-later
; Standard and extended FCB semantics with a relocated guarded DTA.
; Historical context: Microsoft MS-DOS Encyclopedia, INT21 0F-17,21-24,27-29; preserve FreeDOS behavior.
bits 16
cpu 8086
org 100h
%include "macros.inc"
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        mov dx, buffer
        mov ah, 1ah
        DOS 2001
        OK
        mov ah, 2fh
        DOS 2002
        cmp bx, buffer
        jne failure
        mov ax, cs
        cmp [snapshot+20], ax
        jne failure
        OK
        mov ax, 2900h
        mov si, parse_text
        mov di, parsed
        DOS 2003
        EQUAL_AL 0
        mov si, parsed
        mov di, parsed_expected
        mov cx, 12
        repe cmpsb
        jne failure
        mov ax, 2900h
        mov si, wild_text
        mov di, parsed
        DOS 2004
        EQUAL_AL 1
        mov si, parsed
        mov di, wild_expected
        mov cx, 12
        repe cmpsb
        jne failure
        mov dx, missing_fcb
        mov ah, 0fh
        DOS 2005
        EQUAL_AL 0ffh
        mov dx, fcb
        mov ah, 16h
        DOS 2006
        EQUAL_AL 0
        cmp word [fcb+14], 128
        jne failure
        cmp word [fcb+12], 0
        jne failure
        mov byte [fcb+32], 0
        mov di, buffer
        mov al, 'Q'
        mov cx, 128
        rep stosb
        mov dx, fcb
        mov ah, 15h
        DOS 2007
        EQUAL_AL 0
        cmp byte [fcb+32], 1
        jne failure
        mov di, buffer
        mov al, 'R'
        mov cx, 128
        rep stosb
        mov dx, fcb
        mov ah, 15h
        DOS 2008
        EQUAL_AL 0
        cmp byte [fcb+32], 2
        jne failure
        cmp word [fcb+16], 256
        jne failure
        mov dx, fcb
        mov ah, 10h
        DOS 2009
        EQUAL_AL 0
        ; AH=0Fh requires an unopened FCB: only drive/name/extension remain set.
        ; Use the default-drive code and check the normalized drive and position.
        mov byte [fcb], 0
        mov di, fcb+12
        xor ax, ax
        mov cx, 12
        rep stosw
        mov byte [fcb+36], 0
        mov dx, fcb
        mov ah, 0fh
        DOS 2010
        EQUAL_AL 0
        cmp byte [fcb], 1
        jne failure
        cmp byte [fcb+12], 0
        jne failure
        cmp word [fcb+14], 128
        jne failure
        cmp word [fcb+16], 256
        jne failure
        cmp word [fcb+18], 0
        jne failure
        cmp byte [fcb+32], 0
        jne failure
        OK
        mov dx, fcb
        mov ah, 14h
        DOS 2011
        EQUAL_AL 0
        mov al, 'Q'
        call check_record
        mov dx, fcb
        mov ah, 14h
        DOS 2012
        EQUAL_AL 0
        mov al, 'R'
        call check_record
        mov dx, fcb
        mov ah, 14h
        DOS 2013
        EQUAL_AL 1
        mov word [fcb+12], 0
        mov byte [fcb+32], 1
        mov dx, fcb
        mov ah, 24h
        DOS 2014
        cmp word [fcb+33], 1
        jne failure
        OK
        mov dx, fcb
        mov ah, 21h
        DOS 2015
        EQUAL_AL 0
        cmp word [fcb+33], 1
        jne failure
        mov al, 'R'
        call check_record
        mov di, buffer
        mov cx, 128
        mov al, 'S'
        rep stosb
        mov dx, fcb
        mov ah, 22h
        DOS 2016
        EQUAL_AL 0
        cmp word [fcb+33], 1
        jne failure
        ; Random write addresses the selected record without advancing it.
        ; Read the same record back before changing the record size.
        mov dx, fcb
        mov ah, 21h
        int 21h
        cmp al, 0
        jne failure
        mov al, 'S'
        call check_record
        cmp word [fcb+33], 1
        jne failure
        mov word [fcb+14], 16
        mov word [fcb+33], 0
        mov word [fcb+35], 0
        mov di, buffer
        mov cx, 16
        mov al, 'a'
        rep stosb
        mov cx, 16
        mov al, 'b'
        rep stosb
        mov dx, fcb
        mov cx, 2
        mov ah, 28h
        DOS 2017
        EQUAL_AL 0
        EQUAL_CX 2
        cmp word [fcb+33], 2
        jne failure
        cmp byte [fcb+32], 2
        jne failure
        mov word [fcb+33], 0
        mov dx, fcb
        mov cx, 3
        mov ah, 27h
        DOS 2018
        EQUAL_AL 0
        EQUAL_CX 3
        cmp word [fcb+33], 3
        jne failure
        mov di, buffer
        mov cx, 16
        mov al, 'a'
        repe scasb
        jne failure
        mov cx, 16
        mov al, 'b'
        repe scasb
        jne failure
        mov cx, 16
        mov al, 'Q'
        repe scasb
        jne failure
        mov word [size_fcb+14], 128
        mov dx, size_fcb
        mov ah, 23h
        DOS 2019
        EQUAL_AL 0
        cmp word [size_fcb+33], 2
        jne failure
        mov word [fcb+33], 0
        mov di, buffer
        mov al, 0cch
        mov cx, 16
        rep stosb
        mov dx, fcb
        xor cx, cx
        mov ah, 27h
        DOS 2020
        ; The reference promises no data is read for CX=0, but does not
        ; define AL here. Verify the DTA stays untouched; leave AL unasserted.
        mov di, buffer
        mov al, 0cch
        mov cx, 16
        repe scasb
        jne failure
        OK
        mov word [fcb+33], 4
        mov dx, fcb
        xor cx, cx
        mov ah, 28h
        DOS 2021
        EQUAL_AL 0
        EQUAL_CX 0
        cmp word [fcb+16], 64
        jne failure
        mov dx, fcb
        mov ah, 10h
        DOS 2022
        EQUAL_AL 0
        ; Reopen the existing file from a valid, unopened standard FCB.
        mov byte [fcb], 0
        mov di, fcb+12
        xor ax, ax
        mov cx, 12
        rep stosw
        mov byte [fcb+36], 0
        mov dx, fcb
        mov ah, 0fh
        DOS 2023
        EQUAL_AL 0
        cmp byte [fcb], 1
        jne failure
        cmp byte [fcb+12], 0
        jne failure
        cmp word [fcb+14], 128
        jne failure
        cmp word [fcb+16], 64
        jne failure
        cmp word [fcb+18], 0
        jne failure
        cmp byte [fcb+32], 0
        jne failure
        OK
        mov byte [fcb+32], 0
        mov di, buffer
        mov cx, 128
        mov al, 0a5h
        rep stosb
        mov dx, fcb
        mov ah, 14h
        DOS 2024
        EQUAL_AL 3
        cmp byte [fcb+32], 1
        jne failure
        mov di, buffer+64
        xor al, al
        mov cx, 64
        repe scasb
        jne failure
        mov word [fcb+14], 0ffffh
        mov dx, fcb
        mov ah, 14h
        DOS 2025
        EQUAL_AL 2
        cmp byte [fcb+32], 1
        jne failure
        cmp word [buffer-2], 0a55ah
        jne failure
        cmp word [buffer+256], 05aa5h
        jne failure
        mov word [fcb+14], 128
        mov dx, fcb
        mov ah, 10h
        DOS 2026
        EQUAL_AL 0
        mov dx, rename_fcb
        mov ah, 17h
        DOS 2027
        EQUAL_AL 0
        mov si, search_fcb
        mov di, search_snapshot
        mov cx, 6
        rep movsw
        mov di, buffer
        mov al, 0cch
        mov cx, 33
        rep stosb
        ; A DOS 1.x-compatible '?' pattern matches ordinary 8.3 files.
        ; Keep the search FCB unchanged across both calls.
        mov dx, search_fcb
        mov ah, 11h
        DOS 2028
        EQUAL_AL 0
        cmp byte [buffer], 1
        jne failure
        cmp byte [buffer+1], 0
        je failure
        cmp byte [buffer+1], ' '
        je failure
        mov si, buffer+1
        mov di, first_search_name
        mov cx, 11
        rep movsb
        mov si, search_fcb
        mov di, search_snapshot
        mov cx, 6
        repe cmpsw
        jne failure
        OK
        mov dx, search_fcb
        mov ah, 12h
        DOS 2029
        EQUAL_AL 0
        cmp byte [buffer], 1
        jne failure
        mov si, buffer+1
        mov di, first_search_name
        mov cx, 11
        repe cmpsb
        je failure
        mov si, search_fcb
        mov di, search_snapshot
        mov cx, 6
        repe cmpsw
        jne failure
        OK
        mov dx, extended_fcb
        mov ah, 16h
        DOS 2030
        EQUAL_AL 0
        mov byte [extended_fcb+7+32], 0
        mov di, buffer
        mov al, 'X'
        mov cx, 128
        rep stosb
        mov dx, extended_fcb
        mov ah, 15h
        DOS 2031
        EQUAL_AL 0
        mov dx, extended_fcb
        mov ah, 10h
        DOS 2032
        EQUAL_AL 0
        mov dx, extended_name
        mov ax, 4300h
        DOS 2033
        CARRY_CLEAR
        test cx, 2
        jz failure
        OK
        mov dx, extended_fcb
        mov ah, 13h
        DOS 2034
        EQUAL_AL 0
        mov dx, deleted_fcb
        mov ah, 0fh
        DOS 2035
        EQUAL_AL 0ffh
        mov dx, renamed_name
        mov ax, 3d00h
        DOS 2036
        jc failure
        mov [h1], ax
        OK
        mov bx, [h1]
        mov dx, buffer
        mov cx, 128
        mov ah, 3fh
        DOS 2037
        EQUAL_AX 64
        mov di, buffer
        mov cx, 16
        mov al, 'a'
        repe scasb
        jne failure
        mov cx, 16
        mov al, 'b'
        repe scasb
        jne failure
        mov cx, 32
        mov al, 'Q'
        repe scasb
        jne failure
        mov bx, [h1]
        mov ah, 3eh
        DOS 2038
        SUCCESS
        mov dx, delete_fcb
        mov ah, 16h
        DOS 2039
        EQUAL_AL 0
        mov dx, delete_fcb
        mov ah, 10h
        DOS 2040
        EQUAL_AL 0
        mov dx, delete_fcb
        mov ah, 13h
        DOS 2041
        EQUAL_AL 0
        mov dx, delete_fcb
        mov ah, 13h
        DOS 2042
        EQUAL_AL 0ffh
        ; AH=16h on an existing ordinary file must truncate it to zero bytes.
        mov dx, truncate_fcb
        mov ah, 16h
        DOS 2043
        EQUAL_AL 0
        cmp byte [truncate_fcb], 1
        jne failure
        cmp byte [truncate_fcb+12], 0
        jne failure
        cmp word [truncate_fcb+14], 128
        jne failure
        cmp word [truncate_fcb+16], 0
        jne failure
        cmp word [truncate_fcb+18], 0
        jne failure
        cmp byte [truncate_fcb+32], 0
        jne failure
        OK
        mov dx, truncate_fcb
        mov ah, 10h
        DOS 2044
        EQUAL_AL 0
        jmp passed
check_record:
        mov di, buffer
        mov cx, 128
        repe scasb
        jne failure
        ret
h1: dw 0
parse_text: db 'a:fcb.dat rest',0
parsed_expected: db 1,'FCB     DAT'
wild_text: db 'FC*.D?',0
wild_expected: db 0,'FC??????D? '
parsed: times 37 db 0
fcb: db 0,'FCBA    DAT'
        times 25 db 0
size_fcb: db 0,'FCBA    DAT'
        times 25 db 0
missing_fcb: db 0,'NOFCB   XYZ'
        times 25 db 0
deleted_fcb: db 0,'XFCB    DAT'
        times 25 db 0
rename_fcb: db 0,'FCBA    DAT'
        times 5 db 0
        db 'FCBR    DAT'
        times 9 db 0
search_fcb: db 0,'???????????'
        times 25 db 0
search_snapshot: times 12 db 0
first_search_name: times 11 db 0
extended_fcb: db 0ffh,0,0,0,0,0,2,0,'XFCB    DAT'
        times 25 db 0
delete_fcb: db 0,'FCBDEL  DAT'
        times 25 db 0
renamed_name: db 'FCBR.DAT',0
extended_name: db 'XFCB.DAT',0
truncate_fcb: db 0,'FCBR    DAT'
        times 25 db 0
        dw 0a55ah
buffer: times 256 db 0cch
        dw 05aa5h
result_name: db 'FCB.RES',0
%include "harness.inc"
