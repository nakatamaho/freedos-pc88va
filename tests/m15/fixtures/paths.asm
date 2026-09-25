; SPDX-License-Identifier: GPL-2.0-or-later
; Original path and independent-DTA tests. Historical context: Microsoft MS-DOS
; Encyclopedia System Calls 0E,19,1A,2F,36,39-3B,47,4E,4F,56,60; preserve FreeDOS behavior.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%macro CREATE 3
        mov dx, %1
        xor cx, cx
        mov ah, 3ch
        DOS %2
        jc failure
        mov bx, ax
        OK
        mov ah, 3eh
        DOS %3
        SUCCESS
%endmacro
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        mov ah, 19h
        DOS 3001
        EQUAL_AL 0
        xor dx, dx
        mov ah, 0eh
        DOS 3002
        cmp al, 1
        jb failure
        OK
        xor dx, dx
        mov ah, 36h
        DOS 3003
        cmp ax, 0ffffh
        je failure
        or ax, ax
        jz failure
        cmp cx, 1024
        jne failure
        cmp bx, dx
        ja failure
        OK
        mov dl, 27
        mov ah, 36h
        DOS 3004
        cmp ax, 0ffffh
        jne failure
        OK
        mov dx, missing_parent
        mov ah, 39h
        DOS 3005
        ERROR 3
        mov dx, parent_dir
        mov ah, 39h
        DOS 3006
        SUCCESS
        mov dx, parent_dir
        mov ah, 39h
        DOS 3007
        ERROR 5
        mov dx, lowercase_dir
        mov ah, 3bh
        DOS 3008
        SUCCESS
        xor dx, dx
        mov si, cwd
        mov ah, 47h
        DOS 3009
        CARRY_CLEAR
        mov si, cwd
        mov di, parent_dir
        call same_string
        OK
        CREATE one, 3010, 3011
        CREATE two, 3012, 3013
        CREATE other, 3014, 3015
        mov dx, hidden
        mov cx, 2
        mov ah, 3ch
        DOS 3016
        jc failure
        mov bx, ax
        OK
        mov ah, 3eh
        DOS 3017
        SUCCESS
        mov dx, child_dir
        mov ah, 39h
        DOS 3018
        SUCCESS
        mov dx, dta_a
        mov ah, 1ah
        DOS 3019
        OK
        xor cx, cx
        mov dx, txt_pattern
        mov ah, 4eh
        DOS 3020
        SUCCESS
        mov si, dta_a+30
        mov di, first_name
        mov cx, 13
        rep movsb
        mov dx, dta_b
        mov ah, 1ah
        DOS 3021
        OK
        xor cx, cx
        mov dx, bin_pattern
        mov ah, 4eh
        DOS 3022
        CARRY_CLEAR
        mov si, dta_b+30
        mov di, other
        call same_string
        OK
        mov dx, dta_a
        mov ah, 1ah
        DOS 3023
        OK
        mov ah, 4fh
        DOS 3024
        CARRY_CLEAR
        mov si, dta_a+30
        mov di, first_name
        mov cx, 13
        repe cmpsb
        je failure
        ; Exactly the two original TXT names, independent of enumeration order.
        mov si, first_name
        cmp byte [si], 'O'
        jne .two_first
        mov di, one
        call same_string
        mov si, dta_a+30
        mov di, two
        jmp .second
.two_first:
        mov di, two
        call same_string
        mov si, dta_a+30
        mov di, one
