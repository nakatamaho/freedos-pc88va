; SPDX-License-Identifier: GPL-2.0-or-later
; DOS 5 IOCTL packet layouts and independently specified FAT12 boot fields.
; Run only on a disposable copy. Restore the complete original boot sector.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%define M15_FAILURE_HOOK restore_state
%define M15_ABSOLUTE_IO 1
%macro ABS 2
        mov byte [cs:absolute_interrupt], %1
        DOS %2
        mov byte [cs:absolute_interrupt], 0
%endmacro
%macro IOCTL 3
        mov bx, 1
        mov cx, %2
        mov dx, %3
        mov ax, 440dh
        DOS %1
%endmacro
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        mov ax, cs
        mov [rw+11], ax
        mov [packet+8], ax
        mov ah, 0dh
        DOS 23001
        OK
        mov bx, 1
        mov cx, 25
        mov dx, mid
        mov ax, 4404h
        DOS 23002
        ERROR 1
        mov ax, 4405h
        DOS 23003
        ERROR 1
        IOCTL 23010, 0860h, params
        SUCCESS
        call check_geometry
        mov byte [params], 1
        IOCTL 23011, 0860h, params
        SUCCESS
        call check_geometry
        IOCTL 23012, 0840h, params
        SUCCESS
        IOCTL 23013, 0860h, params
        SUCCESS
        call check_geometry
        IOCTL 23019, 0861h, rw
        SUCCESS
        cmp word [original+11], 1024
        jne failure
        cmp byte [original+26h], 29h
        jne failure
        mov si, original
        mov di, modified
        mov cx, 512
        rep movsw
        IOCTL 23020, 0866h, mid
        SUCCESS
        call check_mid
        mov bx, 1
        mov dx, mid
        mov ax, 6900h
        DOS 23021
        SUCCESS
        call check_mid
        xor word [modified+27h], 1234h
        call prepare_mid
        mov byte [media_changed], 1
        IOCTL 23022, 0846h, mid
        SUCCESS
        mov word [rw+9], readback
        IOCTL 23023, 0861h, rw
        SUCCESS
        call compare_sector
        IOCTL 23024, 0866h, mid
        SUCCESS
        call check_mid
        xor word [modified+29h], 5678h
        call prepare_mid
        mov bx, 1
        mov dx, mid
        mov ax, 6901h
        DOS 23025
        SUCCESS
        mov bx, 1
        mov dx, mid
        mov ax, 6900h
        DOS 23026
        SUCCESS
        call check_mid
        IOCTL 23027, 0861h, rw
        SUCCESS
        call compare_sector
        ; The raw track writer restores all bytes, including both serial words.
        mov word [rw+9], original
        IOCTL 23028, 0841h, rw
        SUCCESS
        mov si, original
        mov di, modified
        mov cx, 512
        rep movsw
        mov word [rw+9], readback
        IOCTL 23029, 0861h, rw
        SUCCESS
        call compare_sector
        IOCTL 23030, 0866h, mid
        SUCCESS
        call check_mid
        IOCTL 23035, 0862h, verify
        SUCCESS
        ; Absolute writes must also refresh the DOS metadata-query result.
        xor word [modified+27h], 1357h
        xor ax, ax
        mov bx, modified
        mov cx, 1
        xor dx, dx
        ABS 26h, 23036
        ; Set Device Parameters marks the media changed. The accepted M14
        ; binding rule rejects this old request before writing any byte.
        ERROR 8102h
        call check_stack
        IOCTL 23046, 0861h, rw
        SUCCESS
        mov si, original
        mov di, readback
        mov cx, 1024
        repe cmpsb
        jne failure
        ; A new pathname operation establishes the new media binding.
        mov dx, existing_file
        mov ax, 3d00h
        DOS 23047
        CARRY_CLEAR
        mov bx, ax
        OK
        mov ah, 3eh
        DOS 23048
        SUCCESS
        mov ah, 0dh
        DOS 23049
        OK
        xor ax, ax
        mov bx, modified
        mov cx, 1
        xor dx, dx
        ABS 26h, 23050
        SUCCESS
        call check_stack
        mov ah, 0dh
        DOS 23037
        OK
        IOCTL 23038, 0866h, mid
        SUCCESS
        call check_mid
        mov word [packet+6], readback
        xor ax, ax
        mov bx, packet
        mov cx, 0ffffh
        ABS 25h, 23039
        SUCCESS
        call check_stack
        call compare_sector
        xor word [modified+29h], 2468h
        mov word [packet+6], modified
        xor ax, ax
        mov bx, packet
        mov cx, 0ffffh
        ABS 26h, 23040
        SUCCESS
        call check_stack
        xor ax, ax
        mov bx, readback
        mov cx, 1
        xor dx, dx
        ABS 25h, 23041
        SUCCESS
        call check_stack
        call compare_sector
        mov bx, 1
        mov dx, mid
        mov ax, 6900h
        DOS 23042
        SUCCESS
        call check_mid
        mov word [packet+6], original
        xor ax, ax
        mov bx, packet
        mov cx, 0ffffh
        ABS 26h, 23043
        SUCCESS
        call check_stack
        mov si, original
        mov di, modified
        mov cx, 512
        rep movsw
        mov ah, 0dh
        DOS 23044
        OK
        IOCTL 23045, 0866h, mid
        SUCCESS
        call check_mid
        mov byte [media_changed], 0
        mov bx, 26
        mov dx, mid
        mov ax, 6900h
        DOS 23031
        ERROR 15
        mov bx, 1
        mov ax, 6902h
        DOS 23032
        ERROR 1
        IOCTL 23033, 09ffh, mid
        ; The category is outside this target's block-device contract; only
        ; the carry result is defined for this unsupported category probe.
        jnc failure
        OK
        IOCTL 23034, 08ffh, mid
        ; Keep the FreeDOS error value as an observation; require failure only.
        ERROR_ANY
        cmp word [mid-2], 0a55ah
        jne failure
        cmp word [mid+25], 05aa5h
        jne failure
        cmp word [params-2], 0a55ah
        jne failure
        cmp word [params+32], 05aa5h
        jne failure
        cmp word [rw-2], 0a55ah
        jne failure
        cmp word [rw+13], 05aa5h
        jne failure
        cmp word [original-2], 0a55ah
        jne failure
        cmp word [original+1024], 05aa5h
        jne failure
        cmp word [readback-2], 0a55ah
        jne failure
        cmp word [readback+1024], 05aa5h
        jne failure
        cmp word [packet-2], 0a55ah
        jne failure
        cmp word [packet+10], 05aa5h
        jne failure
        ; Keep this known provider-dependent case last so block results remain
        ; observable without weakening its DOS 4 contract.
        mov cx, 1
        mov dx, 1
        mov ax, 440bh
        DOS 23004
        ; DOS 4 requires SHARE for retry configuration; it is absent in M15.
        ERROR 1
        jmp passed
