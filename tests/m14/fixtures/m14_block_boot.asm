; SPDX-License-Identifier: GPL-2.0-or-later
; Exclusive pre-DOS block probe. Link the unmodified production platform,
; resident disk, and machine-service objects. No DOS filesystem is mounted.
; The loader supplies a disposable medium; this program never boots DOS or
; returns after raw mutation. RESTORE=0 deliberately leaves target patterns.
bits 16
cpu 8086
%include "kernel/m13_segments.inc"
%include "boot/loader_abi.inc"
segment _PC88VA_CODE

extern FL_READ, FL_WRITE, FL_VERIFY, pc88va_machine_init_
extern pc88va_m12_drive_context_, pc88va_m12_call_flags_
extern pc88va_m12_request_
%ifdef M14_ERROR_STATUS
extern pc88va_clock_read_, pc88va_m10_clock_record_
%endif
%ifdef M14_PARTIAL
extern pc88va_m12_prepare_, pc88va_kernel_disk_write_
extern pc88va_kernel_firmware_write_one_, pc88va_m12_buffer_
global m14_partial_ready, m14_partial_done, m14_partial_recover
%endif
global entry, ..start, _int21_service, pc88va_console_putc_
global m14_block_stop, m14_block_result, m14_block_phase, m14_block_case
global m14_reject_begin, m14_reject_end
%ifdef M14_ERROR_STATUS
global m14_error_ready, m14_recover_ready, m14_error_status, m14_error_completed
%endif

%if M14_SECTOR_BYTES != 1024 || M14_SECTORS_TRACK != 8 || M14_HEADS != 2
%error Fixture geometry must match the production VA adapter
%endif
%define BUFFER_BYTES (2*M14_SECTOR_BYTES)

entry:
..start:
        cli
        cld
        push cs
        pop ds
        push cs
        pop es
        mov [pc88va_m12_drive_context_], dx
        mov [pc88va_m12_call_flags_], bx
        call pc88va_machine_init_
        or ax, ax
        jnz failed
        mov si, begin_message
        call puts
%ifdef M14_ERROR_STATUS
%ifdef M14_PARTIAL
        jmp partial_case
%else
        jmp error_case
%endif
%endif
        mov word [m14_block_case], 0
.case:
        mov bx, [m14_block_case]
        shl bx, 1
        shl bx, 1
        mov ax, [cases+bx]
        mov [lba], ax
        mov ax, [cases+bx+2]
        mov [count], ax
        mov byte [m14_block_phase], 1
        mov bx, original
        mov bp, FL_READ
        call transfer
        or ax, ax
        jnz failed
        call guards
        jnz guard_failed

        mov ax, [lba]
        xor ax, 0a55ah
        mov di, pattern
        mov cx, [count]
        mov bx, M14_SECTOR_BYTES/2
        push ax
        mov ax, cx
        mul bx
        mov cx, ax
        pop ax
.pattern:
        stosw
        add ax, 17
        loop .pattern
        mov byte [m14_block_phase], 2
        mov bx, pattern
        mov bp, FL_WRITE
        call transfer
        or ax, ax
        jnz mutation_failed
        mov byte [m14_block_phase], 3
        mov bx, pattern
        mov bp, FL_VERIFY
        call transfer
        or ax, ax
        jnz mutation_failed
        mov byte [m14_block_phase], 4
        mov bx, readback
        mov bp, FL_READ
        call transfer
        or ax, ax
        jnz mutation_failed
        mov si, pattern
        call compare_readback
        jne compare_failed
        call guards
        jnz guard_failed
%if M14_RESTORE
        mov byte [m14_block_phase], 5
        call restore
        or ax, ax
        jnz failed
        mov byte [m14_block_phase], 6
        mov bx, readback
        mov bp, FL_READ
        call transfer
        or ax, ax
        jnz failed
        mov si, original
        call compare_readback
        jne compare_failed
        call guards
        jnz guard_failed
%endif
        inc word [m14_block_case]
        cmp word [m14_block_case], (cases_end-cases)/4
        jb .case
        ; The final sector fits exactly below offset 10000h. The linked
        ; zero-fill tail owns this buffer plus a guard beyond that boundary.
        mov byte [m14_block_phase], 7
        mov word [0fbfeh], 071c3h
        mov ax, cs
        add ax, 1000h
        mov es, ax
        mov word [es:0], 03c17h
        push cs
        pop es
        mov si, pattern
        mov di, 0fc00h
        mov cx, M14_SECTOR_BYTES/2
        rep movsw
        mov bx, 0fc00h
        mov bp, FL_WRITE
        call transfer
        or ax, ax
        jnz mutation_failed
        mov bx, 0fc00h
        mov bp, FL_VERIFY
        call transfer
        or ax, ax
        jnz mutation_failed
        mov di, 0fc00h
        mov cx, M14_SECTOR_BYTES/2
        mov ax, 05a5ah
        rep stosw
        mov bx, 0fc00h
        mov bp, FL_READ
        call transfer
        or ax, ax
        jnz mutation_failed
        mov si, pattern
        mov di, 0fc00h
        mov cx, M14_SECTOR_BYTES/2
        repe cmpsw
        jne compare_failed
        cmp word [0fbfeh], 071c3h
        jne guard_failed
        mov ax, cs
        add ax, 1000h
        mov es, ax
        cmp word [es:0], 03c17h
        push cs
        pop es
        jne guard_failed
