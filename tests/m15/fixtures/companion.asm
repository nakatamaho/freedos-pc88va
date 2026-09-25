; SPDX-License-Identifier: GPL-2.0-or-later
; Alternate DOS entries and local server/error packets.
; Microsoft DOS 4 SRVCALL.ASM defines AL=0Ah as DS:DX -> DPL and seeds
; the next AH=59h query. AH=59h's destroyed registers are never asserted.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%define M15_COMPANION 1
%define M15_FAILURE_HOOK restore_error
%macro ALT 2
        mov byte [cs:companion_entry], %1
        DOS %2
        mov byte [cs:companion_entry], 0
%endmacro
%macro MUX 2
        mov bx, 0ffffh
        mov dx, 0ffffh
        mov ax, %2
        ALT 2fh, %1
%endmacro
start:
        push cs
        pop ds
        push cs
        pop es
        cld
        mov ax, 3530h
        DOS 23999
        mov [vector30], bx
        mov [vector30+2], es
        OK
        call save_report
        mov es, [vector30+2]
        mov si, [vector30]
        mov ax, [es:si]
        mov bx, [es:si+2]
        mov cx, [es:si+4]
        mov dx, [es:si+6]
        mov ah, 19h
        DOS 24000
        OK
        call save_report
        push cs
        pop es
        mov ah, 19h
        DOS 24001
        mov [drive], al
        OK
        call save_report
        mov cl, 19h
        ALT 5, 24002
        cmp al, [drive]
        jne failure
        OK
        call save_report
        mov cl, 0bh
        ALT 5, 24003
        cmp al, 0
        je .call5_status_valid
        cmp al, 0ffh
        jne failure
