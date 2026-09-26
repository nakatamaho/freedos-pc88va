; SPDX-License-Identifier: GPL-2.0-or-later
invoke21:
        mov [cs:snapshot+2], ax
        mov [cs:call_sp], sp
%ifdef M15_ABSOLUTE_IO
        cmp byte [cs:absolute_interrupt], 25h
        je .read_absolute
        cmp byte [cs:absolute_interrupt], 26h
        je .write_absolute
%endif
%ifdef M15_COMPANION
        cmp byte [cs:companion_entry], 28h
        je .idle
        cmp byte [cs:companion_entry], 29h
        je .fast_output
        cmp byte [cs:companion_entry], 2fh
        je .multiplex
        cmp byte [cs:companion_entry], 5
        je .call5
%endif
        int 21h
%ifdef M15_COMPANION
        jmp .capture
.idle:
        int 28h
        jmp .capture
.fast_output:
        int 29h
        jmp .capture
.multiplex:
        int 2fh
        jmp .capture
.call5:
        call 5
        jmp .capture
%endif
%ifdef M15_ABSOLUTE_IO
        jmp .capture
.read_absolute:
        int 25h
        jmp .absolute_flags
.write_absolute:
        int 26h
.absolute_flags:
        mov [cs:absolute_sp], sp
        ; DOS deliberately leaves the caller's FLAGS image on this stack.
        ; POP memory preserves the returned CF before the common capture.
        pop word [cs:absolute_flags]
%endif
.capture:
        mov [cs:snapshot+4], ax
        mov [cs:snapshot+6], bx
        mov [cs:snapshot+8], cx
        mov [cs:snapshot+10], dx
        mov [cs:snapshot+12], si
        mov [cs:snapshot+14], di
        mov [cs:snapshot+16], bp
        mov [cs:snapshot+18], ds
        mov [cs:snapshot+20], es
        pushf
        pop word [cs:snapshot+22]
        mov [cs:return_sp], sp
        push cs
        pop ds
        push cs
        pop es
        mov ax, [case_id]
        mov [snapshot], ax
        mov ax, [return_sp]
        sub ax, [call_sp]
        mov [snapshot+24], ax
        mov word [snapshot+26], 0
        cmp word [record_count], 192
        jb .space
        mov ax, [case_id]
        mov [first_failure], ax
%ifdef M15_FAILURE_HOOK
        call M15_FAILURE_HOOK
%endif
        jmp finish
.space:
        mov si, snapshot
        mov di, [record_end]
        mov cx, 14
        cld
        rep movsw
        mov [record_end], di
        inc word [record_count]
        mov ax, [snapshot+4]
        mov bx, [snapshot+6]
        mov cx, [snapshot+8]
        mov dx, [snapshot+10]
        mov si, [snapshot+12]
        mov di, [snapshot+14]
        mov bp, [snapshot+16]
        push word [snapshot+22]
        popf
        ret

failure:
        mov bx, [record_end]
        mov word [bx-2], 0
        mov ax, [case_id]
        mov [first_failure], ax
%ifdef M15_FAILURE_HOOK
        call M15_FAILURE_HOOK
%endif
        jmp finish
passed:
        mov word [first_failure], 0
finish:
        call save_report
        mov dx, done_message
        mov ah, 09h
        int 21h
        mov ax, [first_failure]
        or ax, ax
        jz .exit
        mov al, 1
.exit:
        mov ah, 4ch
        int 21h
save_report:
        push cs
        pop ds
        push cs
        pop es
        mov dx, result_name
        xor cx, cx
        mov ah, 3ch
        int 21h
        jc report_failure
        mov [report_handle], ax
        mov bx, ax
        mov dx, report
        mov cx, [record_end]
        sub cx, report
        mov [report_length], cx
        mov ah, 40h
        int 21h
        jc report_failure
        cmp ax, [report_length]
        jne report_failure
        mov bx, [report_handle]
        mov ah, 3eh
        int 21h
        jc report_failure
        ret
report_failure:
        mov bx, [first_failure]
        mov cx, [record_count]
        mov dx, [snapshot+4]
report_failed_stop:
        nop
        mov ax, 4cffh
        int 21h

case_id: dw 0
call_sp: dw 0
return_sp: dw 0
report_handle: dw 0
report_length: dw 0
snapshot: times 14 dw 0
%ifdef M15_COMPANION
companion_entry: db 0
%endif
%ifdef M15_ABSOLUTE_IO
absolute_interrupt: db 0
absolute_sp: dw 0
absolute_flags: dw 0
%endif
record_end: dw records
done_message: db 'M15 recorded results; host verification required',13,10,'$'
report:
        db 'M15R'
        dw 1, 28
record_count: dw 0
first_failure: dw 0
records: times 192*28 db 0