%if M14_RESTORE
        call restore
        or ax, ax
        jnz failed
        mov bx, readback
        mov bp, FL_READ
        call transfer
        or ax, ax
        jnz failed
        mov si, original
        call compare_readback
        jne compare_failed
%endif
        call guards
        jnz guard_failed
        mov byte [m14_block_phase], 8
        ; Verify must reject mismatching bytes, not merely perform a read.
%if M14_RESTORE
        mov bx, original
%else
        mov bx, pattern
%endif
        xor word [bx], 1
        mov bp, FL_VERIFY
        call transfer
        xor word [bx], 1
        cmp ax, 10h
        jne failed
        mov byte [m14_block_phase], 9
m14_reject_begin:
        xor di, di
.function:
        mov bp, [functions+di]
        mov si, rejected
        mov cx, (rejected_end-rejected)/14
.request:
        push cx
        push word [si]
        push word [si+2]
        push word [si+4]
        push word [si+6]
        push word [si+8]
        mov ax, [si+10]
        or ax, ax
        jnz .segment
        mov ax, cs
.segment:
        push ax
        push word [si+12]
        push cs
        call bp
        pop cx
        cmp ax, 2
        jne failed
        add si, 14
        loop .request
        add di, 2
        cmp di, 6
        jb .function
m14_reject_end:
        call guards
        jnz guard_failed
        mov word [m14_block_result], 0
        mov si, pass_message
        call puts
        jmp m14_block_stop

compare_failed:
        mov ax, 0ff01h
        jmp mutation_failed
guard_failed:
        mov ax, 0ff02h
mutation_failed:
        mov [m14_block_result], ax
%if M14_RESTORE
        ; Best effort only: an unsuccessful restoration is still a failure.
        call restore
%endif
        mov ax, [m14_block_result]
failed:
        or ax, ax
        jnz .nonzero
        mov ax, 0ff05h              ; unexpected success is still test failure
.nonzero:
        mov [m14_block_result], ax
        mov si, fail_message
        call puts
        mov ax, [m14_block_result]
        call hex_word
        mov ax, [m14_block_case]
        call hex_word
        xor ax, ax
        mov al, [m14_block_phase]
        call hex_word
m14_block_stop:
        cli
        hlt
        jmp m14_block_stop

%ifdef M14_ERROR_STATUS
error_case:
        mov word [lba], M14_TOTAL_SECTORS-1
        mov word [count], 1
        mov byte [m14_block_phase], 10
        mov bx, original
        mov bp, FL_READ
        call transfer
        or ax, ax
        jnz failed
        mov si, original
        mov di, pattern
        mov cx, M14_SECTOR_BYTES/2
        rep movsw
        xor word [pattern], 1
        ; The normal emulator mount facility changes only the device medium
        ; at these labels. No guest memory or return value is patched.
m14_error_ready:
        nop
        call settle_device
        mov bx, pattern
        mov bp, FL_WRITE
        call transfer
        mov [m14_error_status], ax
        mov dx, [pc88va_m12_request_+RD_COMPLETED]
        mov [m14_error_completed], dx
        cmp ax, M14_ERROR_STATUS
        jne failed
        or dx, dx
        jnz count_failed
        call guards
        jnz guard_failed
        mov si, error_message
        call puts
        mov byte [m14_block_phase], 11
m14_recover_ready:
        nop
        call settle_device
        mov bx, pattern
        mov bp, FL_WRITE
        call transfer
        or ax, ax
        jnz mutation_failed
        mov bx, pattern
        mov bp, FL_VERIFY
        call transfer
        or ax, ax
        jnz mutation_failed
        mov bx, readback
        mov bp, FL_READ
        call transfer
        or ax, ax
        jnz mutation_failed
        mov si, pattern
        call compare_readback
        jne compare_failed
        call restore
        or ax, ax
        jnz failed
        mov bx, readback
        mov bp, FL_READ
        call transfer
        or ax, ax
        jnz failed
        mov si, original
        call compare_readback
        jne compare_failed
        call guards
        jnz guard_failed
        mov word [m14_block_result], 0
        mov si, recovery_message
        call puts
        jmp m14_block_stop