.call5_status_valid:
        OK
        call save_report
        mov ax, 1234h
        mov bx, 2345h
        mov cx, 3456h
        mov dx, 4567h
        mov si, 5678h
        mov di, 6789h
        mov bp, 789ah
        ALT 28h, 24005
        cmp ax, 1234h
        jne failure
        cmp bx, 2345h
        jne failure
        cmp cx, 3456h
        jne failure
        cmp dx, 4567h
        jne failure
        cmp si, 5678h
        jne failure
        cmp di, 6789h
        jne failure
        cmp bp, 789ah
        jne failure
        mov ax, cs
        cmp [snapshot+18], ax
        jne failure
        cmp [snapshot+20], ax
        jne failure
        OK
        call save_report
        mov ax, 1680h
        ALT 2fh, 24006
        ; The local idle hook must return with its caller stack intact.
        OK
        call save_report
        mov ax, 1200h
        ALT 2fh, 24007
        EQUAL_AL 0ffh
        xor bx, bx
        mov ax, 1220h
        ALT 2fh, 24008
        CARRY_CLEAR
        mov es, [snapshot+20]
        xor bx, bx
        mov bl, [es:di]
        cmp bl, 0ffh
        je failure
        push cs
        pop es
        OK
        mov ax, 1216h
        ALT 2fh, 24009
        CARRY_CLEAR
        mov es, [snapshot+20]
        cmp word [es:di], 0
        je failure
        test word [es:di+5], 80h
        jz failure
        push cs
        pop es
        OK
        MUX 24010, 1400h
        CARRY_CLEAR
        cmp bx, 534bh             ; Public FreeDOS NLS interface identifier.
        jne failure
        EQUAL_AL 0
        mov di, counted
        mov cx, 4
        MUX 24011, 1422h
        CARRY_CLEAR
        cmp word [counted], 'AB'
        jne failure
        cmp word [counted+2], '19'
        jne failure
        cmp byte [counted+4], 'z'
        jne failure
        OK
        mov di, filename
        mov cx, 4
        MUX 24012, 14a2h
        CARRY_CLEAR
        cmp word [filename], 'FD'
        jne failure
        cmp word [filename+2], '.C'
        jne failure
        cmp byte [filename+4], 'x'
        jne failure
        OK
        mov cx, 'Y'
        MUX 24013, 1423h
        EQUAL_AL 1
        mov cx, 'N'
        MUX 24014, 1423h
        EQUAL_AL 0
        mov cx, '?'
        MUX 24015, 1423h
        EQUAL_AL 2
        ; A direct packet entry executes the same version query as AH30.
        mov ax, 3000h
        DOS 24016
        mov [version], ax
        OK
        mov ax, cs
        mov [packet+12], ax
        mov [packet+14], ax
        mov dx, packet
        mov ax, 5d00h
        DOS 24017
        cmp ax, [version]
        jne failure
        OK
        mov ax, 5d06h
        DOS 24018
        CARRY_CLEAR
        or cx, cx
        jz failure
        or dx, dx
        jz failure
        cmp dx, cx
        ja failure
        mov ax, si
        add ax, cx
        jc failure
        mov ax, [snapshot+18]
        or ax, ax
        jz failure
        OK
        ; Fast output is observed independently in the saved TVRAM dump.
        mov al, '['
        ALT 29h, 24025
        OK
        mov al, 'M'
        ALT 29h, 24026
        OK
        mov al, '1'
        ALT 29h, 24027
        OK
        mov al, '5'
        ALT 29h, 24028
        OK
        mov al, ']'
        ALT 29h, 24029
        OK
        ; No SHARE provider is loaded in the M15 profile.
        MUX 24030, 1000h
        EQUAL_AL 0
        ; No network redirector provider is loaded in the M15 profile.
        MUX 24031, 1100h
        EQUAL_AL 0
        ; Establish an error to save only AH=59h's documented return fields.
        mov dx, missing_error
        mov ax, 3d00h
        DOS 24032
        ERROR 2
        xor bx, bx
        mov ah, 59h
        DOS 24033
        cmp ax, 2
        jne failure
        cmp bh, 1
        jb failure
        cmp bh, 13
        ja failure
        cmp bl, 1
        jb failure
        cmp bl, 7
        ja failure
        cmp ch, 1
        jb failure
        cmp ch, 5
        ja failure
        mov [old_error], ax
        mov [old_error+2], bx
        xor ax, ax
        mov ah, ch
        mov [old_error+4], ax
        ; The saved DPL's DI/ES fields stay null: AH=59h destroys them.
        OK
        mov ax, cs
        mov [new_error+14], ax
        mov byte [error_changed], 1
        mov dx, new_error
        mov si, decoy_error
        mov ax, 5d0ah
        DOS 24034
        ; The next AH=59h result validates the DPL's documented fields.
        OK
        xor bx, bx
        mov ah, 59h
        DOS 24035
        call check_error
        OK
        ; Restore the prior documented error fields with a safe null device.
        mov dx, old_error
        mov ax, 5d0ah
        DOS 24036
        OK
        xor bx, bx
        mov ah, 59h
        DOS 24037
        cmp ax, [old_error]
        jne failure
        cmp bx, [old_error+2]
        jne failure
        cmp ch, [old_error+5]
        jne failure
        mov byte [error_changed], 0
        OK
        cmp word [new_error-2], 0a55ah
        jne failure
        cmp word [new_error+22], 05aa5h
        jne failure
        cmp word [packet-2], 0a55ah
        jne failure
        cmp word [packet+22], 05aa5h
        jne failure
        jmp passed
check_error:
        cmp ax, 5
        jne failure
        cmp bx, 0304h
        jne failure
        cmp ch, 4
        jne failure
        ; DOS 4 documents CL/DX/SI/DI/DS/ES as destroyed by AH=59h.
        ; These registers remain in the capture but are deliberately not asserted.
        ret
restore_error:
        push cs
        pop ds
        cmp byte [error_changed], 0
        je .done
        mov dx, old_error
        mov ax, 5d0ah
        int 21h
.done:
        push cs
        pop es
        ret
drive: db 0
version: dw 0
counted: db 'ab19z'
filename: db 'fd.cx'
missing_error: db 'A:\M15E59.$$$',0
error_changed: db 0
device_marker: db 'SYNTHETIC DEVICE POINTER'
old_error: times 11 dw 0
decoy_error: times 11 dw 0
        dw 0a55ah
new_error: dw 5,0304h,0400h,0,0,device_marker,0,0,0,0,0
        dw 05aa5h,0a55ah
packet: dw 3000h,0,0,0,0,0,0,0,0,0,0
        dw 05aa5h
vector30: dw 0,0
result_name: db 'CMPANION.RES',0
%include "harness.inc"
