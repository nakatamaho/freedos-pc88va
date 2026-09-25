; SPDX-License-Identifier: GPL-2.0-or-later
; Original short-name conformance for the DOS 7.20 43FF path aliases.
; This does not qualify extended-length names or LFN behavior.
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

        mov dx, alias_dir
        mov ax, 43ffh
        mov bp, 5053h
        mov cl, 39h
        DOS 3061
        SUCCESS

        mov dx, alias_dir
        mov ah, 3bh
        DOS 3062
        SUCCESS
        xor dx, dx
        mov si, cwd
        mov ah, 47h
        DOS 3063
        CARRY_CLEAR
        mov si, cwd
        mov di, alias_dir
        call same_string
        OK
        mov dx, root_dir
        mov ah, 3bh
        DOS 3064
        SUCCESS

        mov dx, alias_dir
        mov ax, 43ffh
        mov bp, 5053h
        mov cl, 39h
        DOS 3065
        ERROR 5

        ; The pinned handler forwards CL=3Ah to the common RMDIR service.
        ; Keep this as an undocumented observation, separate from the
        ; documented 43FFh mkdir and rename subfunctions.
        mov dx, alias_dir
        mov ax, 43ffh
        mov bp, 5053h
        mov cl, 3ah
        DOS 3066
        SUCCESS
        mov dx, alias_dir
        mov ax, 43ffh
        mov bp, 5053h
        mov cl, 3ah
        DOS 3067
        ERROR 3

        mov dx, source_name
        xor cx, cx
        mov ah, 3ch
        DOS 3068
        CARRY_CLEAR
        mov [handle], ax
        OK
        mov bx, [handle]
        mov ah, 3eh
        DOS 3069
        SUCCESS

        mov dx, source_name
        mov di, target_name
        mov ax, 43ffh
        mov bp, 5053h
        mov cl, 56h
        DOS 3070
        SUCCESS
        mov dx, source_name
        mov ax, 3d00h
        DOS 3071
        ERROR 2
        mov dx, target_name
        mov ax, 3d00h
        DOS 3072
        CARRY_CLEAR
        mov [handle], ax
        OK
        mov bx, [handle]
        mov ah, 3eh
        DOS 3073
        SUCCESS

        mov dx, occupied_name
        xor cx, cx
        mov ah, 3ch
        DOS 3074
        CARRY_CLEAR
        mov [handle], ax
        OK
        mov bx, [handle]
        mov ah, 3eh
        DOS 3075
        SUCCESS

        mov dx, target_name
        mov di, occupied_name
        mov ax, 43ffh
        mov bp, 5053h
        mov cl, 56h
        DOS 3076
        ERROR 5
        mov dx, missing_name
        mov di, target_name
        mov ax, 43ffh
        mov bp, 5053h
        mov cl, 56h
        DOS 3077
        ERROR 2

        ; Verify both names survived the rejected destination-exists rename.
        mov dx, target_name
        mov ax, 3d00h
        DOS 3078
        CARRY_CLEAR
        mov [handle], ax
        OK
        mov bx, [handle]
        mov ah, 3eh
        DOS 3079
        SUCCESS
        mov dx, occupied_name
        mov ax, 3d00h
        DOS 3080
        CARRY_CLEAR
        mov [handle], ax
        OK
        mov bx, [handle]
        mov ah, 3eh
        DOS 3081
        SUCCESS

        mov dx, target_name
        mov ah, 41h
        DOS 3082
        SUCCESS
        mov dx, occupied_name
        mov ah, 41h
        DOS 3083
        SUCCESS
        jmp passed

same_string:
        mov al, [si]
        cmp al, [di]
        jne failure
        inc si
        inc di
        or al, al
        jnz same_string
        ret

alias_dir: db 'ALIASDIR',0
root_dir: db '\',0
source_name: db 'ALIAS1.TXT',0
target_name: db 'ALIAS2.TXT',0
occupied_name: db 'ALIAS3.TXT',0
missing_name: db 'MISSING.TXT',0
cwd: times 64 db 0cch
handle: dw 0
result_name: db 'ALIAS.RES',0
%include "harness.inc"