check_stack:
        mov ax, [absolute_sp]
        add ax, 2
        cmp ax, [call_sp]
        jne failure
        ret
check_geometry:
        cmp word [params+4], 80
        jne failure
        cmp word [params+7], 1024
        jne failure
        cmp byte [params+9], 1
        jne failure
        cmp word [params+10], 1
        jne failure
        cmp byte [params+12], 2
        jne failure
        cmp word [params+13], 192
        jne failure
        cmp word [params+15], 1280
        jne failure
        cmp byte [params+17], 0feh
        jne failure
        cmp word [params+18], 2
        jne failure
        cmp word [params+20], 8
        jne failure
        cmp word [params+22], 2
        jne failure
        ret
prepare_mid:
        mov si, modified+27h
        mov di, mid+2
        mov cx, 23
        rep movsb
        ret
check_mid:
        mov si, modified+27h
        mov di, mid+2
        mov cx, 23
        repe cmpsb
        jne failure
        ret
compare_sector:
        mov si, modified
        mov di, readback
        mov cx, 1024
        repe cmpsb
        jne failure
        ret
restore_state:
        push cs
        pop ds
.media:
        cmp byte [media_changed], 0
        je .done
        mov word [rw+9], original
        mov bx, 1
        mov cx, 0841h
        mov dx, rw
        mov ax, 440dh
        int 21h
.done:
        push cs
        pop es
        ret
media_changed: db 0
existing_file: db 'TYPEA.TXT',0
verify: db 0
        dw 0,0,1
        dw 0a55ah
packet: dd 0
        dw 1,readback,0
        dw 05aa5h
        dw 0a55ah
mid: dw 0
        times 23 db 0cch
        dw 05aa5h,0a55ah
params: db 0
        times 31 db 0cch
        dw 05aa5h,0a55ah
rw: db 0
        dw 0,0,0,1,original,0
        dw 05aa5h,0a55ah
original: times 1024 db 0cch
        dw 05aa5h,0a55ah
modified: times 1024 db 0cch
        dw 05aa5h,0a55ah
readback: times 1024 db 0cch
        dw 05aa5h
result_name: db 'BLKIO.RES',0
%include "harness.inc"
