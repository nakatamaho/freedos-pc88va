; SPDX-License-Identifier: GPL-2.0-or-later
; Original 8086 FreeDOS/VA runtime recorder. Capture outputs before assertions,
; retain them in guest memory, then serialize through the already qualified
; DOS write path. A missing/truncated record is never a pass. The diagnostic
; stop label exposes first-failure AX/BX/CX/DX without changing guest state.
%macro DOS 1
        mov word [cs:case_id], %1
        call invoke21
%endmacro
%macro OK 0
        push bx
        mov bx, [record_end]
        mov word [bx-2], 1
        pop bx
%endmacro
%macro SUCCESS 0
        jc failure
        OK
%endmacro
%macro ERROR 1
        jnc failure
        cmp ax, %1
        jne failure
        OK
%endmacro
; Use for owner-deferred MS-DOS error-value comparisons: the FreeDOS call must
; report failure, but its exact error value is retained as an observation.
%macro ERROR_ANY 0
        jnc failure
        OK
%endmacro
; Preserve a documented provider-unavailable mismatch while continuing to
; collect later independent cases. The recorded case stays unchecked and the
; caller must finish through `finish`, not `passed`.
%macro ERROR_CONTINUE 1
        jc %%carry_set
        jmp %%failed
%%carry_set:
        cmp ax, %1
        jne %%failed
        OK
        jmp %%done
%%failed:
        push bx
        mov bx, [record_end]
        mov word [bx-2], 0
        pop bx
        mov ax, [case_id]
        cmp word [first_failure], 0
        jne %%done
        mov [first_failure], ax
%%done:
%endmacro
%macro EQUAL_AX 1
        jc failure
        cmp ax, %1
        jne failure
        OK
%endmacro
%macro EQUAL_DX 1
        cmp dx, %1
        jne failure
%endmacro
%macro EQUAL_CX 1
        cmp cx, %1
        jne failure
%endmacro
%macro CARRY_CLEAR 0
        jc failure
%endmacro

%macro EQUAL_AL 1
        cmp al, %1
        jne failure
        OK
%endmacro