count_failed:
        mov ax, 0ff04h
        jmp failed
m14_error_status dw 0ffffh
m14_error_completed dw 0ffffh
error_message db 'M14BLOCK:EXPECTED-ERROR', 13, 10, 0
recovery_message db 'M14BLOCK:RECOVERED', 13, 10, 0

; Mount requests are asynchronous host device actions. Wait for observed
; retrace edges through the existing machine service, not a host-speed delay
; or a fabricated device-ready bit. Missing media remains absent throughout.
settle_device:
        mov cx, 64
.edge:
        mov ax, pc88va_m10_clock_record_
        call pc88va_clock_read_
        or ax, ax
        jnz failed
        loop .edge
        ret
%endif

%ifdef M14_PARTIAL
partial_case:
        mov word [lba], M14_SECTORS_TRACK-1
        mov word [count], 2
        mov byte [m14_block_phase], 12
        mov bx, original
        mov bp, FL_READ
        call transfer
        or ax, ax
        jnz failed
        mov di, pattern
        mov ax, 'PP'
        mov cx, M14_SECTOR_BYTES
        rep stosw
        mov si, pattern
        mov di, pc88va_m12_buffer_
        mov cx, M14_SECTOR_BYTES
        rep movsw
        call pc88va_m12_prepare_
        mov word [pc88va_m12_request_+RD_LBA], M14_SECTORS_TRACK-1
        mov word [pc88va_m12_request_+RD_COUNT], 2
        mov word [pc88va_m12_request_+RD_ADAPTER_OFFSET], pc88va_kernel_firmware_write_one_
m14_partial_ready:
        nop
        mov ax, pc88va_m12_request_
        call pc88va_kernel_disk_write_
m14_partial_done:
        mov [m14_error_status], ax
        mov dx, [pc88va_m12_request_+RD_COMPLETED]
        mov [m14_error_completed], dx
        cmp ax, DISK_FIRMWARE
        jne failed
        cmp dx, M14_SECTOR_BYTES
        jne count_failed
        cmp word [pc88va_m12_request_+RD_CURRENT_LBA], M14_SECTORS_TRACK
        jne count_failed
        cmp word [pc88va_m12_request_+RD_REMAINING], 1
        jne count_failed
        call guards
        jnz guard_failed
        mov si, partial_message
        call puts
        mov byte [m14_block_phase], 13
m14_partial_recover:
        nop
        call settle_device
        ; Leave the failed request's first-sector prefix for host inspection.
        ; Prove recovery on a different extent, restoring that extent exactly.
        mov word [lba], M14_TOTAL_SECTORS-1
        mov word [count], 1
        mov bx, original
        mov bp, FL_READ
        call transfer
        or ax, ax
        jnz failed
        mov di, pattern
        mov ax, 'QQ'
        mov cx, M14_SECTOR_BYTES/2
        rep stosw
        mov bx, pattern
        mov bp, FL_WRITE
        call transfer
        or ax, ax
        jnz mutation_failed
        mov bx, pattern
        mov bp, FL_VERIFY
        call transfer
        or ax, ax
        jnz mutation_failed
        mov bx, readback
        mov bp, FL_READ
        call transfer
        or ax, ax
        jnz mutation_failed
        mov si, pattern
        call compare_readback
        jne compare_failed
        call restore
        or ax, ax
        jnz failed
        mov bx, readback
        mov bp, FL_READ
        call transfer
        or ax, ax
        jnz failed
        mov si, original
        call compare_readback
        jne compare_failed
        call guards
        jnz guard_failed
        mov word [m14_block_result], 0
        mov si, partial_recovered
        call puts
        jmp m14_block_stop
partial_message db 'M14BLOCK:PARTIAL-ERROR', 13, 10, 0
partial_recovered db 'M14BLOCK:PARTIAL-RECOVERED', 13, 10, 0
%endif

restore:
        mov bx, original
        mov bp, FL_WRITE
        call transfer
        ret

; Same FAR PASCAL ABI as the medium-model common kernel. BP selects the
; production function; all three production objects share PC88VA_PLATFORM.
transfer:
        xor ax, ax
        push ax                      ; logical drive zero
        mov ax, [lba]
        xor dx, dx
        mov cx, M14_SECTORS_TRACK
        div cx
        inc dx
        mov [sector], dx
        xor dx, dx
        mov cx, M14_HEADS
        div cx
        push dx                      ; head
        push ax                      ; cylinder
        push word [sector]
        push word [count]
        push ds
        push bx                      ; caller buffer
        push cs
        call bp                      ; synthetic FAR call, no private patch
        ret

