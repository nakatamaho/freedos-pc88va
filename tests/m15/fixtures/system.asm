; SPDX-License-Identifier: GPL-2.0-or-later
; Local DOS state, vector, ASCII NLS and capability contracts.
; No physical devices, alternate codepages or undocumented memory writes.
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
        mov ax, 3000h
        DOS 5001
        or al, al
        jz failure
        mov [reported_version], ax
        mov [reported_oem_serial], bh
        mov [reported_user_serial], bl
        mov [reported_user_serial+1], cx
        ; The version and OEM/user serial values are runtime-dependent. Check
        ; all documented return fields for stability across an unchanged query.
        mov ax, 3000h
        int 21h
        cmp ax, [reported_version]
        jne failure
        cmp bh, [reported_oem_serial]
        jne failure
        cmp bl, [reported_user_serial]
        jne failure
        cmp cx, [reported_user_serial+1]
        jne failure
        OK
        mov ax, 3001h
        DOS 5002
        cmp ax, [reported_version]
        jne failure
        test bh, 10h                 ; This profile does not run DOS in HMA.
        jnz failure
        OK
        mov ax, 3306h
        DOS 5003
        cmp bl, 5
        jb failure
        test dl, 0f8h
        jnz failure
        test dh, 18h
        jnz failure
        OK
        mov ax, 3305h
        DOS 5004
        cmp dl, 1
        jne failure
        OK
        mov ax, 3300h
        DOS 5005
        cmp dl, 1
        ja failure
        mov [old_break], dl
        OK
        mov dl, 1
        mov ax, 3301h
        DOS 5006
        OK
        mov ax, 3300h
        DOS 5007
        cmp dl, 1
        jne failure
        OK
        xor dl, dl
        mov ax, 3302h
        DOS 5008
        cmp dl, 1
        jne failure
        OK
        mov ax, 3300h
        DOS 5009
        or dl, dl
        jnz failure
        OK
        mov dl, [old_break]
        mov ax, 3301h
        DOS 5010
        OK
        mov ax, 3303h
        DOS 5011
        EQUAL_AL 0ffh
        ; Exercise AL=01h with both documented states, independent of its entry state.
        xor dl, dl
        mov ax, 3301h
        DOS 5055
        OK
        mov ax, 3300h
        DOS 5056
        or dl, dl
        jnz failure
        OK
        mov dl, [old_break]
        mov ax, 3301h
        DOS 5057
        OK
        mov ax, 3300h
        DOS 5058
        cmp dl, [old_break]
        jne failure
        OK
        mov ax, 33ffh
        DOS 5012
        mov es, dx
        mov bx, ax
        mov cx, 256
.release_string:
        cmp byte [es:bx], 0
        je .release_found
        inc bx
        loop .release_string
        jmp failure