.second:
        call same_string
        OK
        mov ah, 4fh
        DOS 3025
        ERROR 18
        mov dx, dta_b
        mov ah, 1ah
        DOS 3026
        OK
        mov ah, 4fh
        DOS 3027
        ERROR 18
        mov dx, no_pattern
        xor cx, cx
        mov ah, 4eh
        DOS 3028
        ; Function 4E documents both file-not-found and no-match errors.
        call search_absent
        mov dx, hidden
        xor cx, cx
        mov ah, 4eh
        DOS 3029
        call search_absent
        mov dx, hidden
        mov cx, 2
        mov ah, 4eh
        DOS 3030
        CARRY_CLEAR
        test byte [dta_b+21], 2
        jz failure
        OK
        mov dx, child_dir
        mov cx, 10h
        mov ah, 4eh
        DOS 3031
        CARRY_CLEAR
        test byte [dta_b+21], 10h
        jz failure
        OK
        mov si, relative_one
        mov di, canonical
        mov ah, 60h
        DOS 3032
        CARRY_CLEAR
        mov si, canonical
        mov di, absolute_one
        call same_string
        OK
        mov dx, drive_one
        mov ax, 3d00h
        DOS 3033
        jc failure
        mov bx, ax
        OK
        mov ah, 3eh
        DOS 3034
        SUCCESS
        mov dx, one
        mov di, two
        mov ah, 56h
        DOS 3035
        ERROR 5
        mov dx, one
        mov di, moved_one
        mov ah, 56h
        DOS 3036
        SUCCESS
        mov dx, one
        mov ax, 3d00h
        DOS 3037
        ERROR 2
        mov dx, moved_one
        mov ax, 3d00h
        DOS 3038
        jc failure
        mov bx, ax
        OK
        mov ah, 3eh
        DOS 3039
        SUCCESS
        mov dx, child_dir
        mov ah, 3ah
        DOS 3040
        ERROR 5
        mov dx, nested_dot
        mov ah, 3bh
        DOS 3041
        SUCCESS
        xor dx, dx
        mov si, cwd
        mov ah, 47h
        DOS 3042
        CARRY_CLEAR
        mov si, cwd
        mov di, parent_dir
        call same_string
        OK
        mov dx, moved_one
        mov ah, 41h
        DOS 3043
        SUCCESS
        mov dx, child_dir
        mov ah, 3ah
        DOS 3044
        SUCCESS
        mov dx, child_dir
        mov ah, 3bh
        DOS 3045
        ERROR 3
        mov dx, root_dir
        mov ah, 3bh
        DOS 3046
        SUCCESS
        xor dx, dx
        mov si, cwd
        mov ah, 47h
        DOS 3047
        CARRY_CLEAR
        cmp byte [cwd], 0
        jne failure
        OK
        mov dx, parent_dir
        mov ah, 3ah
        DOS 3048
        ERROR 5
        mov dx, removed_absolute
        mov di, impossible_rename
        mov ah, 56h
        DOS 3049
        ERROR 2
        mov dl, 27
        mov si, cwd
        mov ah, 47h
        DOS 3050
        ERROR 15
        cmp word [dta_a-2], 0a55ah
        jne failure
        cmp word [dta_a+43], 05aa5h
        jne failure
        cmp word [dta_b-2], 0a55ah
        jne failure
        cmp word [dta_b+43], 05aa5h
        jne failure
        cmp word [canonical-2], 0a55ah
        jne failure
        cmp word [canonical+128], 05aa5h
        jne failure
        jmp passed
search_absent:
        jnc failure
        cmp ax, 2
        je .valid
        cmp ax, 18
        jne failure
.valid:
        OK
        ret
same_string:
        mov al, [si]
        cmp al, [di]
        jne failure
        inc si
        inc di
        or al, al
        jnz same_string
        ret
parent_dir: db 'PATHA',0
lowercase_dir: db 'patha',0
child_dir: db 'SUB',0
missing_parent: db 'MISSING\CHILD',0
one: db 'ONE.TXT',0
two: db 'TWO.TXT',0
other: db 'OTHER.BIN',0
hidden: db 'HIDDEN.DAT',0
txt_pattern: db '*.TXT',0
bin_pattern: db '*.BIN',0
no_pattern: db '*.ZZZ',0
relative_one: db '.\ONE.TXT',0
absolute_one: db 'A:\PATHA\ONE.TXT',0
drive_one: db 'a:one.txt',0
moved_one: db 'SUB\ONE.TXT',0
nested_dot: db 'SUB\..\.',0
root_dir: db '\',0
removed_absolute: db 'A:\PATHA\ONE.TXT',0
impossible_rename: db 'A:\PATHA\NEW.TXT',0
first_name: times 13 db 0
        dw 0a55ah
dta_a: times 43 db 0cch
        dw 05aa5h, 0a55ah
dta_b: times 43 db 0cch
        dw 05aa5h
cwd: times 64 db 0cch
        dw 0a55ah
canonical: times 128 db 0cch
        dw 05aa5h
result_name: db 'PATHS.RES',0
%include "harness.inc"