compare_readback:
        mov di, readback
        mov cx, [count]
        mov ax, M14_SECTOR_BYTES/2
        mul cx
        mov cx, ax
        repe cmpsw
        ret

guards:
        cmp word [original_guard_before], 071c3h
        jne .done
        cmp word [original_guard_after], 03c17h
        jne .done
        cmp word [pattern_guard_before], 071c3h
        jne .done
        cmp word [pattern_guard_after], 03c17h
        jne .done
        cmp word [readback_guard_before], 071c3h
        jne .done
        cmp word [readback_guard_after], 03c17h
.done:
        ret

puts:
        lodsb
        or al, al
        jz .done
        xor ah, ah
        call pc88va_console_putc_
        jmp puts
.done:
        ret

hex_word:
        push bx
        push cx
        mov bx, ax
        mov cx, 4
.digit:
        push cx
        mov cl, 4
        rol bx, cl
        mov al, bl
        and al, 15
        add al, '0'
        cmp al, '9'
        jbe .print
        add al, 7
.print:
        xor ah, ah
        call pc88va_console_putc_
        pop cx
        loop .digit
        mov ax, ' '
        call pc88va_console_putc_
        pop cx
        pop bx
        ret

; Display only; disk I/O never passes through a test replacement callback.
pc88va_console_putc_:
        pushf
        push ax
        push bx
        push cx
        push dx
        push si
        push di
        push bp
        push ds
        push es
        push ax
        push ss
        pop ds
        mov si, sp
        mov dx, 08000h
        mov ah, 02h
        int 083h
        add sp, 2
        pop es
        pop ds
        pop bp
        pop di
        pop si
        pop dx
        pop cx
        pop bx
        pop ax
        popf
        ret

; Resolve the unused DOS bridge symbol by trapping, never invent DOS success.
_int21_service:
        mov ax, 0ff03h
        jmp failed

begin_message db 'M14BLOCK:BEGIN', 13, 10, 0
%if M14_RESTORE
pass_message db 'M14BLOCK:RESTORED', 13, 10, 0
%else
pass_message db 'M14BLOCK:PATTERNS', 13, 10, 0
%endif
fail_message db 'M14BLOCK:FAIL status/case/phase ', 0
cases:
        dw 0, 1
        dw M14_SECTORS_TRACK-1, 2
        dw M14_SECTORS_TRACK*M14_HEADS-1, 2
        dw M14_TOTAL_SECTORS-1, 1
cases_end:
functions dw FL_READ, FL_WRITE, FL_VERIFY
; FAR PASCAL arguments, buffer segment zero denotes this program's CS.
rejected:
        dw 1, 0, 0, 1, 1, 0, pattern
        dw 0, 2, 0, 1, 1, 0, pattern
        dw 0, 0, M14_TOTAL_SECTORS/(M14_HEADS*M14_SECTORS_TRACK), 1, 1, 0, pattern
        dw 0, 0, 0, 0, 1, 0, pattern
        dw 0, 0, 0, M14_SECTORS_TRACK+1, 1, 0, pattern
        dw 0, 0, 0, 1, 0, 0, pattern
        dw 0, 0, 0, 1, 0ffffh, 0, pattern
        dw 0, M14_HEADS-1, M14_TOTAL_SECTORS/(M14_HEADS*M14_SECTORS_TRACK)-1, M14_SECTORS_TRACK, 2, 0, pattern
        dw 0, 0, 0, 1, 1, 0, 0fc01h
        dw 0, 0, 0, 1, 2, 0, 0f801h
        dw 0, 0, 0, 1, 65, 0, 0
        dw 0, 0, 0, 1, 2, 0ffc0h, 0
rejected_end:
lba dw 0
count dw 0
sector dw 0
m14_block_result dw 0ffffh
m14_block_case dw 0
m14_block_phase db 0
align 2, db 0
original_guard_before dw 071c3h
original times BUFFER_BYTES db 0
original_guard_after dw 03c17h
pattern_guard_before dw 071c3h
pattern times BUFFER_BYTES db 0
pattern_guard_after dw 03c17h
readback_guard_before dw 071c3h
readback times BUFFER_BYTES db 0
readback_guard_after dw 03c17h

segment M14_STACK class=STACK stack align=16 use16
        resb 4096

; Additional declared zero-fill allocation, not an unowned magic RAM buffer.
; The build checks the MZ extent includes CS:10000h and keeps the stack close
; to the resident machine-service code. The loader/carrier owns this tail.
segment M14_TAIL_ARENA class=BSS public align=16 use16
        resb 49152