.release_found:
        cmp cx, 256
        je failure
        push cs
        pop es
        OK
        mov ah, 54h
        DOS 5013
        cmp al, 1
        ja failure
        mov [old_verify], al
        OK
        mov ax, 2e01h
        xor dx, dx
        DOS 5014
        OK
        mov ah, 54h
        DOS 5015
        EQUAL_AL 1
        mov ax, 2e00h
        DOS 5016
        OK
        mov ah, 54h
        DOS 5017
        EQUAL_AL 0
        mov al, [old_verify]
        mov ah, 2eh
        DOS 5018
        OK
        mov ax, 3560h
        DOS 5019
        mov [old_vector], bx
        mov ax, [snapshot+20]
        mov [old_vector+2], ax
        OK
        mov dx, vector_handler
        mov ax, 2560h
        DOS 5020
        OK
        mov ax, 3560h
        DOS 5021
        cmp bx, vector_handler
        jne failure
        mov ax, cs
        cmp [snapshot+20], ax
        jne failure
        OK
        int 60h
        cmp word [vector_hits], 1
        jne failure
        mov dx, [old_vector]
        mov ds, [old_vector+2]
        mov ax, 2560h
        DOS 5022
        OK
        mov ax, 3560h
        DOS 5023
        cmp bx, [old_vector]
        jne failure
        mov ax, [snapshot+20]
        cmp ax, [old_vector+2]
        jne failure
        OK
        mov ah, 34h
        DOS 5024
        mov es, [snapshot+20]
        cmp byte [es:bx], 0
        jne failure
        push cs
        pop es
        OK
        mov ax, 3700h
        DOS 5025
        mov [old_switch], dl
        OK
        mov dl, '-'
        mov ax, 3701h
        DOS 5026
        OK
        mov ax, 3700h
        DOS 5027
        cmp dl, '-'
        jne failure
        OK
        mov dl, [old_switch]
        mov ax, 3701h
        DOS 5028
        OK
        mov ax, 3700h
        DOS 5059
        cmp dl, [old_switch]
        jne failure
        OK
        mov ax, 6520h
        mov dl, 'q'
        DOS 5029
        CARRY_CLEAR
        cmp dl, 'Q'
        jne failure
        OK
        mov ax, 6521h
        mov cx, 4
        mov dx, counted
        DOS 5030
        CARRY_CLEAR
        cmp word [counted], 'AZ'
        jne failure
        cmp word [counted+2], '19'
        jne failure
        cmp byte [counted+4], 'z'
        jne failure
        OK
        mov ax, 6522h
        mov dx, terminated
        DOS 5031
        CARRY_CLEAR
        cmp word [terminated], 'HI'
        jne failure
        cmp word [terminated+2], 0
        jne failure
        cmp byte [terminated+4], 'x'
        jne failure
        OK
        mov ax, 65a0h
        mov dl, 'm'
        DOS 5032
        CARRY_CLEAR
        cmp dl, 'M'
        jne failure
        OK
        mov ax, 65a1h
        mov dx, counted_file
        mov cx, 4
        DOS 5033
        CARRY_CLEAR
        cmp word [counted_file], 'AB'
        jne failure
        cmp word [counted_file+2], 'CD'
        jne failure
        cmp byte [counted_file+4], 'e'
        jne failure
        OK
        mov ax, 65a2h
        mov dx, filename
        DOS 5034
        CARRY_CLEAR
        cmp word [filename], 'FD'
        jne failure
        cmp word [filename+2], '.C'
        jne failure
        OK
        mov ax, 6523h
        mov dl, 'y'
        DOS 5035
        EQUAL_AX 1
        mov ax, 6523h
        mov dl, 'N'
        DOS 5036
        EQUAL_AX 0
        mov ax, 6523h
        mov dl, '?'
        DOS 5037
        EQUAL_AX 2
        mov ax, 6601h
        DOS 5038
        CARRY_CLEAR
        mov [codepage], bx
        or bx, bx
        jz failure
        or dx, dx
        jz failure
        OK
        mov ax, 3800h
        mov dx, country
        DOS 5039
        CARRY_CLEAR
        or bx, bx
        jz failure
        mov [country_id], bx
        cmp word [country], 2
        ja failure
        OK
        mov ax, 6501h
        mov bx, 0ffffh
        mov dx, 0ffffh
        mov cx, 41
        mov di, extended
        DOS 5040
        CARRY_CLEAR
        cmp byte [extended], 1
        jne failure
        mov ax, [country_id]
        cmp [extended+3], ax
        jne failure
        mov ax, [codepage]
        cmp [extended+5], ax
        jne failure
        OK
        mov ax, 6501h
        mov bx, 0ffffh
        mov dx, 0ffffh
        mov cx, 1
        mov di, extended
        DOS 5041
        ERROR 1
        mov ax, 6500h
        mov bx, 0ffffh
        mov dx, 0ffffh
        mov cx, 41
        mov di, extended
        DOS 5042
        ERROR 1
        mov ax, 6300h
        DOS 5043
        mov es, [snapshot+18]
        cmp word [es:si], 0          ; No DBCS lead bytes in ASCII profile.
        jne failure
        push cs
        pop es
        OK
        mov ax, 6301h
        DOS 5044
        EQUAL_AL 0ffh
        mov ax, 6302h
        DOS 5045
        EQUAL_AL 0ffh
        cmp word [country-2], 0a55ah
        jne failure
        cmp word [country+34], 05aa5h
        jne failure
        cmp word [extended-2], 0a55ah
        jne failure
        cmp word [extended+41], 05aa5h
        jne failure
        ; Retain an incomplete checkpoint before exercising the absent NLS
        ; provider path. A hang or missing final record cannot pass.
        call save_report
        mov ax, 38ffh
        mov bx, 0fffeh
        mov dx, country
        DOS 5046
        ; The selected FreeDOS NLS MUX path returns DE_INVLDFUNC (AX=1) when
        ; this explicit country package is not loaded; do not impose an
        ; MS-DOS reference error value on the port.
        ERROR 1
        mov ax, 5900h
        xor bx, bx
        DOS 5047
        ; AH=59h returns the preserved FreeDOS CritErrCode from the preceding
        ; missing-country-package request.
        cmp ax, 1
        jne failure
        OK
        mov ax, 3800h
        mov dx, country
        DOS 5048
        CARRY_CLEAR
        cmp bx, [country_id]
        jne failure
        OK
        mov ax, 38ffh
        mov bx, [country_id]
        mov dx, 0ffffh
        DOS 5049
        SUCCESS
        mov ax, 38ffh
        mov bx, 0fffeh
        mov dx, 0ffffh
        DOS 5050
        ERROR 2
        mov ax, 6601h
        DOS 5051
        CARRY_CLEAR
        cmp bx, [codepage]
        jne failure
        OK
        mov ax, 6602h
        mov bx, [codepage]
        DOS 5052
        ; Global code-page switching requires the absent NLSFUNC provider.
        ; DOS documents file-not-found when the required package is unavailable.
        ERROR 2
        mov ax, 6601h
        DOS 5053
        CARRY_CLEAR
        cmp bx, [codepage]
        jne failure
        OK
        cmp word [country-2], 0a55ah
        jne failure
        cmp word [country+34], 05aa5h
        jne failure
        jmp passed
vector_handler:
        inc word [cs:vector_hits]
        iret
reported_version: dw 0
reported_oem_serial: db 0
reported_user_serial: db 0,0,0
old_break: db 0
old_verify: db 0
old_switch: db 0
old_vector: dd 0
vector_hits: dw 0
codepage: dw 0
country_id: dw 0
counted: db 'az19z'
terminated: db 'hi',0,0,'x'
counted_file: db 'abcde'
filename: db 'fd.c',0
        dw 0a55ah
country: times 34 db 0cch
        dw 05aa5h, 0a55ah
extended: times 41 db 0cch
        dw 05aa5h
result_name: db 'SYSTEM.RES',0
%include "harness.inc"
