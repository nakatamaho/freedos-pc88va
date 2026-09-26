; SPDX-License-Identifier: GPL-2.0-or-later
; Original 8086 probe for the local INT 21h/5F07h and 5F08h mapping calls.
; AH=52h is used only to observe the target's own List-of-Lists/CDS state.
bits 16
cpu 8086
org 100h
%include "macros.inc"
%define M15_FAILURE_HOOK restore_mapping_on_failure
%define M15_CHAIN_NAME 'DRVMAP.MCB'

%define LOL_CDS_OFFSET 16h
%define LOL_LASTDRIVE_OFFSET 21h
%define CDS_FLAGS_OFFSET 43h
%define CDS_DPB_OFFSET 45h
%define CDS_PHYSICAL 4000h

start:
        push cs
        pop ds
        push cs
        pop es
        cld

        mov ah, 62h
        DOS 5801
        mov [psp], bx
        mov ax, cs
        cmp bx, ax
        jne failure
        OK

        ; The local AH=52h result addresses LoL.DPBp. Its CDS pointer and
        ; lastdrive fields are read only as target-local state observations.
        mov ah, 52h
        DOS 5802
        mov es, [snapshot+20]
        mov bx, [snapshot+6]
        mov ax, [es:bx+LOL_CDS_OFFSET]
        mov [cds_offset], ax
        mov ax, [es:bx+LOL_CDS_OFFSET+2]
        mov [cds_segment], ax
        mov al, [es:bx+LOL_LASTDRIVE_OFFSET]
        mov [lastdrive], al
        push cs
        pop es
        cmp byte [lastdrive], 1
        jb failure
        OK

        ; The target's kernel build uses -zp1; cds.h therefore places flags
        ; immediately after the 67-byte current-path field.
        mov es, [cds_segment]
        mov bx, [cds_offset]
        cmp word [es:bx+CDS_DPB_OFFSET], 0
        je failure
        mov ax, [es:bx+CDS_FLAGS_OFFSET]
        mov [original_flags], ax
        mov byte [mapping_saved], 1
        push cs
        pop es

        xor dx, dx                     ; DL=0 is the physical A: CDS entry.
        mov ax, 5f08h                  ; Disable physical drive mapping.
        DOS 5803
        SUCCESS
        call check_disabled

        xor dx, dx
        mov ax, 5f07h                  ; Enable physical drive mapping.
        DOS 5804
        SUCCESS
        call check_enabled

        mov dl, [lastdrive]            ; One past the highest valid index.
        mov ax, 5f07h
        DOS 5805
        ERROR 15
        call check_enabled

        mov dl, [lastdrive]
        mov ax, 5f08h
        DOS 5806
        ERROR 15
        call check_enabled

        ; Restore the original bit even if this drive started unmapped.
        test word [original_flags], CDS_PHYSICAL
        jz .restore_disabled
        mov ax, 5f07h
        jmp short .restore_mapping
.restore_disabled:
        mov ax, 5f08h
.restore_mapping:
        xor dx, dx
        DOS 5807
        SUCCESS
        call check_original
        call save_chain
        jmp passed

check_disabled:
        mov es, [cds_segment]
        mov bx, [cds_offset]
        test word [es:bx+CDS_FLAGS_OFFSET], CDS_PHYSICAL
        jnz failure
        push cs
        pop es
        ret

check_enabled:
        mov es, [cds_segment]
        mov bx, [cds_offset]
        test word [es:bx+CDS_FLAGS_OFFSET], CDS_PHYSICAL
        jz failure
        push cs
        pop es
        ret

check_original:
        mov es, [cds_segment]
        mov bx, [cds_offset]
        mov ax, [es:bx+CDS_FLAGS_OFFSET]
        and ax, CDS_PHYSICAL
        mov dx, [original_flags]
        and dx, CDS_PHYSICAL
        cmp ax, dx
        jne failure
        push cs
        pop es
        ret

restore_mapping_on_failure:
        cmp byte [mapping_saved], 1
        jne .done
        test word [original_flags], CDS_PHYSICAL
        jz .disabled
        mov ax, 5f07h
        jmp short .restore
.disabled:
        mov ax, 5f08h
.restore:
        xor dx, dx
        int 21h
.done:
        ret

cds_offset: dw 0
cds_segment: dw 0
lastdrive: db 0
original_flags: dw 0
mapping_saved: db 0
result_name: db 'DRVMAP.RES',0
%include "arena.inc"
%include "harness.inc"
